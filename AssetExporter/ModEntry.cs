using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using StardewModdingAPI;
using StardewModdingAPI.Events;
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
        private List<string> stringAssetPaths = new();
        private List<string> dataAssetPaths = new();

        // Data/* 模型型资产 -> 对应的 Strings/* 资产（用于 token 解析）
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
            @"\[LocalizedText\s+[^:]+:(\w+)\]",
            RegexOptions.Compiled
        );

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
                if (textDataAssets.Contains(path))
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

        private void ExportAssets()
        {
            string outRoot = Path.Combine(Constants.GamePath, "Export_TextAssets");
            Directory.CreateDirectory(outRoot);

            try
            {
                string enDir = Path.Combine(outRoot, "en");
                string zhDir = Path.Combine(outRoot, "zh");
                Directory.CreateDirectory(enDir);
                Directory.CreateDirectory(zhDir);

                if (stringAssetPaths.Count > 0)
                {
                    Monitor.Log("正在导出字符串资产...", LogLevel.Info);
                    ExportStringAssets(stringAssetPaths, enDir, null);
                    ExportStringAssets(stringAssetPaths, zhDir, ".zh-CN");
                }

                if (dataAssetPaths.Count > 0)
                {
                    Monitor.Log("正在导出 Data 资产（显示名+描述）...", LogLevel.Info);
                    ExportDataAssets(dataAssetPaths, enDir, zhDir);
                }
            }
            catch (Exception ex)
            {
                Monitor.Log($"导出过程发生异常：{ex}", LogLevel.Error);
            }
            finally
            {
                Monitor.Log("导出完成。文件位于：" + outRoot, LogLevel.Info);
            }
        }

        private void ExportStringAssets(List<string> paths, string outputDir, string localeSuffix)
        {
            foreach (string assetPath in paths)
            {
                string loadPath = assetPath + (localeSuffix ?? "");
                try
                {
                    var dict = Helper.GameContent.Load<Dictionary<string, string>>(loadPath);
                    if (dict == null || dict.Count == 0) continue;

                    string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
                    string filePath = Path.Combine(outputDir, safeName);

                    var options = new JsonSerializerOptions
                    {
                        WriteIndented = true,
                        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
                    };
                    File.WriteAllText(filePath, JsonSerializer.Serialize(dict, options));
                    Monitor.Log($"已导出字符串资产：{loadPath}", LogLevel.Info);
                }
                catch (Exception ex)
                {
                    Monitor.Log($"跳过 {loadPath}：{ex.Message}", LogLevel.Warn);
                }
            }
        }

        private void ExportDataAssets(List<string> paths, string enDir, string zhDir)
        {
            foreach (string assetPath in paths)
            {
                try
                {
                    if (assetPath == "Data/hats" || assetPath == "Data/Boots"
                        || assetPath == "Data/Quests" || assetPath == "Data/SecretNotes"
                        || assetPath == "Data/EngagementDialogue")
                    {
                        var enResult = ExportPipeDelimitedData(assetPath, assetPath);
                        var zhResult = ExportPipeDelimitedData(assetPath, assetPath + ".zh-CN");
                        WriteDataExport(assetPath, enDir, enResult);
                        WriteDataExport(assetPath, zhDir, zhResult);
                    }
                    else if (assetPath == "Data/SecretNotes")
                    {
                        var enResult = ExportIntKeyPipeData(assetPath, '^');
                        var zhResult = ExportIntKeyPipeData(assetPath + ".zh-CN", '^');
                        WriteDataExport(assetPath, enDir, enResult);
                        WriteDataExport(assetPath, zhDir, zhResult);
                    }
                    else if (DataToStringsAsset.ContainsKey(assetPath))
                    {
                        string stringsAsset = DataToStringsAsset[assetPath];
                        var enStrings = Helper.GameContent.Load<Dictionary<string, string>>(stringsAsset);

                        Dictionary<string, string> zhStrings = null;
                        try
                        {
                            zhStrings = Helper.GameContent.Load<Dictionary<string, string>>(stringsAsset + ".zh-CN");
                            Monitor.Log($"  加载了 {stringsAsset}.zh-CN 用于中文解析 ({zhStrings.Count} 条目)", LogLevel.Info);
                        }
                        catch
                        {
                            Monitor.Log($"  未找到 {stringsAsset}.zh-CN，中文将回退英文", LogLevel.Warn);
                            zhStrings = enStrings;
                        }

                        var enResult = LoadModelDataWithTokenResolution(assetPath, assetPath, enStrings);
                        WriteDataExport(assetPath, enDir, enResult);

                        var zhResult = LoadModelDataWithTokenResolution(assetPath, assetPath, zhStrings);
                        WriteDataExport(assetPath, zhDir, zhResult);
                    }
                    else
                    {
                        Monitor.Log($"未知的 Data 资产类型：{assetPath}，跳过。", LogLevel.Warn);
                    }
                }
                catch (Exception ex)
                {
                    Monitor.Log($"跳过 {assetPath}：{ex.Message}", LogLevel.Warn);
                }
            }
        }

        private void WriteDataExport(string assetPath, string outputDir, Dictionary<string, Dictionary<string, string>> data)
        {
            if (data == null || data.Count == 0) return;

            string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
            string filePath = Path.Combine(outputDir, safeName);
            var options = new JsonSerializerOptions
            {
                WriteIndented = true,
                Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
            };
            File.WriteAllText(filePath, JsonSerializer.Serialize(data, options));
            Monitor.Log($"  已导出：{safeName}（{data.Count} 条目）", LogLevel.Info);
        }

        private Dictionary<string, Dictionary<string, string>> ExportIntKeyPipeData(string loadPath, char delimiter)
        {
            var raw = Helper.GameContent.Load<Dictionary<int, string>>(loadPath);
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
                    ["description"] = description
                };
            }
            return result;
        }

        private Dictionary<string, Dictionary<string, string>> ExportPipeDelimitedData(string assetPath, string loadPath)
        {
            var raw = Helper.GameContent.Load<Dictionary<string, string>>(loadPath);
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
                else if (assetPath == "Data/SecretNotes")
                {
                    displayName = fields.Length > 0 ? fields[0] : "";
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

        private Dictionary<string, Dictionary<string, string>> LoadModelDataWithTokenResolution(
            string assetPath, string loadPath, Dictionary<string, string> stringsDict)
        {
            return assetPath switch
            {
                "Data/Objects" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, ObjectData>>(loadPath), stringsDict),
                "Data/Tools" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, ToolData>>(loadPath), stringsDict),
                "Data/Weapons" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, WeaponData>>(loadPath), stringsDict),
                "Data/Shirts" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, ShirtData>>(loadPath), stringsDict),
                "Data/Pants" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, PantsData>>(loadPath), stringsDict),
                "Data/BigCraftables" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, BigCraftableData>>(loadPath), stringsDict),
                "Data/Powers" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, PowersData>>(loadPath), stringsDict),
                "Data/Trinkets" => ExtractTokenizedData(
                    Helper.GameContent.Load<Dictionary<string, TrinketData>>(loadPath), stringsDict),
                _ => null
            };
        }

        private Dictionary<string, Dictionary<string, string>> ExtractTokenizedData<T>(
            Dictionary<string, T> rawData, Dictionary<string, string> stringsDict)
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
                    ["displayName"] = ResolveToken(dn, stringsDict),
                    ["description"] = ResolveToken(desc, stringsDict)
                };
            }
            return result;
        }

        private string ResolveToken(string rawValue, Dictionary<string, string> stringsDict)
        {
            if (string.IsNullOrEmpty(rawValue))
                return "";

            var match = TokenRegex.Match(rawValue);
            if (match.Success)
            {
                string key = match.Groups[1].Value;
                if (stringsDict != null && stringsDict.TryGetValue(key, out string resolved))
                    return resolved;
            }

            return rawValue;
        }
    }
}
