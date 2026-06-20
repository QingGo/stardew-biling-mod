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
        private List<string> assetPaths = new();

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
            assetPaths = File.ReadAllLines(listFile)
                             .Select(l => l.Trim())
                             .Where(l => !string.IsNullOrEmpty(l) && !l.StartsWith("#"))
                             .ToList();

            if (assetPaths.Count == 0)
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
                // 导出英文（无后缀）
                string enDir = Path.Combine(outRoot, "en");
                Directory.CreateDirectory(enDir);
                Monitor.Log("正在导出英文资产...", LogLevel.Info);
                ExportLanguage(assetPaths, enDir, null);

                // 导出中文（加 .zh-CN 后缀）
                string zhDir = Path.Combine(outRoot, "zh");
                Directory.CreateDirectory(zhDir);
                Monitor.Log("正在导出中文资产...", LogLevel.Info);
                ExportLanguage(assetPaths, zhDir, ".zh-CN");
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

        private void ExportLanguage(List<string> paths, string outputDir, string localeSuffix)
        {
            foreach (string assetPath in paths)
            {
                string loadPath = assetPath + (localeSuffix ?? "");
                try
                {
                    var dict = Helper.GameContent.Load<Dictionary<string, string>>(loadPath);

                    if (dict == null || dict.Count == 0)
                    {
                        Monitor.Log($"资产 {loadPath} 为空或加载失败。", LogLevel.Warn);
                        continue;
                    }

                    string safeName = assetPath.Replace("/", "_").Replace("\\", "_") + ".json";
                    string filePath = Path.Combine(outputDir, safeName);

                    var options = new JsonSerializerOptions
                    {
                        WriteIndented = true,
                        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
                    };
                    string json = JsonSerializer.Serialize(dict, options);
                    File.WriteAllText(filePath, json);
                    Monitor.Log($"已导出：{loadPath} -> {safeName}");
                }
                catch (Exception ex)
                {
                    Monitor.Log($"无法加载资产 {loadPath}，跳过。错误：{ex.Message}", LogLevel.Warn);
                }
            }
        }
    }
}
