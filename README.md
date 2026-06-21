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
| English | 256（159 字符串 + 26 结构型 + 42 `^` 分隔 × 2 方向） |
| Bilingual | 256 |

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
python verify.py --data    # Token 完整性和分隔符检查
python verify.py --dialogue # 对话分段安全分析
python verify.py --log SMAPI-latest.txt  # SMAPI 日志分析
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
│   ├── assets-list.txt
│   └── BilingualMod/               # 脚本输出（由 .gitignore 忽略）
├── BilingualMod/                   # Content Patcher 内容包模板
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
| Token 解析 | 多源正则 `\[LocalizedText (source):(key)\]` | 提取 source 路径加载正确的 Strings 资产 |
| 对话双语 | 按 `#$e#`/`#$b#` 分段 | 每段独立做双语，避免中文被结束标记丢弃 |
| 信件双语 | `[#]` 去重 + 命令单次执行 | 只保留 EN 的 `[#]` 标记和命令，ZH 取纯文本 |
| 事件双语 | 引号感知脚本分割器 | 按 `/` 分割事件脚本（尊重引号），对 `speak`/`message` 等命令做双语 |
| `^` 分隔资产 | `EditData` + `Entries` 全值替换 | 读取 `_raw` 字段，按 `^` 分割后逐字段双语再拼接 |
| Content Patcher | 全部用 `EditData` | 所有补丁加 `When: "English, Bilingual"`，中文模式 0 补丁 |
| 验证 | `verify.py` 四合一 | Token 完整性、`^` 分隔、对话安全、SMAPI 日志 |

## 已知问题

### 表现异常

1. **信件正文纯英文** — `make_mail_bilingual()` 的正则 `%%?\[#\]` 不匹配无 `%%` 前缀的 `[#]` 标记，导致部分信件回退到简单拼接（双 `[#]` 问题未修复）。
2. **事件对话段落不对齐** — 事件 `speak` 命令内含有 `#$b#`（对话换框），双语拼接后 `#$b#` 将双语文本拆开，导致英文内容出现在前一框、中文内容在后一框。
3. **部分对话纯英文** — `Maybe now that my mother has her bus...` 等条目来源不明（可能在 `StringsFromCSFiles` 或动态生成文本中），双语化未覆盖到。

### 架构限制

4. **收获任务文本** — `ItemHarvestQuest` 的格式字符串不在任何数据资产中（`StringsFromCSFiles` 无对应条目），需要 Harmony C# 补丁才能修改。
5. **字幕 (Strings/credits)** — 非 `Dictionary<string, string>` 格式，导出失败。
6. **剧情动画事件缺失 2/45** — `IslandFarmHouse`、`Tent` 导出失败。

## 后续计划（按优先级）

### P0 — 事件对话段落对齐
- `make_event_bilingual()` 内对话文本也按 `#$b#` 分段后再做双语（同 `make_dialogue_bilingual`）

### P0 — 信件 `[#]` 无前缀匹配
- 修复 `MAIL_TITLE_RE` 正则，增加 `|\[#\]` 分支匹配无 `%%` 前缀的 `[#]` 标记

### P1 — 对话纯英文条目追踪
- 定位 `Maybe now that my mother has her bus...` 的来源资产
- 确认是什么原因导致双语化失败

### P1 — 收获任务文本（Harmony）
- 如需修复 `ItemHarvestQuest` 目标描述，需开发 C# SMAPI Mod 使用 Harmony 补丁

### P2 — Strings/credits 支持
- 研究 `Strings/credits` 格式（`List<string>`），决定是否需要覆盖

## 许可证

MIT
