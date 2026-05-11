# HoMM3 / HotA AI 随机地图模板生成器

把自然语言“点菜”转换成 HotA 随机地图模板 `.h3t`。

示例：

```bash
python3 order.py "我想要末日之刃和天使联盟、4 玩家、中等地图、强敌、有金龙"
```

程序会调用 OpenRouter/Claude 把输入翻译成结构化订单，经过本地 catalog 严格校验后，写出以 `ai_` 开头的 HotA RMG 模板文件到：

```text
/Applications/英雄无敌3：二合一.app/Contents/drive_c/game/HotA_RMGTemplates/
```

生成后重开游戏里的随机地图设置窗口，就能在模板列表看到新模板。

## 功能

- 自然语言识别生物、神器、特殊对象、难度、玩家数、地图大小。
- 所有点菜项必须精确命中本地 `catalog.py`，未识别则失败，不生成模板。
- 支持中文、英文和常见别名。
- 支持相似项建议，方便补 catalog 或修改输入。
- `.h3t` 用 GBK 编码写入，避免 HotA 中文乱码。
- 以 `Jebus Cross.h3t` 为骨架，只改必要字段。

## 环境准备

需要 Python 3 和 Anthropic SDK：

```bash
python3 -m pip install anthropic
```

项目支持读取根目录 `.env` 文件。复制 `.env.example` 为 `.env`，然后填入你的 OpenRouter key：

```bash
cp .env.example .env
```

`.env` 示例：

```dotenv
HTTPS_PROXY=http://127.0.0.1:7890
HTTP_PROXY=http://127.0.0.1:7890
ALL_PROXY=
all_proxy=
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
ANTHROPIC_AUTH_TOKEN=<OpenRouter key>
```

真实 `.env` 已被 `.gitignore` 忽略，不会提交到 GitHub。代理变量会以 `.env` 为准，避免继承到系统里的 SOCKS `ALL_PROXY/all_proxy` 后触发缺少 `socksio` 的错误。

凭证读取优先级：

```text
api_key 参数 > ANTHROPIC_API_KEY > ANTHROPIC_AUTH_TOKEN > OPENROUTER_API_KEY
```

`ANTHROPIC_BASE_URL` 可以带 `/v1`，程序会自动归一化，避免 SDK 拼成 `/v1/v1/messages`。

## 使用

生成模板：

```bash
python3 order.py "我想要末日之刃和天使联盟、4 玩家、中等地图、强敌、有金龙"
```

列出已经生成的 AI 模板：

```bash
python3 order.py --list
```

删除所有以 `ai_` 开头的生成模板：

```bash
python3 order.py --clean
```

查看帮助：

```bash
python3 order.py --help
```

## 示例输出

成功时会输出类似：

```text
[输入] '我想要末日之刃和天使联盟、4 玩家、中等地图、强敌、有金龙'

[1/3] AI 翻译中...
[2/3] 严格白名单校验:
[3/3] 写入模板:
  生成: /Applications/英雄无敌3：二合一.app/Contents/drive_c/game/HotA_RMGTemplates/ai_金龙_末日之刃_天使联盟_hard_0115.h3t

[完成] 启动游戏 -> 单人 -> 随机地图 -> 在模板列表里找以 'AI ' 开头的项
```

## 已支持写入的 HotA RMG 字段

- 模板名和描述。
- 地图大小：`S`、`M`、`L`、`XL`。
- 玩家数：同步 Zone 段和已有 Connection 段。
- 难度：`easy`、`normal`、`hard` 映射到 `weak`、`avg`、`strong`。
- 必出神器：写入 `Map.Artifacts`，例如末日之刃 `+128`、天使联盟 `+129`。

## 已知限制

- HotA RMG 没有“指定某个具体生物必出”的直接字段。输入金龙、圣龙等生物时，程序会严格识别并记录提示，但不会写入具体 creature ID。
- 圣杯作为特殊对象识别，当前由 RMG 默认方尖碑机制处理，不额外写字段。
- 组合神器当前直接按全局 artifact RMG ID 写入 `Map.Artifacts`，不使用 `Combo Arts` 列。
- HotA 不从子目录加载 RMG 模板，生成文件必须在 `HotA_RMGTemplates` 根目录。

## 退出码

```text
0 成功
1 CLI 用法错误
2 AI / 网络 / SDK 错误
3 用户输入有未识别项
```

未识别项会显示类别、原话和相似建议。只要有任意未识别点菜项，程序就会中止，不会生成模板。

## 测试

运行完整单元测试：

```bash
python3 -m unittest order_test catalog_test ai_translator_test order_to_rmg_test
```

当前测试覆盖 catalog 解析、AI 输出解析、严格校验、RMG 字段动作生成和 CLI 主流程。

## 主要文件

- `order.py`：CLI 主入口。
- `ai_translator.py`：调用 Anthropic SDK / OpenRouter，把自然语言转成 `TranslatedOrder`。
- `catalog.py`：生物、神器、特殊对象、难度词典和相似建议。
- `order_to_rmg.py`：把校验后的订单转成 `.h3t` 表格 cell 修改动作。
- `template_writer.py`：读取 HotA 骨架模板，应用动作并按 GBK 写出 `.h3t`。
