using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using Newtonsoft.Json.Linq;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides configuration management for the application, including paths, templates, and settings.
    /// </summary>
    /// <remarks>The <see cref="ConfigurationService"/> class is responsible for managing application
    /// settings,  such as file paths, presentation templates, and system prompts. It reads and writes configuration
    /// data from a settings file and provides properties to access these settings at runtime.  This class also includes
    /// default values for certain settings, which are used as fallbacks  when no values are provided in the
    /// configuration file.</remarks>
    public partial class ConfigurationService : ObservableObject
    {
        public string DocumentsPath { get; private set; }
        public List<string> AddedPresentationTemplatesPaths { get; private set; } = [];
        public string SystemPromptPath { get; private set; }
        public string IntentPromptPath { get; private set; }
        public string ServerConfigPath { get; private set; }
        public string OllamaPath { get; private set; }
        public string OllamaModelsDir { get; private set; }
        public Uri OllamaUri { get; private set; }
        public string SelectedModel { get; private set; }

        // System settings defaults - to be used as fallback options
        public readonly string[] defaultTemplatesPaths =
        [
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "LibreOffice",
                "4",
                "user",
                "template"
            ),
            "C:\\Program Files\\LibreOffice\\share\\template\\common\\presnt",
        ];

        public readonly string defaultModel = "qwen3:8b";

        public readonly string defaultDocumentsPath = Environment.GetFolderPath(
            Environment.SpecialFolder.MyDocuments
        );

        public ConfigurationService()
        {
#if DEBUG
            // Use hardcoded paths in Debug Mode
            OllamaPath = "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\Ollama\\ollama.exe";
            OllamaModelsDir =
                "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\Ollama\\lib\\models\\";

            string settingsPath = "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\settings.json";

            ServerConfigPath = "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\server_config.json";
            string serverCommand =
                "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\MCPServer\\main.exe";

            SystemPromptPath = "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\SystemPrompt.txt";
            IntentPromptPath = "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\IntentPrompt.txt";
#else
            // Use the deployed directory in Release/Published mode
            OllamaPath = Path.Combine(AppContext.BaseDirectory, "Ollama", "ollama.exe");
            OllamaModelsDir = Path.Combine(AppContext.BaseDirectory, "Ollama", "lib", "models");

            string settingsPath = Path.Combine(AppContext.BaseDirectory, "settings.json");
            string serverCommand = Path.Combine(AppContext.BaseDirectory, "MCPServer", "main.exe");
            ServerConfigPath = Path.Combine(AppContext.BaseDirectory, "server_config.json");

            SystemPromptPath = Path.Combine(AppContext.BaseDirectory, "SystemPrompt.txt");
            IntentPromptPath = Path.Combine(AppContext.BaseDirectory, "IntentPrompt.txt");

#endif
            try
            {
                // Get all settings from settings.json
                var settingsJson = JObject.Parse(File.ReadAllText(settingsPath));

                // Documents Folder
                var documentsPath = (string?)settingsJson["documentsFolderPath"];

                // Set correct Documents path in settings if it is not already set
                if (string.IsNullOrEmpty(documentsPath) || !File.Exists(documentsPath))
                {
                    documentsPath = defaultDocumentsPath;
                    settingsJson["documentsFolderPath"] = documentsPath;
                    File.WriteAllText(settingsPath, settingsJson.ToString());
                }

                DocumentsPath = documentsPath;

                // Additional Presentation Template Folders
                var templatesToken = settingsJson["addedPresentationTemplatesPaths"];

                if (templatesToken is JArray templatesArray)
                {
                    foreach (var pathToken in templatesArray)
                    {
                        var path = (string?)pathToken;
                        if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
                            AddedPresentationTemplatesPaths.Add(path);
                    }
                }

                // Ollama URI
                var ollamaUriString = (string?)settingsJson["ollamaUri"];
                if (string.IsNullOrEmpty(ollamaUriString))
                {
                    throw new InvalidOperationException(
                        "The 'ollamaUri' setting is missing or empty in settings.json."
                    );
                }
                OllamaUri = new Uri(ollamaUriString);

                // Ollama Model
                var selectedModel = (string?)settingsJson["selectedModel"];
                if (string.IsNullOrEmpty(selectedModel))
                {
                    throw new InvalidOperationException(
                        "The 'selectedModel' setting is missing or empty in settings.json."
                    );
                }
                SelectedModel = selectedModel;

                // Add command to run MCP server in server config
                var json = File.ReadAllText(ServerConfigPath);
                var jObject = JObject.Parse(json);

                if (jObject["mcpServers"]?["libreoffice-server"] is JObject libreOfficeServer)
                {
                    var command = (string?)libreOfficeServer["command"];
                    if (string.IsNullOrEmpty(command) || !File.Exists(command))
                    {
                        libreOfficeServer["command"] = serverCommand;
                        File.WriteAllText(ServerConfigPath, jObject.ToString());
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error setting up config: {ex}");
            }
        }

        public async Task<bool> SaveChangedSettings(
            string newDocumentsPath,
            string newSelectedModel,
            List<string> newPresentationTemplatesPaths
        )
        {
#if DEBUG
            string settingsPath = "C:\\Users\\ben_t\\source\\repos\\LibreOfficeAI\\settings.json";
#else
            string settingsPath = Path.Combine(AppContext.BaseDirectory, "settings.json");
#endif

            // Read, update and write settings.json
            JObject settingsJson;
            try
            {
                settingsJson = JObject.Parse(await File.ReadAllTextAsync(settingsPath));
                settingsJson["documentsFolderPath"] = newDocumentsPath;
                settingsJson["selectedModel"] = newSelectedModel;

                // Store the array of template paths in settings.json
                settingsJson["addedPresentationTemplatesPaths"] = new JArray(
                    newPresentationTemplatesPaths ?? []
                );

                await File.WriteAllTextAsync(settingsPath, settingsJson.ToString());

                // Update the properties in the service as well
                DocumentsPath = newDocumentsPath;
                SelectedModel = newSelectedModel;
                AddedPresentationTemplatesPaths = newPresentationTemplatesPaths ?? [];
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Failed to update settings.json: {ex}");
                return false;
            }

            return true;
        }
    }
}
