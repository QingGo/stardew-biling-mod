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
    public class ModEntry : Mod
    {
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

        public override void Entry(IModHelper helper)
        {
            helper.Events.GameLoop.GameLaunched += OnGameLaunched;
        }

        private void OnGameLaunched(object sender, GameLaunchedEventArgs e)
        {
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
                if (textDataAssets.Contains(path) || path.StartsWith("Data/Events/"))
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

        private T LoadEn<T>(string assetPath)
        {
            var origLang = LocalizedContentManager.CurrentLanguageCode;
            LocalizedContentManager.CurrentLanguageCode = LocalizedContentManager.LanguageCode.en;

            InvalidateAllCaches();

            var result = Helper.GameContent.Load<T>(assetPath);

            LocalizedContentManager.CurrentLanguageCode = origLang;
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

        private T LoadZh<T>(string assetPath)
        {
            DebugLog($"LoadZh<{typeof(T).Name}>(\"{assetPath}\")");
            var origLang = LocalizedContentManager.CurrentLanguageCode;
            LocalizedContentManager.CurrentLanguageCode = LocalizedContentManager.LanguageCode.zh;
            InvalidateAllCaches();

            var result = Helper.GameContent.Load<T>(assetPath);

            // Don't restore — subsequent LoadEn will handle its own switching
            // Actually, we must restore so the game doesn't break when user plays
            LocalizedContentManager.CurrentLanguageCode = origLang;

            // Verify we got Chinese data
            if (result is Dictionary<string, string> dict && dict.Count > 0)
            {
                var sample = dict.First();
                bool hasChinese = sample.Value.Any(c => c > 0x2FF);
                if (!hasChinese)
                {
                    DebugLog($"  ⚠ LoadZh(\"{assetPath}\") — NO Chinese found! \"{sample.Key}\"=\"{sample.Value.Substring(0, Math.Min(60, sample.Value.Length))}\"");
                    // Try again with stronger measures
                    LocalizedContentManager.CurrentLanguageCode = LocalizedContentManager.LanguageCode.zh;
                    InvalidateAllCaches();
                    result = Helper.GameContent.Load<T>(assetPath);
                    LocalizedContentManager.CurrentLanguageCode = origLang;
                }
            }

            return result;
        }

        // ====== 主流程 ======

        private void ExportAssets()
        {
            string outRoot = Path.Combine(Constants.GamePath, "Export_TextAssets");
            string enDir = Path.Combine(outRoot, "en");
            string zhDir = Path.Combine(outRoot, "zh");

            Directory.CreateDirectory(enDir);
            Directory.CreateDirectory(zhDir);

            Monitor.Log("=== 导出开始 ===", LogLevel.Info);
            Monitor.Log("EN: Switch CurrentLanguageCode=en + InvalidateCache<Dict<string,string>> + Load", LogLevel.Info);
            Monitor.Log("ZH: Helper.GameContent.Load (Chinese locale)", LogLevel.Info);

            var validation = new ExportValidation(Monitor);

            if (stringAssetPaths.Count > 0)
            {
                Monitor.Log("--- 字符串资产 ---", LogLevel.Info);
                ExportStringAssets(stringAssetPaths, enDir, zhDir, validation);
            }

            if (dataAssetPaths.Count > 0)
            {
                Monitor.Log("--- Data 资产（显示名+描述）---", LogLevel.Info);
                ExportDataAssets(dataAssetPaths, enDir, zhDir, validation);
            }

            validation.Report();

            Monitor.Log("=== 导出完成 ===", LogLevel.Info);
            Monitor.Log($"文件位于: {outRoot}", LogLevel.Info);
        }

        // ====== 字符串资产（Dictionary<string, string>）=====

        private void ExportStringAssets(List<string> paths, string enDir, string zhDir, ExportValidation validation)
        {
            foreach (string assetPath in paths)
            {
                try
                {
                    var enDict = LoadEn<Dictionary<string, string>>(assetPath);
                    if (enDict == null || enDict.Count == 0) continue;

                    var zhDict = LoadZh<Dictionary<string, string>>(assetPath);
                    if (zhDict == null || zhDict.Count == 0) continue;

                    // Debug: check first key
                    if (enDict.Count > 0)
                    {
                        var first = enDict.First();
                        bool chinese = first.Value.Any(c => c > 0x2FF);
                        string sample = first.Value.Length > 60 ? first.Value.Substring(0, 60) + "..." : first.Value;
                        if (chinese)
                            Monitor.Log($"  ⚠ {assetPath} EN 仍含中文: \"{first.Key}\"=\"{sample}\"", LogLevel.Warn);
                        else
                            Monitor.Log($"  ✓ {assetPath}: EN={enDict.Count} ZH={zhDict.Count} 条目", LogLevel.Info);
                    }

                    string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
                    WriteJson(enDict, Path.Combine(enDir, safeName));
                    WriteJson(zhDict, Path.Combine(zhDir, safeName));

                    validation.AddStrings(assetPath, enDict, zhDict);
                }
                catch (Exception ex)
                {
                    Monitor.Log($"  跳过 {assetPath}：{ex.Message}", LogLevel.Warn);
                }
            }
        }

        // ====== Data 资产 ======

        private void ExportDataAssets(List<string> paths, string enDir, string zhDir, ExportValidation validation)
        {
            foreach (string assetPath in paths)
            {
                try
                {
                    if (assetPath == "Data/hats" || assetPath == "Data/Boots"
                        || assetPath == "Data/Quests" || assetPath == "Data/EngagementDialogue")
                    {
                        var enResult = ExportPipeDelimitedData(assetPath, isEnglish: true);
                        var zhResult = ExportPipeDelimitedData(assetPath, isEnglish: false);
                        WriteDataExport(assetPath, enDir, enResult);
                        WriteDataExport(assetPath, zhDir, zhResult);
                        validation.AddData(assetPath, enResult, zhResult);
                    }
                    else if (assetPath == "Data/SecretNotes" || assetPath == "Data/Achievements")
                    {
                        var enResult = ExportIntKeyPipeData(assetPath, '^', isEnglish: true);
                        var zhResult = ExportIntKeyPipeData(assetPath, '^', isEnglish: false);
                        WriteDataExport(assetPath, enDir, enResult);
                        WriteDataExport(assetPath, zhDir, zhResult);
                        validation.AddData(assetPath, enResult, zhResult);
                    }
                    else if (DataToStringsAsset.ContainsKey(assetPath))
                    {
                        string stringsAsset = DataToStringsAsset[assetPath];
                        var enStrings = LoadEn<Dictionary<string, string>>(stringsAsset);
                        var zhStrings = LoadZh<Dictionary<string, string>>(stringsAsset);

                        var enResult = LoadModelDataWithTokenResolution(assetPath, enStrings, isEnglish: true);
                        var zhResult = LoadModelDataWithTokenResolution(assetPath, zhStrings, isEnglish: false);
                        WriteDataExport(assetPath, enDir, enResult);
                        WriteDataExport(assetPath, zhDir, zhResult);
                        validation.AddData(assetPath, enResult, zhResult);
                    }
                    else
                    {
                        Monitor.Log($"  未知的 Data 资产类型：{assetPath}，跳过。", LogLevel.Warn);
                    }
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

        private Dictionary<string, Dictionary<string, string>> ExportPipeDelimitedData(string assetPath, bool isEnglish)
        {
            Dictionary<string, string> raw;
            if (isEnglish)
                raw = LoadEn<Dictionary<string, string>>(assetPath);
            else
                raw = LoadZh<Dictionary<string, string>>(assetPath);

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

                result[kvp.Key] = new Dictionary<string, string>
                {
                    ["displayName"] = displayName,
                    ["description"] = description
                };
            }
            return result;
        }

        // ====== ^ 分隔的 int-key Data（SecretNotes）=====

        private Dictionary<string, Dictionary<string, string>> ExportIntKeyPipeData(string assetPath, char delimiter, bool isEnglish)
        {
            Helper.GameContent.InvalidateCache<Dictionary<int, string>>();

            Dictionary<int, string> raw;
            if (isEnglish)
                raw = LoadEn<Dictionary<int, string>>(assetPath);
            else
                raw = LoadZh<Dictionary<int, string>>(assetPath);

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
            string assetPath, Dictionary<string, string> stringsDict, bool isEnglish)
        {
            return assetPath switch
            {
                "Data/Objects" => ExtractTokenizedData(
                    LoadModelData<ObjectData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/Tools" => ExtractTokenizedData(
                    LoadModelData<ToolData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/Weapons" => ExtractTokenizedData(
                    LoadModelData<WeaponData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/Shirts" => ExtractTokenizedData(
                    LoadModelData<ShirtData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/Pants" => ExtractTokenizedData(
                    LoadModelData<PantsData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/BigCraftables" => ExtractTokenizedData(
                    LoadModelData<BigCraftableData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/Powers" => ExtractTokenizedData(
                    LoadModelData<PowersData>(assetPath, isEnglish), stringsDict, isEnglish),
                "Data/Trinkets" => ExtractTokenizedData(
                    LoadModelData<TrinketData>(assetPath, isEnglish), stringsDict, isEnglish),
                _ => null
            };
        }

        private Dictionary<string, T> LoadModelData<T>(string assetPath, bool isEnglish)
        {
            if (isEnglish)
                return LoadEn<Dictionary<string, T>>(assetPath);
            else
                return LoadZh<Dictionary<string, T>>(assetPath);
        }

        private Dictionary<string, Dictionary<string, string>> ExtractTokenizedData<T>(
            Dictionary<string, T> rawData, Dictionary<string, string> primaryStrings, bool isEnglish)
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
                    ["displayName"] = ResolveToken(dn, primaryStrings, isEnglish),
                    ["description"] = ResolveToken(desc, primaryStrings, isEnglish)
                };
            }
            return result;
        }

        private string ResolveToken(string rawValue, Dictionary<string, string> primaryStrings, bool isEnglish)
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
                string cacheKey = assetPath + ":" + isEnglish;

                if (!_stringsLoadCache.TryGetValue(cacheKey, out var tokenSourceStrings))
                {
                    try
                    {
                        if (isEnglish)
                            tokenSourceStrings = LoadEn<Dictionary<string, string>>(assetPath);
                        else
                            tokenSourceStrings = LoadZh<Dictionary<string, string>>(assetPath);
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
            }

            return rawValue;
        }

        // ====== 导出验证 ======

        private class ExportValidation
        {
            private readonly IMonitor _monitor;
            private readonly List<AssetReport> _reports = new();

            public class AssetReport
            {
                public string AssetPath;
                public int TotalMergedKeys;
                public int IdenticalValues;
                public int EnTokenResidual;
                public int ZhTokenResidual;
                public int EnOnly;
                public int ZhOnly;
            }

            public ExportValidation(IMonitor monitor) { _monitor = monitor; }

            public void AddStrings(string assetPath, Dictionary<string, string> en, Dictionary<string, string> zh)
            {
                var allKeys = new HashSet<string>(en.Keys);
                allKeys.UnionWith(zh.Keys);

                var r = new AssetReport { AssetPath = assetPath };
                foreach (var key in allKeys)
                {
                    r.TotalMergedKeys++;
                    bool hasEn = en.TryGetValue(key, out string enVal);
                    bool hasZh = zh.TryGetValue(key, out string zhVal);

                    if (hasEn && hasZh && enVal == zhVal && !string.IsNullOrEmpty(enVal))
                        r.IdenticalValues++;
                    if (hasEn && !hasZh) r.EnOnly++;
                    if (hasZh && !hasEn) r.ZhOnly++;
                    if (hasEn && TokenRegex.IsMatch(enVal)) r.EnTokenResidual++;
                    if (hasZh && TokenRegex.IsMatch(zhVal)) r.ZhTokenResidual++;
                }
                _reports.Add(r);
            }

            public void AddData(string assetPath,
                Dictionary<string, Dictionary<string, string>> en,
                Dictionary<string, Dictionary<string, string>> zh)
            {
                if (en == null && zh == null) return;

                var allKeys = new HashSet<string>();
                if (en != null) allKeys.UnionWith(en.Keys);
                if (zh != null) allKeys.UnionWith(zh.Keys);

                var r = new AssetReport { AssetPath = assetPath };
                foreach (var key in allKeys)
                {
                    r.TotalMergedKeys++;
                    bool hasEn = en?.ContainsKey(key) ?? false;
                    bool hasZh = zh?.ContainsKey(key) ?? false;

                    if (hasEn && !hasZh) r.EnOnly++;
                    else if (hasZh && !hasEn) r.ZhOnly++;
                    else if (hasEn && hasZh)
                    {
                        var ev = en[key];
                        var zv = zh[key];
                        bool same = ev.Count == zv.Count
                            && ev.Keys.All(k => zv.TryGetValue(k, out string v) && v == ev[k]);
                        if (same)
                            r.IdenticalValues++;
                    }

                    if (hasEn)
                        foreach (var fv in en[key].Values)
                            if (TokenRegex.IsMatch(fv)) r.EnTokenResidual++;
                    if (hasZh)
                        foreach (var fv in zh[key].Values)
                            if (TokenRegex.IsMatch(fv)) r.ZhTokenResidual++;
                }
                _reports.Add(r);
            }

            public void Report()
            {
                int totalIdentical = 0;
                int totalKeys = 0;
                int totalEnOnly = 0;
                int totalZhOnly = 0;
                int totalTokens = 0;

                _monitor.Log("--- 导出验证报告 ---", LogLevel.Info);

                foreach (var r in _reports.OrderBy(r => r.AssetPath))
                {
                    totalIdentical += r.IdenticalValues;
                    totalKeys += r.TotalMergedKeys;
                    totalEnOnly += r.EnOnly;
                    totalZhOnly += r.ZhOnly;
                    totalTokens += r.EnTokenResidual + r.ZhTokenResidual;

                    var issues = new List<string>();
                    if (r.IdenticalValues > 0 && r.IdenticalValues > r.TotalMergedKeys * 0.3)
                        issues.Add($"EN=ZH 占 {r.IdenticalValues}/{r.TotalMergedKeys}");
                    if (r.EnTokenResidual > 0 || r.ZhTokenResidual > 0)
                        issues.Add($"Token 残留 EN:{r.EnTokenResidual} ZH:{r.ZhTokenResidual}");
                    if (r.EnOnly > 10)
                        issues.Add($"仅英文键: {r.EnOnly}");
                    if (r.ZhOnly > 10)
                        issues.Add($"仅中文键: {r.ZhOnly}");

                    if (issues.Count > 0)
                        _monitor.Log($"  ⚠ {r.AssetPath}: {string.Join("; ", issues)}", LogLevel.Warn);
                    else
                        _monitor.Log($"  ✓ {r.AssetPath}: {r.TotalMergedKeys} 键", LogLevel.Info);
                }

                _monitor.Log("--- 汇总 ---", LogLevel.Info);
                _monitor.Log($"总资产: {_reports.Count}", LogLevel.Info);
                _monitor.Log($"总合并键: {totalKeys}", LogLevel.Info);
                _monitor.Log($"EN=ZH 完全相同: {totalIdentical}", LogLevel.Info);
                _monitor.Log($"仅英文键: {totalEnOnly}", LogLevel.Info);
                _monitor.Log($"仅中文键: {totalZhOnly}", LogLevel.Info);
                _monitor.Log($"Token 残留: {totalTokens}", LogLevel.Info);
            }
        }
    }
}
