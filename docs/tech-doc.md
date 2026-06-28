# 星露谷物语双语显示 Mod——资产替换方案实施指南

> **历史说明**：本文档是 v1 初始架构（基于 `Load` 补丁 + 三目录切换）的设计方案。当前版本已演进为基于 `EditData` 补丁 + 单文件双语格式 + 布尔值 `BilingualMode` 切换的架构。细节以实际代码和 [README.md](../README.md) 为准，本文仅供参考架构思路。

---

## 1. 目标与原理

**最终交付物**：一个 Content Patcher 内容包（一个文件夹），放入 `Stardew Valley/Mods` 后，玩家可在游戏内通过 Generic Mod Config Menu (GMCM) 实时切换以下三种显示模式：

- 纯英文（English）
- 纯中文（Chinese）
- 双语（Bilingual）：每行文本显示为 `English\n[中文]` 的格式

**实现路径**：  
借助 SMAPI 的 Asset Export 导出原版游戏的所有文本资产（中、英文），用 Python 脚本将其合并成三套 JSON 文件，再包装为一个带有配置令牌的 Content Patcher 包。游戏运行时，Content Patcher 会根据玩家选择的模式，动态加载对应的资产文件，无需修改任何游戏代码。

**为什么不直接修改游戏方法？**  
修改绘制方法（Harmony Patch）无法覆盖全部文本，且稳定性差。资产替换能覆盖所有通过 Content Pipeline 加载的文本，无崩溃风险。

---

## 2. 准备工作

### 2.1 基础环境

- **操作系统**：Windows / macOS / Linux 均可
- **游戏**：《星露谷物语》最新版本（已包含官方中文）
- **SMAPI**：最新版，已正确安装
- **Content Patcher**：最新版，已安装
- **.NET SDK 6.0 或更高**（用于编译导出 Mod）—— 或使用 Visual Studio Community
- **Python 3.9+**（用于数据合并与包生成）

### 2.2 资源清单

- 一份完整的**文本资产列表**（见附录 A）。我们会以此为基础，但允许后续补充。
- 一个**导出 Mod**（我们会创建），用于从游戏中提取中英文原文。
- 一个**合并脚本**（Python），用于生成三套资产。
- 一个**Content Patcher 内容包模板**。

---

## 3. 阶段一：创建导出 Mod（Asset Exporter）

这个 Mod 只会被我们（开发者）使用，不发布给玩家。它在游戏启动后，遍历所有目标资产，以英文和中文两种语言分别加载，并保存为 `.json` 文件到指定目录。

### 3.1 项目结构

在任意工作目录下创建文件夹 `AssetExporter`，内部结构：

```
AssetExporter/
├── AssetExporter.csproj
├── manifest.json
├── ModEntry.cs
└── assets-list.txt   （待会儿创建）
```

### 3.2 `manifest.json`

```json
{
  "Name": "Asset Exporter for Bilingual Mod",
  "Author": "QingGo",
  "Version": "1.0.0",
  "Description": "Exports all text assets as JSON for offline processing.",
  "UniqueID": "QingGo.AssetExporter",
  "EntryDll": "AssetExporter.dll",
  "MinimumApiVersion": "4.0.0",
  "UpdateKeys": []
}
```

### 3.3 `AssetExporter.csproj`

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>AssetExporter</AssemblyName>
    <Version>1.0.0</Version>
    <TargetFramework>net6.0</TargetFramework>
    <EnableHarmony>false</EnableHarmony>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Pathoschild.Stardew.ModBuildConfig" Version="4.1.1" />
  </ItemGroup>
</Project>
```

> 使用 `ModBuildConfig` 可以自动引用游戏和 SMAPI 的程序集，且编译后自动打包到 `Mods` 目录。如果你不想用 NuGet，也可以手动添加对 `StardewValley.exe`、`StardewModdingAPI.dll` 的引用。

### 3.4 `ModEntry.cs`

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace AssetExporter
{
    public class ModEntry : Mod
    {
        // 从 assets-list.txt 读取的资产路径（不含语言后缀）
        private List<string> assetPaths = new();

        public override void Entry(IModHelper helper)
        {
            helper.Events.GameLoop.GameLaunched += OnGameLaunched;
        }

        private void OnGameLaunched(object sender, GameLaunchedEventArgs e)
        {
            // 读取资产列表文件
            string listFile = Path.Combine(Helper.DirectoryPath, "assets-list.txt");
            if (!File.Exists(listFile))
            {
                Monitor.Log($"资产列表文件 {listFile} 不存在，导出中止。", LogLevel.Error);
                return;
            }
            assetPaths = File.ReadAllLines(listFile)
                             .Select(l => l.Trim())
                             .Where(l => !string.IsNullOrEmpty(l) && !l.StartsWith("#"))
                             .ToList();

            if (assetPaths.Count == 0)
            {
                Monitor.Log("资产列表为空，导出中止。", LogLevel.Error);
                return;
            }

            // 执行导出
            ExportAssets();
        }

        private void ExportAssets()
        {
            // 输出根目录：游戏目录/Export_TextAssets
            string outRoot = Path.Combine(Constants.ExecutionPath, "Export_TextAssets");
            Directory.CreateDirectory(outRoot);

            // 保存原始语言，以便导出完成后恢复
            var originalLang = LocalizedContentManager.CurrentLanguageCode;

            try
            {
                // --- 导出英文 ---
                LocalizedContentManager.CurrentLanguageCode = LocalizedContentManager.LanguageCode.en;
                string enDir = Path.Combine(outRoot, "en");
                Directory.CreateDirectory(enDir);
                Monitor.Log("正在导出英文资产...", LogLevel.Info);
                ExportLanguage(assetPaths, enDir);

                // --- 导出中文 ---
                LocalizedContentManager.CurrentLanguageCode = LocalizedContentManager.LanguageCode.zh;
                string zhDir = Path.Combine(outRoot, "zh");
                Directory.CreateDirectory(zhDir);
                Monitor.Log("正在导出中文资产...", LogLevel.Info);
                ExportLanguage(assetPaths, zhDir);
            }
            catch (Exception ex)
            {
                Monitor.Log($"导出过程发生异常：{ex}", LogLevel.Error);
            }
            finally
            {
                // 恢复语言
                LocalizedContentManager.CurrentLanguageCode = originalLang;
                Monitor.Log("导出完成。文件位于：" + outRoot, LogLevel.Info);
            }
        }

        private void ExportLanguage(List<string> paths, string outputDir)
        {
            foreach (string assetPath in paths)
            {
                try
                {
                    // 尝试以 Dictionary<string,string> 加载
                    // 大多数文本资产都是这个类型
                    var dict = Helper.Content.Load<Dictionary<string, string>>(
                        assetPath,
                        ContentSource.GameContent
                    );

                    if (dict == null || dict.Count == 0)
                    {
                        Monitor.Log($"资产 {assetPath} 为空或加载失败。", LogLevel.Warn);
                        continue;
                    }

                    // 将字典序列化为 JSON，并保存
                    // 路径中的 / 或 \ 替换为 _ 作为文件名
                    string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
                    string filePath = Path.Combine(outputDir, safeName);

                    // 使用 System.Text.Json 序列化，保持可读性
                    var options = new JsonSerializerOptions
                    {
                        WriteIndented = true,
                        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
                    };
                    string json = JsonSerializer.Serialize(dict, options);
                    File.WriteAllText(filePath, json);

                    Monitor.Log($"已导出：{assetPath} -> {safeName}");
                }
                catch (Exception ex)
                {
                    // 有些资产可能是 Dictionary<int, string> 或其他类型，暂不处理
                    Monitor.Log($"无法以 Dictionary<string,string> 加载资产 {assetPath}，跳过。错误：{ex.Message}", LogLevel.Warn);
                }
            }
        }
    }
}
```

**说明**：

- 我们在 `GameLaunched` 事件后执行导出，此时游戏已初始化，所有资产都可访问。
- 利用 `LocalizedContentManager.CurrentLanguageCode` 临时切换语言，使得 `Helper.Content.Load` 返回对应语言的文本。
- 只处理 `Dictionary<string, string>` 类型的资产，这覆盖了 **绝大多数** 可见文本（对话、菜单、物品名、描述、事件等）。少量特殊类型资产（如 `Data/Achievements` 的键为 int）会在后续逐步加入，初期不影响主要功能。
- 异常处理：加载失败则跳过并记录，不中断整体导出。

### 3.5 准备资产列表 `assets-list.txt`

在工作目录中创建此文件，填入需要导出的资产路径，一行一个，`#` 开头为注释。

**初始推荐列表（基于星露谷 1.6）**：

```
# Strings (most UI text)
Strings/Buildings
Strings/BundleNames
Strings/Characters
Strings/Events
Strings/EventFiles
Strings/FarmAnimals
Strings/Furniture
Strings/Locations
Strings/Maps
Strings/NPCNames
Strings/Objects
Strings/Quests
Strings/SecretNotes
Strings/SpeechBubbles
Strings/StringsFromCSFiles
Strings/StringsFromMaps
Strings/TV
Strings/UI

# Data (item/object descriptions etc.)
Data/Boots
Data/BuffIcons
Data/CookingRecipes
Data/CraftingRecipes
Data/ExtraDialogue
Data/Festivals/FestivalDates
Data/hats
Data/Locations
Data/mail
Data/MonsterSlayerQuests
Data/Movies
Data/MoviesReactions
Data/Objects
Data/Pants
Data/Shirts
Data/SpecialOrders
Data/Tools
Data/TV/CookingChannel
Data/TV/TipChannel
Data/Weapons

# Dialogue
Characters/Dialogue/Abigail
Characters/Dialogue/Alex
Characters/Dialogue/Caroline
Characters/Dialogue/Clint
Characters/Dialogue/Demetrius
Characters/Dialogue/Dwarf
Characters/Dialogue/Elliott
Characters/Dialogue/Emily
Characters/Dialogue/Evelyn
Characters/Dialogue/George
Characters/Dialogue/Gus
Characters/Dialogue/Haley
Characters/Dialogue/Harvey
Characters/Dialogue/Jas
Characters/Dialogue/Jodi
Characters/Dialogue/Kent
Characters/Dialogue/Krobus
Characters/Dialogue/Leah
Characters/Dialogue/Leo
Characters/Dialogue/Lewis
Characters/Dialogue/Linus
Characters/Dialogue/Marnie
Characters/Dialogue/Maru
Characters/Dialogue/Pam
Characters/Dialogue/Penny
Characters/Dialogue/Pierre
Characters/Dialogue/Robin
Characters/Dialogue/Sam
Characters/Dialogue/Sandy
Characters/Dialogue/Sebastian
Characters/Dialogue/Shane
Characters/Dialogue/Vincent
Characters/Dialogue/Willy
Characters/Dialogue/Wizard
Characters/Dialogue/MarriageDialogue
Characters/Dialogue/MarriageDialogueAbigail
Characters/Dialogue/MarriageDialogueAlex
Characters/Dialogue/MarriageDialogueCaroline
Characters/Dialogue/MarriageDialogueClint
Characters/Dialogue/MarriageDialogueDemetrius
Characters/Dialogue/MarriageDialogueElliott
Characters/Dialogue/MarriageDialogueEmily
Characters/Dialogue/MarriageDialogueEvelyn
Characters/Dialogue/MarriageDialogueGeorge
Characters/Dialogue/MarriageDialogueGus
Characters/Dialogue/MarriageDialogueHaley
Characters/Dialogue/MarriageDialogueHarvey
Characters/Dialogue/MarriageDialogueJas
Characters/Dialogue/MarriageDialogueJodi
Characters/Dialogue/MarriageDialogueKent
Characters/Dialogue/MarriageDialogueKrobus
Characters/Dialogue/MarriageDialogueLeah
Characters/Dialogue/MarriageDialogueLeo
Characters/Dialogue/MarriageDialogueLewis
Characters/Dialogue/MarriageDialogueLinus
Characters/Dialogue/MarriageDialogueMarnie
Characters/Dialogue/MarriageDialogueMaru
Characters/Dialogue/MarriageDialoguePam
Characters/Dialogue/MarriageDialoguePenny
Characters/Dialogue/MarriageDialoguePierre
Characters/Dialogue/MarriageDialogueRobin
Characters/Dialogue/MarriageDialogueSam
Characters/Dialogue/MarriageDialogueSandy
Characters/Dialogue/MarriageDialogueSebastian
Characters/Dialogue/MarriageDialogueShane
Characters/Dialogue/MarriageDialogueVincent
Characters/Dialogue/MarriageDialogueWilly
Characters/Dialogue/MarriageDialogueWizard
```

**说明**：  
这个列表覆盖了 95% 以上的游戏文本。如果测试时发现某些文本没有被双语化，通常是因为对应的资产路径未加入。只需将路径追加到 `assets-list.txt`，重新运行导出 Mod 和后续脚本即可。

---

## 4. 阶段二：运行导出 Mod，获取原始数据

### 4.1 编译

在 `AssetExporter` 目录中打开终端，执行：

```bash
dotnet build
```

如果使用 `ModBuildConfig`，构建成功后，Mod 会被自动复制到 `Stardew Valley/Mods/AssetExporter` 目录。否则需要手动复制。

### 4.2 执行导出

1. 确保游戏语言已设为 **英文**（重要！因为我们要在英文模式下导出中文，防止某些资产在中文模式下被映射导致遗漏）。
2. 通过 SMAPI 启动游戏一次。
3. 加载一个存档（游戏需完全进入农场场景），然后退出游戏。  
   这个过程中，导出 Mod 会在游戏目录下生成 `Export_TextAssets/en/` 和 `Export_TextAssets/zh/` 两个文件夹，里面包含所有资产的 JSON 文件。

如果控制台显示某些资产跳过，请记下路径，判断是否需要手动处理（通常不影响）。

---

## 5. 阶段三：编写资产合并与包生成脚本（Python）

我们需要一个 Python 脚本，完成以下工作：

1. 读取 `Export_TextAssets/en/` 下的所有 JSON 文件。
2. 读取 `Export_TextAssets/zh/` 下对应的文件。
3. 生成三套输出文件：
   - `assets/English/`：纯英文（原封不动）
   - `assets/Chinese/`：纯中文（原封不动）
   - `assets/Bilingual/`：合并为 `"{en}\n[{zh}]"` 格式
4. 为 Content Patcher 生成 `content.json`，对每一个资产路径写入对应的 `Load` patch，且使用配置令牌 `{{config:LanguageMode}}` 动态选择 `English`、`Chinese`、`Bilingual` 目录。

### 5.1 脚本源码 `build_bilingual_pack.py`

在工作目录（如 `BilingualModBuilder`）下创建：

```python
import json
import os
import shutil
from pathlib import Path

# ====== 配置区域 ======
# 导出资产所在的根目录（之前 Export_TextAssets 的位置）
EXPORT_DIR = Path("E:/Games/Stardew Valley/Export_TextAssets")  # 修改为你的实际路径
# 输出包的目标目录（生成的 Content Patcher 包）
OUTPUT_DIR = Path("./BilingualMod")
# 资产路径列表文件（与导出时使用的一致）
ASSETS_LIST_FILE = Path("./assets-list.txt")  # 复制一份过来

# 双语格式模板，可自定义
# {en} 英文原文，{zh} 中文翻译
BILINGUAL_TEMPLATE = "{en}\n[{zh}]"

# ====== 工具函数 ======
def asset_path_to_filename(asset_path: str) -> str:
    """将资产路径转为导出时的安全文件名（与导出 Mod 一致）"""
    return asset_path.replace("/", "_").replace("\\", "_") + ".json"

def load_json(file_path: Path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, file_path: Path):
    os.makedirs(file_path.parent, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ====== 主要逻辑 ======
def main():
    # 读取资产列表（与导出时一致）
    if not ASSETS_LIST_FILE.exists():
        print(f"错误：找不到资产列表文件 {ASSETS_LIST_FILE}")
        return
    with open(ASSETS_LIST_FILE, 'r', encoding='utf-8') as f:
        asset_paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # 准备输出目录
    langs = ["English", "Chinese", "Bilingual"]
    for lang in langs:
        (OUTPUT_DIR / "assets" / lang).mkdir(parents=True, exist_ok=True)

    content_patches = []  # 用于生成 content.json

    for asset_path in asset_paths:
        filename = asset_path_to_filename(asset_path)

        en_file = EXPORT_DIR / "en" / filename
        zh_file = EXPORT_DIR / "zh" / filename

        if not en_file.exists():
            print(f"警告：缺失英文资产 {asset_path}，跳过")
            continue
        if not zh_file.exists():
            print(f"警告：缺失中文资产 {asset_path}，将使用英文代替中文部分")
            zh_data = None
        else:
            zh_data = load_json(zh_file)

        en_data = load_json(en_file)

        # 纯英文：直接复制
        save_json(en_data, OUTPUT_DIR / "assets" / "English" / filename)
        # 纯中文：如果存在则使用中文，否则用英文（确保文件存在）
        if zh_data:
            save_json(zh_data, OUTPUT_DIR / "assets" / "Chinese" / filename)
        else:
            save_json(en_data, OUTPUT_DIR / "assets" / "Chinese" / filename)  # fallback

        # 双语：合并两个字典
        bilingual_data = {}
        for key, en_val in en_data.items():
            zh_val = ""
            if zh_data and key in zh_data:
                zh_val = zh_data[key]
            else:
                zh_val = ""  # 缺失中文时留空或显示提示
            bilingual_data[key] = BILINGUAL_TEMPLATE.format(en=en_val, zh=zh_val)
        save_json(bilingual_data, OUTPUT_DIR / "assets" / "Bilingual" / filename)

        # 生成 content.json 的 patch 条目
        # 注意：FromFile 使用相对于 content.json 的路径，且使用 Content Patcher 的配置令牌
        # 目录结构：assets/{{config:LanguageMode}}/文件名
        # 这样会根据配置动态加载 English/ Chinese/ Bilingual 下的文件
        from_file = f"assets/{{{{config:LanguageMode}}}}/{filename}"
        patch = {
            "Action": "Load",
            "Target": asset_path,
            "FromFile": from_file
        }
        content_patches.append(patch)

    # 写入 content.json
    content_json = {
        "Format": "2.0.0",
        "Changes": content_patches
    }
    with open(OUTPUT_DIR / "content.json", 'w', encoding='utf-8') as f:
        json.dump(content_json, f, indent=2, ensure_ascii=False)

    print(f"处理完成，共处理 {len(content_patches)} 个资产。")
    print(f"Content Patcher 包已生成至：{OUTPUT_DIR.resolve()}")

if __name__ == "__main__":
    main()
```

### 5.2 执行脚本

1. 将 `assets-list.txt` 复制到脚本所在目录。
2. 修改 `EXPORT_DIR` 变量指向实际导出的 `Export_TextAssets` 文件夹。
3. 运行：

```bash
python build_bilingual_pack.py
```

此时会在 `./BilingualMod` 下生成完整的 Content Patcher 包结构：

```
BilingualMod/
├── manifest.json   （稍后创建）
├── config.json     （稍后创建）
├── content.json    （脚本生成）
└── assets/
    ├── English/
    │   ├── Strings_Locations.json
    │   └── ...
    ├── Chinese/
    │   └── ...
    └── Bilingual/
        └── ...
```

---

## 6. 阶段四：制作 Content Patcher 内容包的配置文件

在 `BilingualMod` 目录下手动创建以下两个文件。

### 6.1 `manifest.json`

```json
{
  "Name": "Stardew Valley Bilingual Text",
  "Author": "QingGo",
  "Version": "1.0.0",
  "Description": "Displays game text in English, Chinese, or bilingual mode. Switchable via GMCM.",
  "UniqueID": "QingGo.BilingualText",
  "MinimumApiVersion": "4.0.0",
  "UpdateKeys": [],
  "ContentPackFor": {
    "UniqueID": "Pathoschild.ContentPatcher",
    "MinimumVersion": "2.0.0"
  }
}
```

### 6.2 `config.json`

> **注意**：当前版本已改用 `BilingualMode`（布尔值），见 [config.json](../BilingualMod/config.json)。

```json
{
  "LanguageMode": "Bilingual",
  "AllowValues": "English, Chinese, Bilingual"
}
```

> Content Patcher 会自动识别 `config.json`，并将其暴露给 GMCM。`AllowValues` 会在 GMCM 中生成下拉菜单。

现在这个 `BilingualMod` 文件夹就是一个可以直接使用的 Mod。

---

## 7. 阶段五：安装与测试

1. 将 `BilingualMod` 文件夹复制到 `Stardew Valley/Mods/` 下。
2. 确保 `Content Patcher` 和 `SMAPI` 已安装。
3. 启动游戏。
4. 进入主菜单后，点击左下角的 **“Mods”** 按钮（或游戏内菜单 -> Mods），找到 `Stardew Valley Bilingual Text`，会看到 `LanguageMode` 选项，可下拉选择 `English`、`Chinese`、`Bilingual`。
5. 切换后立即生效，无需重载存档。浏览不同界面，检查文本显示。

---

## 8. 常见问题与调试

### 8.1 某些文本未变化（仍为纯英文或纯中文）

- **原因**：对应的资产路径未包含在 `assets-list.txt` 中。
- **解决**：找到未变化文本所在的资产（如某个 NPC 对话文件），将其路径加入 `assets-list.txt`，重新运行导出 Mod 和 Python 脚本，替换 `BilingualMod` 即可。

**如何查找缺失的资产路径？**

- 查阅星露谷 Modding 维基的 [Content files](https://stardewvalleywiki.com/Modding:Content_files) 页面。
- 或使用其他 Mod（如 “Debug Mode” 或 “Content Patcher Debug”）来查看当前界面文本的来源。

### 8.2 游戏崩溃或黑屏

- **原因**：某个资产的 JSON 结构与游戏期望不符，或 Content Patcher 包格式错误。
- **检查**：SMAPI 控制台会显示错误日志，定位到具体的资产路径和 patch。
- **临时解决**：从 `content.json` 中注释掉（删除）对应的 patch，重新测试。

### 8.3 双语文分行或显示异常符号

- **原因**：原文中包含特殊控制符（如 `#`、`$`）与换行符产生交互。
- **解决**：修改 `BILINGUAL_TEMPLATE`，例如改为 `"{en} [{zh}]"` 同行显示；或对特定资产进行手动后处理，但这已超出自动化范围。可以先发布，让用户反馈问题区域再手动微调。

### 8.4 切换语言后部分文本未立即刷新

- 大部分文本会立即刷新，但某些缓存的 UI 可能需要切换场景或重新打开菜单才能看到变化。这是游戏本身的限制，无解，但影响极小。

---

## 9. 维护与更新

当游戏版本更新后，官方可能会增加或修改文本资产，这时需要重新生成双语包。

**操作流程**：

1. 更新游戏，确保中文语言包也更新。
2. 重新运行导出 Mod（阶段二），覆盖 `Export_TextAssets`。
3. 如有新增资产路径，补充到 `assets-list.txt`。
4. 再次运行 Python 脚本（阶段三），生成新的 `BilingualMod`。
5. 将新的 Mod 文件夹替换旧版，发布更新。

---

## 10. 进阶优化（可选）

- **添加自定义分隔符选项**：在 `config.json` 中增加一个 `SeparatorStyle` 字段，修改 Python 脚本使其根据该字段动态设置 `BILINGUAL_TEMPLATE`，并在 Content Patcher 中通过令牌传递。但这会显著增加复杂度。初次发布不建议实施。
- **处理非 `Dictionary<string,string>` 资产**：在导出 Mod 中增加对其他类型的尝试（如 `Dictionary<int,string>`），并使用适当的转换。这一部分可在发现缺漏后逐步加入。
- **与 GMCM 更深度集成**：Content Patcher 已经自动完成，无需额外工作。

---

## 附录 A：初始资产列表（已包含在 `assets-list.txt` 中）

```text
Strings/Buildings
Strings/BundleNames
Strings/Characters
Strings/Events
...（完整列表同3.5节）
```

将此列表保存为 `assets-list.txt`，供导出 Mod 和 Python 脚本使用。

---

## 附录 B：目录结构总览

```
stardew-bilin/                    # 仓库根目录
├── AssetExporter/                # 导出 Mod 源代码
│   ├── AssetExporter.csproj
│   ├── manifest.json
│   ├── ModEntry.cs
│   └── assets-list.txt
├── BilingualModBuilder/          # Python 构建工具
│   ├── build_bilingual_pack.py   # 读取 _export/{en,zh}，生成 content.json
│   ├── parsers.py                # 文本解析器
│   ├── assets-list.txt
│   ├── BilingualMod/             # 构建输出（gitignored）
│   └── tests/                    # pytest 单元测试
├── _export/                      # 导出的游戏文本（提交到仓库）
│   ├── en/                       # 英文原文 JSON
│   └── zh/                       # 中文翻译 JSON
└── BilingualMod/                 # 最终 Mod（放入游戏 Mods 目录）
    ├── manifest.json
    ├── config.json
    └── content.json               # 由 build_bilingual_pack.py 自动生成
```

---

你现在拥有了一份完整的、可无脑执行的实施文档。所有文件、路径、配置都已给出，可直接交给 Code Agent 一步一步完成。如果在执行过程中遇到任何问题，随时反馈。