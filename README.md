# Stardew Valley Bilingual Text

星露谷物语中英双语同屏显示 Mod。基于 Content Patcher 实现，无需修改游戏代码，支持实时切换显示模式。

## 功能

- **English** — 纯英文模式
- **中文** — 纯中文模式
- **Bilingual** — 双语模式，同时显示 `英文 / 中文`

通过 Generic Mod Config Menu (GMCM) 实时切换，立即生效。

## 前置要求

- [SMAPI](https://smapi.io/) 4.0+
- [Content Patcher](https://www.nexusmods.com/stardewvalley/mods/1915) 2.0+
- [Generic Mod Config Menu](https://www.nexusmods.com/stardewvalley/mods/5098)（可选，推荐用于便捷切换）
- Stardew Valley 1.6+（已包含官方中文语言包）
- 游戏 Language 必须设为 **中文**（需要中文字体渲染）

## 安装

1. 确保已安装 SMAPI、Content Patcher
2. 下载本 Mod 的 `BilingualMod` 文件夹，放入 `Stardew Valley/Mods/`
3. 启动游戏（通过 `StardewModdingAPI.exe`）
4. 在标题画面将 **Language** 设为 **中文**
5. 进入主菜单后，左下角 **Mods** 按钮 → `Stardew Valley Bilingual Text` → 选择 `Bilingual` 模式

## 当前覆盖情况

### 字符串资产（EditData + Entries，按条目替换）

| 类别 | 资产数 |
|------|--------|
| Strings/* 界面文本 | 30 |
| 对话 (Characters/Dialogue/*) | 41 |
| 日程文本 (Strings/schedules/*) | 30 |
| Data 文本 (ExtraDialogue, mail, TV/*) | 4 |
| 事件对话 (Data/Events/*) | 43 |

### 结构型数据资产（EditData + Fields，按字段替换）

| 类别 | 方法 | 条目数 |
|------|------|--------|
| 一般物品 (Data/Objects) | Fields `DisplayName`+`Description` | 807 |
| 工具 (Data/Tools) | Fields | 37 |
| 武器 (Data/Weapons) | Fields | 67 |
| 大件可制造 (Data/BigCraftables) | Fields | 182 |
| 上衣 (Data/Shirts) | Fields | 303 |
| 裤子 (Data/Pants) | Fields | 18 |
| 帽子 (Data/hats) | Fields (数值索引 5,1) | 122 |
| 靴子 (Data/Boots) | Fields (数值索引 6,1) | 18 |
| 特殊能力 (Data/Powers) | Fields | 36 |
| 饰品 (Data/Trinkets) | Fields | 8 |
| 任务 (Data/Quests) | Fields (数值索引 1,2) | 66 |
| 订婚对话 (Data/EngagementDialogue) | Fields (数值索引 0,1) | 26 |

### `^` 分隔型数据资产（EditData + Entries，全值替换）

| 类别 | 条目数 |
|------|--------|
| 成就 (Data/Achievements) | 39 |
| 秘密纸条 (Data/SecretNotes) | 38 |

### 运行时补丁统计

| 模式 | 活跃补丁数 |
|------|-----------|
| 中文 | 0（所有补丁通过 `When` 条件跳过） |
| English | 272（159 字符串 + 34 结构型 + 42 `^` 分隔 + 8 节日 × 2 方向） |
| Bilingual | 272 |

### 日历节日名称（EditData + Entries，只替换 `name` 键）

| 节日 | 资产 |
|------|------|
| 复活节 (Egg Festival) | `Data/Festivals/spring13` |
| 花舞节 (Flower Dance) | `Data/Festivals/spring24` |
| 卢奥节 (Luau) | `Data/Festivals/summer11` |
| 月光水母之舞 (Dance of the Moonlight Jellies) | `Data/Festivals/summer28` |
| 星露谷展览会 (Stardew Valley Fair) | `Data/Festivals/fall16` |
| 万灵节 (Spirit's Eve) | `Data/Festivals/fall27` |
| 冰雪节 (Festival of Ice) | `Data/Festivals/winter8` |
| 冬日星盛宴 (Feast of the Winter Star) | `Data/Festivals/winter25` |

## 从源码构建

### 1. 导出游戏文本资产

```bash
cd AssetExporter
dotnet build
```

构建后 Mod 自动部署到 `Stardew Valley/Mods/AssetExporter`。复制 `assets-list.txt` 到该目录，启动游戏一次，会在游戏目录生成 `Export_TextAssets/{en,zh}/`。

### 2. 生成双语内容包

```bash
cd BilingualModBuilder
python build_bilingual_pack.py
```

生成的 Content Patcher 包位于 `BilingualModBuilder/BilingualMod/`，复制到 `Stardew Valley/Mods/` 即可使用。

### 3. 验证

```bash
python verify.py --pack      # 检查 content.json（mail 格式、节日、对话安全）
python verify.py --data      # Token 完整性和分隔符检查
python verify.py --dialogue  # 对话分段安全分析
python verify.py --log=SMAPI-latest.txt  # SMAPI 日志分析
```

### 4. 一键构建（可选）

```powershell
.\build.ps1             # 完整构建
.\build.ps1 -Quick      # 仅构建双语包（跳过编译和导出）
.\build.ps1 -Deploy     # 仅部署到 Mods 目录
```

## 项目结构

```
stardew-bilin/
├── AssetExporter/                  # C# SMAPI Mod，用于导出游戏文本资产
│   ├── AssetExporter.csproj
│   ├── manifest.json
│   ├── ModEntry.cs                 # 遍历资产列表，按类型导出 JSON
│   └── assets-list.txt             # 需要导出的资产路径列表
├── BilingualModBuilder/            # Python 合并脚本
│   ├── build_bilingual_pack.py     # 读取中英文 JSON，生成 content.json
│   ├── parsers.py                  # 文本解析器（对话/邮件/事件/Q&A/条件）
│   ├── assets-list.txt
│   └── BilingualMod/               # 脚本输出（由 .gitignore 忽略）
├── BilingualMod/                   # Content Patcher 内容包模板
├── build.ps1                       # 一键构建脚本
│   ├── manifest.json
│   ├── config.json
│   └── content.json                # 模板（由 Python 脚本覆盖生成）
├── docs/
│   └── tech-doc.md                 # 原始技术方案文档
├── verify.py                       # 统一验证系统
├── .gitignore
└── README.md
```

## 技术设计

### 架构

```mermaid
graph TB
    subgraph "构建流水线"
        EX[AssetExporter] -->|语言切换+缓存失效| EN_RAW[Export_TextAssets/en/]
        EX -->|游戏当前 locale| ZH_RAW[Export_TextAssets/zh/]
        PY[build_bilingual_pack.py] -->|读取中英文 JSON| EN_RAW
        PY -->|读取中英文 JSON| ZH_RAW
        PY -->|字符串: EditData+Entries| BP[content.json]
        PY -->|模型型: EditData+Fields| BP
        PY -->|^分隔型: EditData+Entries| BP
        PY -->|对话: 分段双语| BP
        PY -->|信件: [#]去重| BP
        PY -->|事件: 脚本解析| BP
    end

    subgraph "运行时"
        SMAPI[SMAPI] --> CP[Content Patcher]
        CP -->|读取 content.json| BP
        CP -->|根据 LanguageMode 选择| WHEN{When 条件}
        WHEN -->|中文: 0 补丁| NATIVE[游戏原生 .zh-CN 覆盖层]
        WHEN -->|English/Bilingual| PATCH[EditData 补丁]
        PATCH -->|在 .zh-CN 覆盖层之后生效| FINAL[最终文本]
    end
```

### 关键实现细节

| 组件 | 技术 | 说明 |
|------|------|------|
| 英文导出 | `LocalizedContentManager` 切换为 `en` + SMAPI 缓存失效 | 强制加载纯英文 XNB（绕过当前中文 locale） |
| 中文导出 | `Helper.GameContent` 直接加载 | 获取合并后的中文数据（base + `.zh-CN` 覆盖层） |
| Token 解析 | 多源正则 `\[LocalizedText (source):(key)\]` | 提取 source 路径加载正确的 Strings 资产；支持 format 参数（如 `TrashCan_Description 15 → 15%`） |
| 对话双语 | 按 `#$e#`/`#$b#` 分段 | 每段独立做双语，避免中文被结束标记丢弃；支持 `$d COND#T\|F` 条件分支 |
| 信件双语 | `[#]` 去重 + 命令 `%%` 终结 | 只保留 EN 的 `[#]` 标记和命令，ZH 取纯文本；`%command` 在 ` / ` 前终结 |
| 事件双语 | 引号感知脚本分割器 | 按 `/` 分割事件脚本（尊重引号），对 `speak`/`message`/`$q/$r`/`$p` 等做双语 |
| `^` 分隔资产 | `EditData` + `Entries` 全值替换 | 读取 `_raw` 字段，按 `^` 分割后逐字段双语再拼接 |
| 日历节日 | `EditData` + `Entries` | 只替换 `name` 键，不影响 `conditions`/`mainEvent` 等 |
| Content Patcher | 全部用 `EditData` | 所有补丁加 `When: "English, Bilingual"`，中文模式 0 补丁 |
| 验证 | `verify.py` 六合一 | Token 完整性、`^` 分隔、对话安全、SMAPI 日志、mail 格式、节日名称 |

## 已知问题

### 架构限制（不可修复）

1. **Special Orders/Crop 任务 `{Crop:Text}` token** — `Strings/SpecialOrderStrings` 中的 `{Crop:Text}`、`{FishType:Text}`、`{Monster:LocalizedName}` 等是游戏运行时 token，Content Patcher 无法控制其解析行为。双语格式中 EN/ZH 两侧的 token 会解析为同一值（当前语言对应的作物/物品名），导致句内混用（如 "Harvest 100 芋头 / 收获 100 份芋头"）。

2. **海盗的任务动态文本** — `ItemDeliveryQuest` 的任务目标由 C# 代码（`"Looking for " + npcName + "'s " + itemName`）在运行时拼接，不会经过 Content Patcher 的数据流。修复需要 Harmony C# 补丁。

### 已知限制

3. **字幕 (Strings/credits)** — 非 `Dictionary<string, string>` 格式，导出失败。
4. **剧情动画事件缺失 2/45** — `IslandFarmHouse`、`Tent` 导出失败。
5. **Data/Tools Token 参数** — 垃圾桶升级（Copper/Steel/Gold/Iridium）的格式参数 token 已被 C# 导出器修复。如仍有残留，重新导出游戏资产即可。`

## 后续计划

### P1 — 验证邮件命令格式的 `\b` Unicode 问题

`MAIL_CMD_RE` 的 `\b` 在中文前不匹配（如 `%secretsanta精心`），导致 ZH 命令未被剥离。`%secretsanta` 被双面执行。需要修复正则。

### P2 — Strings/credits 支持

研究 `Strings/credits` 格式（`List<string>`），决定是否需要覆盖。

### P2 — 缺失 2 事件

`IslandFarmHouse`、`Tent` 导出失败，研究原因。

### P3 — 海盗任务 Harmony

如需修复 `ItemDeliveryQuest` 动态拼接文本，需开发 C# SMAPI Mod 使用 Harmony 补丁。优先级低，因单条任务影响有限。

## 许可证

MIT
