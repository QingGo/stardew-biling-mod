using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using StardewValley.GameData.Objects;
using StardewValley.GameData.Tools;
using StardewValley.GameData.Weapons;
using StardewValley.GameData.Shirts;
using StardewValley.GameData.Pants;
using StardewValley.GameData.BigCraftables;
using StardewValley.GameData.Powers;
using StardewValley.GameData;

namespace AssetExporter
{
    public class ModConfig
    {
        public string[] Languages { get; set; } = { "en", "zh" };
    }

    public class ModEntry : Mod
    {
        private ModConfig _config;
        private static readonly string DebugLogPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "StardewValley", "export-debug.log");
        private static void DebugLog(string msg)
        {
            try { File.AppendAllText(DebugLogPath, $"[{DateTime.Now:HH:mm:ss}] {msg}\n"); } catch { }
        }

        private List<string> stringAssetPaths = new();
        private List<string> dataAssetPaths = new();

        private static readonly Dictionary<string, string> DataToStringsAsset = new()
        {
            ["Data/Objects"] = "Strings/Objects",
            ["Data/Tools"] = "Strings/Tools",
            ["Data/Weapons"] = "Strings/Weapons",
            ["Data/Shirts"] = "Strings/Shirts",
            ["Data/Pants"] = "Strings/Pants",
            ["Data/BigCraftables"] = "Strings/BigCraftables",
            ["Data/Powers"] = "Strings/1_6_Strings",
            ["Data/Trinkets"] = "Strings/Objects",
        };

        private static readonly Regex TokenRegex = new(
            @"\[LocalizedText\s+([\w\\]+):(.+?)\]",
            RegexOptions.Compiled
        );

        private readonly Dictionary<string, Dictionary<string, string>> _stringsLoadCache = new();

        private static readonly Dictionary<string, LocalizedContentManager.LanguageCode> LangCodeMap = new()
        {
            ["en"] = LocalizedContentManager.LanguageCode.en,
            ["zh"] = LocalizedContentManager.LanguageCode.zh,
            ["de"] = LocalizedContentManager.LanguageCode.de,
            ["ja"] = LocalizedContentManager.LanguageCode.ja,
            ["fr"] = LocalizedContentManager.LanguageCode.fr,
            ["ko"] = LocalizedContentManager.LanguageCode.ko,
            ["tr"] = LocalizedContentManager.LanguageCode.tr,
            ["es"] = LocalizedContentManager.LanguageCode.es,
            ["pt"] = LocalizedContentManager.LanguageCode.pt,
            ["ru"] = LocalizedContentManager.LanguageCode.ru,
            ["hu"] = LocalizedContentManager.LanguageCode.hu,
            ["it"] = LocalizedContentManager.LanguageCode.it,

        };

        public override void Entry(IModHelper helper)
        {
            _config = helper.ReadConfig<ModConfig>();
            helper.Events.GameLoop.GameLaunched += OnGameLaunched;
        }

        private void OnGameLaunched(object sender, GameLaunchedEventArgs e)
        {
            DebugLog($"配置语言: {string.Join(", ", _config.Languages)}");
            Monitor.Log($"导出语言: {string.Join(", ", _config.Languages)}", LogLevel.Info);

            foreach (var lang in _config.Languages)
            {
                if (!LangCodeMap.ContainsKey(lang))
                {
                    Monitor.Log($"不支持的语言代码: {lang}，跳过。支持: {string.Join(", ", LangCodeMap.Keys)}", LogLevel.Warn);
                    return;
                }
            }

            string listFile = Path.Combine(Helper.DirectoryPath, "assets-list.txt");
            if (!File.Exists(listFile))
            {
                Monitor.Log($"资产列表文件 {listFile} 不存在，导出中止。", LogLevel.Error);
                return;
            }

            var allLines = File.ReadAllLines(listFile)
                               .Select(l => l.Trim())
                               .Where(l => !string.IsNullOrEmpty(l) && !l.StartsWith("#"))
                               .ToList();

            var textDataAssets = new HashSet<string>
            {
                "Data/ExtraDialogue", "Data/mail",
                "Data/TV/CookingChannel", "Data/TV/TipChannel"
            };

            foreach (var path in allLines)
            {
                if (textDataAssets.Contains(path) || path.StartsWith("Data/Events/") || path.StartsWith("Data/Festivals/"))
                    stringAssetPaths.Add(path);
                else if (path.StartsWith("Data/"))
                    dataAssetPaths.Add(path);
                else
                    stringAssetPaths.Add(path);
            }

            if (stringAssetPaths.Count == 0 && dataAssetPaths.Count == 0)
            {
                Monitor.Log("资产列表为空，导出中止。", LogLevel.Error);
                return;
            }

            ExportAssets();
        }

        // ====== 加载路径 ======

        private T LoadLanguage<T>(string assetPath, string langCode)
        {
            DebugLog($"LoadLanguage<{typeof(T).Name}>(\"{assetPath}\", \"{langCode}\")");
            var origLang = LocalizedContentManager.CurrentLanguageCode;
            LocalizedContentManager.CurrentLanguageCode = LangCodeMap[langCode];

            InvalidateAllCaches();

            var result = Helper.GameContent.Load<T>(assetPath);

            LocalizedContentManager.CurrentLanguageCode = origLang;

            // Verify: for Chinese, check we got CJK characters
            if (langCode == "zh" && result is Dictionary<string, string> dict && dict.Count > 0)
            {
                var sample = dict.First();
                bool hasChinese = sample.Value.Any(c => c > 0x2FF);
                if (!hasChinese)
                {
                    DebugLog($"  ⚠ LoadLanguage(\"{assetPath}\", \"zh\") — NO Chinese found! \"{sample.Key}\"=\"{sample.Value.Substring(0, Math.Min(60, sample.Value.Length))}\"");
                    LocalizedContentManager.CurrentLanguageCode = LangCodeMap["zh"];
                    InvalidateAllCaches();
                    result = Helper.GameContent.Load<T>(assetPath);
                    LocalizedContentManager.CurrentLanguageCode = origLang;
                }
            }

            return result;
        }

        private void InvalidateAllCaches()
        {
            Helper.GameContent.InvalidateCache<Dictionary<string, string>>();
            Helper.GameContent.InvalidateCache<Dictionary<int, string>>();
            // Model types
            Helper.GameContent.InvalidateCache<Dictionary<string, ObjectData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, ToolData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, WeaponData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, ShirtData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, PantsData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, BigCraftableData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, PowersData>>();
            Helper.GameContent.InvalidateCache<Dictionary<string, TrinketData>>();
        }

        // ====== 主流程 ======

        private void ExportAssets()
        {
            string outRoot = Path.Combine(Constants.GamePath, "Export_TextAssets");
            var langDirs = new Dictionary<string, string>();
            foreach (var lang in _config.Languages)
            {
                var dir = Path.Combine(outRoot, lang);
                Directory.CreateDirectory(dir);
                langDirs[lang] = dir;
            }

            Monitor.Log("=== 导出开始 ===", LogLevel.Info);

            var validation = new ExportValidation(Monitor, _config.Languages);

            if (stringAssetPaths.Count > 0)
            {
                Monitor.Log("--- 字符串资产 ---", LogLevel.Info);
                ExportStringAssets(stringAssetPaths, langDirs, validation);
            }

            if (dataAssetPaths.Count > 0)
            {
                Monitor.Log("--- Data 资产（显示名+描述）---", LogLevel.Info);
                ExportDataAssets(dataAssetPaths, langDirs, validation);
            }

            validation.Report();

            Monitor.Log("=== 导出完成 ===", LogLevel.Info);
            Monitor.Log($"文件位于: {outRoot}", LogLevel.Info);
        }

        // ====== 字符串资产（Dictionary<string, string>）=====

        private void ExportStringAssets(List<string> paths, Dictionary<string, string> langDirs, ExportValidation validation)
        {
            foreach (string assetPath in paths)
            {
                try
                {
                    var langDicts = new Dictionary<string, Dictionary<string, string>>();
                    foreach (var lang in _config.Languages)
                    {
                        var dict = LoadLanguage<Dictionary<string, string>>(assetPath, lang);
                        if (dict == null || dict.Count == 0)
                        {
                            Monitor.Log($"  跳过 {assetPath}（{lang} 为空）", LogLevel.Warn);
                            break;
                        }
                        langDicts[lang] = dict;
                    }
                    if (langDicts.Count != _config.Languages.Length) continue;

                    // Debug: check first key of English
                    if (langDicts.TryGetValue("en", out var enDict) && enDict.Count > 0)
                    {
                        var first = enDict.First();
                        bool chinese = first.Value.Any(c => c > 0x2FF);
                        string sample = first.Value.Length > 60 ? first.Value.Substring(0, 60) + "..." : first.Value;
                        if (chinese)
                            Monitor.Log($"  ⚠ {assetPath} EN 仍含中文: \"{first.Key}\"=\"{sample}\"", LogLevel.Warn);
                        else
                            Monitor.Log($"  ✓ {assetPath}: {string.Join(" ", _config.Languages.Select(l => $"{l}={langDicts[l].Count}"))} 条目", LogLevel.Info);
                    }

                    string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
                    foreach (var lang in _config.Languages)
                        WriteJson(langDicts[lang], Path.Combine(langDirs[lang], safeName));

                    validation.AddStrings(assetPath, langDicts);
                }
                catch (Exception ex)
                {
                    Monitor.Log($"  跳过 {assetPath}：{ex.Message}", LogLevel.Warn);
                }
            }
        }

        // ====== Data 资产 ======

        private void ExportDataAssets(List<string> paths, Dictionary<string, string> langDirs, ExportValidation validation)
        {
            foreach (string assetPath in paths)
            {
                try
                {
                    var langResults = new Dictionary<string, Dictionary<string, Dictionary<string, string>>>();

                    foreach (var lang in _config.Languages)
                    {
                        Dictionary<string, Dictionary<string, string>> result = null;

                        if (assetPath == "Data/hats" || assetPath == "Data/Boots"
                            || assetPath == "Data/Quests" || assetPath == "Data/EngagementDialogue"
                            || assetPath == "Data/Bundles" || assetPath == "Data/Monsters"
                            || assetPath == "Data/NPCGiftTastes")
                        {
                            result = ExportPipeDelimitedData(assetPath, lang);
                        }
                        else if (assetPath == "Data/SecretNotes" || assetPath == "Data/Achievements")
                        {
                            result = ExportIntKeyPipeData(assetPath, '^', lang);
                        }
                        else if (DataToStringsAsset.ContainsKey(assetPath))
                        {
                            string stringsAsset = DataToStringsAsset[assetPath];
                            var stringsDict = LoadLanguage<Dictionary<string, string>>(stringsAsset, lang);
                            result = LoadModelDataWithTokenResolution(assetPath, stringsDict, lang);
                        }
                        else
                        {
                            Monitor.Log($"  未知的 Data 资产类型：{assetPath}，跳过。", LogLevel.Warn);
                            break;
                        }

                        if (result != null)
                            langResults[lang] = result;
                    }

                    if (langResults.Count != _config.Languages.Length) continue;

                    foreach (var lang in _config.Languages)
                        WriteDataExport(assetPath, langDirs[lang], langResults[lang]);

                    validation.AddData(assetPath, langResults);
                }
                catch (Exception ex)
                {
                    Monitor.Log($"  跳过 {assetPath}：{ex.Message}", LogLevel.Warn);
                }
            }
        }

        // ====== 写入 ======

        private void WriteJson<T>(T data, string filePath)
        {
            var options = new JsonSerializerOptions
            {
                WriteIndented = true,
                Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
            };
            File.WriteAllText(filePath, JsonSerializer.Serialize(data, options));
        }

        private void WriteDataExport(string assetPath, string outputDir, Dictionary<string, Dictionary<string, string>> data)
        {
            if (data == null || data.Count == 0) return;

            string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
            WriteJson(data, Path.Combine(outputDir, safeName));
            Monitor.Log($"  已导出：{safeName}（{data.Count} 条目）", LogLevel.Info);
        }

        // ====== 管道分隔型 Data ======

        private Dictionary<string, Dictionary<string, string>> ExportPipeDelimitedData(string assetPath, string langCode)
        {
            var raw = LoadLanguage<Dictionary<string, string>>(assetPath, langCode);
            if (raw == null) return null;

            var result = new Dictionary<string, Dictionary<string, string>>();
            foreach (var kvp in raw)
            {
                var fields = kvp.Value.Split('/');
                string displayName = "";
                string description = "";

                if (assetPath == "Data/hats")
                {
                    description = fields.Length > 1 ? fields[1] : "";
                    displayName = fields.Length > 5 ? fields[5] : "";
                    if (string.IsNullOrEmpty(displayName))
                        displayName = fields.Length > 0 ? fields[0] : "";
                }
                else if (assetPath == "Data/Boots")
                {
                    description = fields.Length > 1 ? fields[1] : "";
                    displayName = fields.Length > 6 ? fields[6] : "";
                    if (string.IsNullOrEmpty(displayName))
                        displayName = fields.Length > 0 ? fields[0] : "";
                }
                else if (assetPath == "Data/Quests")
                {
                    displayName = fields.Length > 1 ? fields[1] : "";
                    description = fields.Length > 2 ? fields[2] : "";
                }
                else if (assetPath == "Data/EngagementDialogue")
                {
                    displayName = fields.Length > 0 ? fields[0] : "";
                }
                else if (assetPath == "Data/Bundles")
                {
                    displayName = fields.Length > 6 ? fields[6] : "";
                }
                else if (assetPath == "Data/Monsters")
                {
                    displayName = fields.Length > 14 ? fields[14] : "";
                }
                else if (assetPath == "Data/NPCGiftTastes")
                {
                    displayName = fields.Length > 0 ? fields[0] : "";
                }

                result[kvp.Key] = new Dictionary<string, string>
                {
                    ["displayName"] = displayName,
                    ["description"] = description
                };

                if (assetPath == "Data/NPCGiftTastes")
                {
                    result[kvp.Key]["_raw"] = kvp.Value;
                }
            }
            return result;
        }

        // ====== ^ 分隔的 int-key Data（SecretNotes）=====

        private Dictionary<string, Dictionary<string, string>> ExportIntKeyPipeData(string assetPath, char delimiter, string langCode)
        {
            Helper.GameContent.InvalidateCache<Dictionary<int, string>>();

            var raw = LoadLanguage<Dictionary<int, string>>(assetPath, langCode);
            if (raw == null) return null;

            var result = new Dictionary<string, Dictionary<string, string>>();
            foreach (var kvp in raw)
            {
                var fields = kvp.Value.Split(delimiter);
                string displayName = fields.Length > 0 ? fields[0] : "";
                string description = fields.Length > 1 ? fields[1] : "";
                result[kvp.Key.ToString()] = new Dictionary<string, string>
                {
                    ["displayName"] = displayName,
                    ["description"] = description,
                    ["_raw"] = kvp.Value
                };
            }
            return result;
        }

        // ====== 模型型 Data ======

        private Dictionary<string, Dictionary<string, string>> LoadModelDataWithTokenResolution(
            string assetPath, Dictionary<string, string> stringsDict, string langCode)
        {
            return assetPath switch
            {
                "Data/Objects" => ExtractTokenizedData(
                    LoadModelData<ObjectData>(assetPath, langCode), stringsDict, langCode),
                "Data/Tools" => ExtractTokenizedData(
                    LoadModelData<ToolData>(assetPath, langCode), stringsDict, langCode),
                "Data/Weapons" => ExtractTokenizedData(
                    LoadModelData<WeaponData>(assetPath, langCode), stringsDict, langCode),
                "Data/Shirts" => ExtractTokenizedData(
                    LoadModelData<ShirtData>(assetPath, langCode), stringsDict, langCode),
                "Data/Pants" => ExtractTokenizedData(
                    LoadModelData<PantsData>(assetPath, langCode), stringsDict, langCode),
                "Data/BigCraftables" => ExtractTokenizedData(
                    LoadModelData<BigCraftableData>(assetPath, langCode), stringsDict, langCode),
                "Data/Powers" => ExtractTokenizedData(
                    LoadModelData<PowersData>(assetPath, langCode), stringsDict, langCode),
                "Data/Trinkets" => ExtractTokenizedData(
                    LoadModelData<TrinketData>(assetPath, langCode), stringsDict, langCode),
                _ => null
            };
        }

        private Dictionary<string, T> LoadModelData<T>(string assetPath, string langCode)
            => LoadLanguage<Dictionary<string, T>>(assetPath, langCode);

        private Dictionary<string, Dictionary<string, string>> ExtractTokenizedData<T>(
            Dictionary<string, T> rawData, Dictionary<string, string> primaryStrings, string langCode)
        {
            if (rawData == null) return null;

            var result = new Dictionary<string, Dictionary<string, string>>();
            foreach (var kvp in rawData)
            {
                dynamic item = kvp.Value;
                string dn = item?.DisplayName as string ?? "";
                string desc = item?.Description as string ?? "";
                result[kvp.Key] = new Dictionary<string, string>
                {
                    ["displayName"] = ResolveToken(dn, primaryStrings, langCode),
                    ["description"] = ResolveToken(desc, primaryStrings, langCode)
                };
            }
            return result;
        }

        private string ResolveToken(string rawValue, Dictionary<string, string> primaryStrings, string langCode)
        {
            if (string.IsNullOrEmpty(rawValue))
                return "";

            var match = TokenRegex.Match(rawValue);
            if (match.Success)
            {
                string source = match.Groups[1].Value; // "Strings\Objects"
                string key = match.Groups[2].Value;    // "DwarvishTranslationGuide_Name"

                // Try the token's specified source first
                string assetPath = source.Replace('\\', '/');
                string cacheKey = assetPath + ":" + langCode;

                if (!_stringsLoadCache.TryGetValue(cacheKey, out var tokenSourceStrings))
                {
                    try
                    {
                        tokenSourceStrings = LoadLanguage<Dictionary<string, string>>(assetPath, langCode);
                        _stringsLoadCache[cacheKey] = tokenSourceStrings;
                    }
                    catch
                    {
                        tokenSourceStrings = null;
                    }
                }

                if (tokenSourceStrings != null && tokenSourceStrings.TryGetValue(key, out var resolved))
                    return resolved;

                // Fall back to primary strings dict
                if (primaryStrings.TryGetValue(key, out var primaryResolved))
                    return primaryResolved;

                // Try splitting format arguments from key (e.g. "TrashCan_Description 15")
                int lastSpace = key.LastIndexOf(' ');
                if (lastSpace > 0)
                {
                    string realKey = key.Substring(0, lastSpace);
                    string fmtArgs = key.Substring(lastSpace + 1);

                    string template = null;
                    if (tokenSourceStrings != null && tokenSourceStrings.TryGetValue(realKey, out var srcTemplate))
                        template = srcTemplate;
                    else if (primaryStrings.TryGetValue(realKey, out var priTemplate))
                        template = priTemplate;

                    if (template != null)
                        return string.Format(template, fmtArgs);
                }
            }

            return rawValue;
        }

        // ====== 导出验证 ======

        private class ExportValidation
        {
            private readonly IMonitor _monitor;
            private readonly string[] _langs;
            private readonly List<AssetReport> _reports = new();

            public class AssetReport
            {
                public string AssetPath;
                public int TotalMergedKeys;
                public int IdenticalValues;
                public Dictionary<string, int> TokenResidual = new();
                public Dictionary<string, int> LangOnly = new();
            }

            public ExportValidation(IMonitor monitor, string[] langs) { _monitor = monitor; _langs = langs; }

            public void AddStrings(string assetPath, Dictionary<string, Dictionary<string, string>> langDicts)
            {
                var allKeys = new HashSet<string>();
                foreach (var dict in langDicts.Values)
                    allKeys.UnionWith(dict.Keys);

                var r = new AssetReport { AssetPath = assetPath };
                foreach (var key in allKeys)
                {
                    r.TotalMergedKeys++;

                    bool allSame = true;
                    string firstVal = null;

                    foreach (var lang in _langs)
                    {
                        var dict = langDicts[lang];
                        bool hasKey = dict.TryGetValue(key, out string val);

                        if (!hasKey)
                        {
                            if (!r.LangOnly.ContainsKey(lang)) r.LangOnly[lang] = 0;
                            r.LangOnly[lang]++;
                        }
                        else
                        {
                            if (firstVal == null) firstVal = val;
                            else if (val != firstVal) allSame = false;

                            if (TokenRegex.IsMatch(val))
                            {
                                if (!r.TokenResidual.ContainsKey(lang)) r.TokenResidual[lang] = 0;
                                r.TokenResidual[lang]++;
                            }
                        }
                    }

                    if (allSame && !string.IsNullOrEmpty(firstVal))
                        r.IdenticalValues++;
                }
                _reports.Add(r);
            }

            public void AddData(string assetPath,
                Dictionary<string, Dictionary<string, Dictionary<string, string>>> langResults)
            {
                if (langResults.Count == 0) return;

                var allKeys = new HashSet<string>();
                foreach (var result in langResults.Values)
                    allKeys.UnionWith(result.Keys);

                var r = new AssetReport { AssetPath = assetPath };
                foreach (var key in allKeys)
                {
                    r.TotalMergedKeys++;

                    bool allSame = true;
                    bool firstSet = false;
                    int sharedFieldCount = 0, sharedFieldMatches = 0;

                    foreach (var lang in _langs)
                    {
                        if (!langResults.TryGetValue(lang, out var result) || !result.ContainsKey(key))
                        {
                            if (!r.LangOnly.ContainsKey(lang)) r.LangOnly[lang] = 0;
                            r.LangOnly[lang]++;
                            continue;
                        }

                        var entry = result[key];
                        if (!firstSet)
                        {
                            firstSet = true;
                            sharedFieldCount = entry.Count;
                            sharedFieldMatches = entry.Count;
                        }
                        else
                        {
                            // Compare against first language's entry
                            var firstEntry = langResults[_langs[0]][key];
                            bool same = entry.Count == firstEntry.Count
                                && entry.Keys.All(k => firstEntry.TryGetValue(k, out string v) && v == entry[k]);
                            if (!same) allSame = false;
                        }

                        foreach (var fv in entry.Values)
                            if (TokenRegex.IsMatch(fv))
                            {
                                if (!r.TokenResidual.ContainsKey(lang)) r.TokenResidual[lang] = 0;
                                r.TokenResidual[lang]++;
                            }
                    }

                    if (allSame && firstSet)
                        r.IdenticalValues++;
                }
                _reports.Add(r);
            }

            public void Report()
            {
                int totalKeys = 0;

                _monitor.Log("--- 导出验证报告 ---", LogLevel.Info);

                foreach (var r in _reports.OrderBy(r => r.AssetPath))
                {
                    totalKeys += r.TotalMergedKeys;

                    var issues = new List<string>();
                    if (r.IdenticalValues > 0 && r.IdenticalValues > r.TotalMergedKeys * 0.3)
                        issues.Add($"所有语言完全一致 占 {r.IdenticalValues}/{r.TotalMergedKeys}");
                    foreach (var kvp in r.TokenResidual)
                        if (kvp.Value > 0) issues.Add($"Token 残留 {kvp.Key}:{kvp.Value}");
                    foreach (var kvp in r.LangOnly)
                        if (kvp.Value > 10) issues.Add($"仅 {kvp.Key} 键: {kvp.Value}");

                    if (issues.Count > 0)
                        _monitor.Log($"  ⚠ {r.AssetPath}: {string.Join("; ", issues)}", LogLevel.Warn);
                    else
                        _monitor.Log($"  ✓ {r.AssetPath}: {r.TotalMergedKeys} 键", LogLevel.Info);
                }

                _monitor.Log("--- 汇总 ---", LogLevel.Info);
                _monitor.Log($"总资产: {_reports.Count}", LogLevel.Info);
                _monitor.Log($"总合并键: {totalKeys}", LogLevel.Info);
            }
        }
    }
}
