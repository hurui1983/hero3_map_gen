# HoMM3 / HotA 随机地图模板生成器

把结构化"点菜"参数转换成 HotA 随机地图模板 `.h3t`。**纯本地, 无 LLM/网络依赖**。

自然语言交互发生在 Claude Code 对话里 —— 让 Claude 把"我想要 X"
拆成 `--creatures`/`--artifacts`/`--difficulty` 等具体参数, 再调用本 CLI。

## 用法

```bash
python3 order.py \
    --creatures 圣龙,水晶龙,仙龙,锈龙 \
    --artifacts 末日之刃,天使联盟 \
    --difficulty hard --players 4 \
    --name "AI 四大龙 末日之刃 天使联盟"
```

生成的 `.h3t` 写到:

```
/Applications/英雄无敌3：二合一.app/Contents/drive_c/game/HotA_RMGTemplates/
```

文件名以 `ai_` 开头. 重开游戏内的随机地图设置窗口, 就能在模板列表
里看到 `AI ...` 开头的模板.

## CLI 参数

| 参数 | 说明 | 例子 |
|---|---|---|
| `--creatures` | 逗号分隔的生物中文名 | `金龙,圣龙` |
| `--artifacts` | 逗号分隔的神器中文名 | `末日之刃,天使联盟` |
| `--specials` | 特殊对象 (圣杯等) | `圣杯` |
| `--difficulty` | `easy` / `normal` / `hard` | `hard` |
| `--players` | 玩家数 2~8 | `4` |
| `--map-size` | `S`/`M`/`L`/`XL` (当前不写入, 仅记录) | `L` |
| `--name` | 模板显示名 (默认自动衍生) | `"AI 四大龙"` |
| `--description` | 模板描述 | `"4 人强敌对战"` |
| `--list` | 列出已生成的所有 AI 模板 | - |
| `--clean` | 删除所有 AI 模板 | - |

所有 catalog 命中靠 `catalog.py` 的中文标准名 + 别名. 不在词典里
会直接失败并给出相似建议, 不会瞎写模板.

## 退出码

```
0 成功
1 CLI 用法错误 (没传任何字段)
3 输入有未识别项 (生物/神器/特殊对象/难度/玩家数/地图大小)
```

## 已支持写入的 HotA RMG 字段

- 模板名和描述 (`Pack.Name` / `Map.Name` / `Pack.Description`)
- 野外守军强度 (`Zone.Strength`, `easy`/`normal`/`hard` →
  `weak`/`avg`/`strong`)
- 必出神器 (`Map.Artifacts`, 例: 末日之刃 `+128`, 天使联盟 `+129`)

## 已知限制

- **难度字段是"野外守军", 不是"游戏难度"**. `Zone.Strength` 控制
  地图上守军点/宝物点刷出的怪兵等级 (strong → 7 级单位概率上升),
  跟玩家在游戏开局选的难度 (Easy/Normal/Hard/Expert/Impossible,
  影响初始资源和 AI 加成) 完全无关.
- **指定具体生物做不到**. HotA RMG 没有 "某只龙必出地图" 的字段.
  `--creatures 圣龙,水晶龙` 只是 catalog 识别和日志记录, **不写入
  任何 RMG 字段**. 写"四大龙"实际上等价于 `--difficulty hard`,
  靠 strong 守军间接堆出 7 级龙. 想强保证某只龙出现请用地图编辑器
  手放, 这是 RMG 模板格式的硬限制.
- **`--players` 不写入**. 实验确认: Jebus Cross 骨架的 player 字段
  改成 `(1,4,4,4)` 强锁 4 人会让 HotA 拒绝创建. 系统模板里没有任何
  "四值全相等" 的写法 (Skirmish(M)=1/2 2/2, mt_Antares=1/4 1/4,
  Jebus Cross=1/4 2/4), 这组合 RMG 不接受. 骨架本来就支持 2-4 人,
  在游戏 UI 自己选玩家数.
- **`--map-size` 不写入**. 骨架是 5 zone 设计, 强制 M/S 会装不下.
  原值 `9/16` = 允许 L/XL, 玩家在 UI 选.
- 圣杯作为特殊对象识别, 由 RMG 默认方尖碑机制处理, 不额外写字段.
- 组合神器直接按全局 artifact RMG ID 写入 `Map.Artifacts`,
  不使用 `Combo Arts` 列. 已在游戏内验证 `+128 +129` 可加载.
- HotA 不从子目录加载 RMG 模板, 生成文件必须在 `HotA_RMGTemplates`
  根目录.

## 测试

```bash
python3 -m unittest order_test catalog_test order_to_rmg_test
```

当前测试覆盖 catalog 解析、严格校验、RMG 字段动作生成和 CLI 主流程.

## 主要文件

- `order.py`: CLI 主入口 + `RawOrder` + `_validate()`
- `catalog.py`: 生物、神器、特殊对象、难度词典和相似建议
- `order_to_rmg.py`: 把校验后的订单转成 `.h3t` 表格 cell 修改动作
- `template_writer.py`: 读取 HotA 骨架模板, 应用动作并按 GBK 写出 `.h3t`
