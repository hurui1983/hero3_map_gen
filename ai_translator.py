"""
Layer 1 - AI 翻译: 自然语言 -> 标准化 Order JSON

调用 Claude API, 把用户的一句话点菜翻译成结构化字典.

输出 schema (强约束):
{
  "creatures": [str],   # 中文标准名/别名, 后续由 catalog.resolve_creature 校验
  "artifacts": [str],
  "difficulty": "easy" | "normal" | "hard" | null,
  "players": int | null,    # 2..8
  "map_size": "S" | "M" | "L" | "XL" | null,
  "description": str | null # AI 给地图起的一句话描述 (展示用)
}

设计原则:
  - LLM 不输出 RMG 内部 ID, 只输出"中文标准名/别名"
  - 任何 LLM 不认识的菜, 也不要瞎编, 直接不输出
  - 严格 JSON 输出, 不带任何 markdown 包装
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import catalog


PROJECT_ENV_FILE = Path(__file__).with_name(".env")
PROXY_ENV_KEYS = {
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "https_proxy",
    "http_proxy",
    "all_proxy",
    "no_proxy",
}


@dataclass(frozen=True)
class TranslatedOrder:
    """LLM 翻译完成、但尚未做白名单校验的原始结果."""
    creatures: list[str]
    artifacts: list[str]
    specials: list[str]    # 圣杯等特殊地图对象
    unrecognized: list[str]  # 用户提到但 LLM 自己也不认识的原话短语
    difficulty: str | None
    players: int | None
    map_size: str | None
    description: str | None


def _build_system_prompt() -> str:
    """生成 system prompt, 把当前 catalog 的菜单注入进去."""
    creature_names = "、".join(catalog.all_creature_names_zh())
    artifact_names = "、".join(catalog.all_artifact_names_zh())
    special_names = "、".join(catalog.all_special_names_zh())

    return f"""你是英雄无敌3 (HotA 资料片) 随机地图模板生成助手.

用户会用自然语言告诉你他想要的地图特征 (生物、神器、特殊对象、难度、玩家数、地图大小).
你的任务是把这句话翻译成严格的 JSON.

## 可点的"菜"

注意: 用户可能用任何说法, 你需要识别意图, 并输出"标准名"或"别名"中的任何一个 (后续会做校验).

生物 (creatures):
{creature_names}

神器 (artifacts):
{artifact_names}

特殊对象 (specials):
{special_names}

难度 (difficulty): easy / normal / hard
玩家数 (players): 2~8 之间的整数
地图大小 (map_size): "S" (小) / "M" (中) / "L" (大) / "XL" (超大)

## 玩家群体术语 (重要, 不要望文生义)

用户可能用以下"群体词"指代多个具体项, 你必须展开成具体名字:

- "四大神龙" / "四龙" / "四大龙" = ["圣龙", "水晶龙", "毒龙", "仙龙"]
  (这是 HoMM3 中立四大七级龙, 不要包含金龙/黑龙/骨龙等城镇龙)
- "组合宝物" / "组合神器" / "套装宝物" = ["末日之刃", "天使联盟", "鬼王斗篷",
  "生命灵药", "诅咒铠甲", "军团雕像", "龙父神力", "泰坦之雷", "海军上将之帽",
  "神射手之弓", "魔力源泉"] (HoMM3 全部 11 件组合神器)

## 输出格式

只输出 JSON, 不要任何其他文字, 不要 markdown 代码块包装.

{{
  "creatures": ["金龙"],
  "artifacts": ["末日之刃"],
  "specials": ["圣杯"],
  "unrecognized": ["龙骨胫甲", "永生靴"],
  "difficulty": "hard",
  "players": 4,
  "map_size": "M",
  "description": "中等地图, 4 玩家对战, 金龙守关, 末日之刃必出"
}}

## 规则

1. 用户没明说的字段, 输出 null (难度/玩家/大小) 或空数组 (生物/神器/特殊对象/未识别).
2. **严禁瞎编名字**. 你不认识或不能精确匹配的, 必须放进 unrecognized 字段, 用用户的原话.
3. unrecognized 的判定标准: 用户提到的"想要的东西"(生物/神器/特殊对象), 但你无法在以上菜单中找到精确匹配项 (包括别名). 此时**必须**保留用户原话到 unrecognized.
4. 不要把 unrecognized 项强行映射到一个"看起来像"的菜单项. 宁可标 unrecognized, 也不要猜.
5. 描述类的形容词 (如"地下风"、"海岛"、"刺激") 不算菜品, 不要进 unrecognized.
6. description 是给玩家看的简短描述, 一句话, 不要超过 30 个字.
7. 只输出 JSON, 不要解释.
"""


def _strip_json_markdown(text: str) -> str:
    """去掉 LLM 偶尔会加的 markdown 代码块包装."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _load_project_env(env_path: Path = PROJECT_ENV_FILE) -> None:
    """Load KEY=VALUE pairs from .env without overriding existing environment.

    Shell-provided credential env vars still win. Proxy keys are intentionally
    overridden by .env because inherited ALL_PROXY/all_proxy values can force
    httpx onto a SOCKS proxy path that this project does not require.
    """
    if not env_path.exists():
        return

    for line_no, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            raise ValueError(f"{env_path} 第 {line_no} 行不是 KEY=VALUE 格式: {raw_line!r}")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{env_path} 第 {line_no} 行环境变量名无效: {key!r}")

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif value.startswith(("'", '"')) or value.endswith(("'", '"')):
            raise ValueError(f"{env_path} 第 {line_no} 行引号不匹配: {raw_line!r}")

        if key in PROXY_ENV_KEYS:
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
        else:
            os.environ.setdefault(key, value)


def translate(user_text: str, api_key: str | None = None) -> TranslatedOrder:
    """调用 Claude 翻译用户的点菜.

    Args:
        user_text: 用户的自然语言点菜
        api_key: Anthropic API Key, 默认从 ANTHROPIC_API_KEY 环境变量读

    Returns:
        TranslatedOrder, LLM 输出的原始结果 (尚未经过白名单校验)

    Raises:
        ImportError: anthropic 库未安装
        RuntimeError: 缺少 API key
        ValueError: LLM 输出不是合法 JSON 或 schema 不对
    """
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("需要安装 anthropic: pip install anthropic") from e

    _load_project_env()

    # anthropic SDK 兼容两种鉴权 + 自定义 base URL (OpenRouter 等代理):
    #   - ANTHROPIC_API_KEY (官方)
    #   - ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL (OpenRouter 等)
    # 显式 api_key 参数优先, 否则交给 SDK 自己读环境变量.
    resolved_key = (
        api_key
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    if not resolved_key:
        raise RuntimeError(
            "缺少凭证: 请设置 ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / OPENROUTER_API_KEY"
        )
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    # Anthropic SDK 自己会补 /v1/messages, 所以 base 不应带 /v1.
    # OpenRouter 文档同时给两种路径示例, 用户经常误带 /v1, 这里统一归一化.
    if base_url:
        base_url = base_url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
    client = anthropic.Anthropic(api_key=resolved_key, base_url=base_url)

    # 走 OpenRouter 时模型 ID 需要带 provider 前缀 (anthropic/...)
    using_openrouter = "openrouter" in (os.environ.get("ANTHROPIC_BASE_URL") or "").lower()
    model = "anthropic/claude-sonnet-4.6" if using_openrouter else "claude-sonnet-4-5"

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_build_system_prompt(),
        messages=[{"role": "user", "content": user_text}],
    )
    raw_text = message.content[0].text
    cleaned = _strip_json_markdown(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 输出非合法 JSON: {e}\n原始输出:\n{raw_text}") from e

    return _parse_order_dict(data)


def _parse_order_dict(data: dict) -> TranslatedOrder:
    """从 dict 构造 TranslatedOrder, 容忍缺字段, 拒绝错误类型."""
    if not isinstance(data, dict):
        raise ValueError(f"LLM 输出顶层不是 dict: {type(data).__name__}")

    def _list_of_str(field: str) -> list[str]:
        v = data.get(field, [])
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError(f"字段 {field!r} 不是 list: {v!r}")
        return [str(x) for x in v if x]

    def _opt_str(field: str) -> str | None:
        v = data.get(field)
        if v is None or v == "":
            return None
        return str(v)

    def _opt_int(field: str) -> int | None:
        v = data.get(field)
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError(f"字段 {field!r} 不是整数: {v!r}")

    return TranslatedOrder(
        creatures=_list_of_str("creatures"),
        artifacts=_list_of_str("artifacts"),
        specials=_list_of_str("specials"),
        unrecognized=_list_of_str("unrecognized"),
        difficulty=_opt_str("difficulty"),
        players=_opt_int("players"),
        map_size=_opt_str("map_size"),
        description=_opt_str("description"),
    )
