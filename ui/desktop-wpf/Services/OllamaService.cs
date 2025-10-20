using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using OllamaSharp;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides functionality for managing and interacting with the Ollama AI service, including initializing and
    /// configuring the service, managing AI models, and facilitating chat-based interactions.
    /// </summary>
    /// <remarks>The <see cref="OllamaService"/> class is responsible for orchestrating the Ollama AI service,
    /// including starting and stopping the service, managing AI models, and providing chat-based interfaces for
    /// external and internal interactions. It integrates with various services such as <see cref="DocumentService"/>,
    /// <see cref="ConfigurationService"/>, and <see cref="ToolService"/>  to provide a comprehensive AI-driven
    /// solution. <para> This class supports asynchronous operations for tasks such as starting the service, checking
    /// model availability, and pulling models from the server. It also ensures proper resource management by
    /// implementing the <see cref="IDisposable"/> interface. </para> <para> The service is initialized with a system
    /// prompt and an intent prompt, which are used to configure the behavior of the AI models. The class also provides
    /// mechanisms to refresh the service when configuration or model changes occur. </para></remarks>
    public partial class OllamaService : ObservableObject, IDisposable
    {
        private Process? _ollamaProcess;

        [ObservableProperty]
        private bool _ollamaReady = false;

        [ObservableProperty]
        private string? _ollamaStatus = null;

        [ObservableProperty]
        private double _modelPercentage = 0;
        public Chat ExternalChat { get; set; }
        private Chat InternalChat { get; set; }
        public OllamaApiClient Client { get; private set; }
        public ToolService ToolService { get; set; }

        private readonly DocumentService _documentService;
        private readonly ConfigurationService _config;
        private string IntentPrompt { get; set; }

        private readonly string systemPrompt;

        public OllamaService(DocumentService documentService, ConfigurationService config)
        {
            _documentService = documentService;
            _config = config;

            // Define an httpClient to allow the timeout to be extended
            var httpClient = new HttpClient()
            {
                BaseAddress = _config.OllamaUri,
                Timeout = TimeSpan.FromMinutes(5),
            };

            Client = new OllamaApiClient(httpClient, _config.SelectedModel);

            systemPrompt = LoadSystemPrompt();

            ExternalChat = new Chat(Client, systemPrompt);

            // Optionally configure Ollama hyperparameters (e.g. NumCtx, NumBatch, NumThread)
            //ExternalChat.Options = new RequestOptions { UseMmap = false };

            IntentPrompt = File.ReadAllText(config.IntentPromptPath);

            InternalChat = new Chat(Client, IntentPrompt);

            // Initialise the ToolService with its own chat
            ToolService = new ToolService(InternalChat, config);
        }

        private string LoadSystemPrompt()
        {
            var prompt = File.ReadAllText(_config.SystemPromptPath);

            // Add Document Folder Path
            prompt += $" Documents folder: {_config.DocumentsPath}.";

            // Add list of all available documents
            string documentsString = _documentService.GetAvailableDocumentsString();
            if (!string.IsNullOrEmpty(documentsString))
            {
                prompt += $" Available documents in Documents folder: {documentsString}.";
            }

            string presentationTemplatesString = _documentService.GetPresentationTemplatesString();
            if (!string.IsNullOrEmpty(presentationTemplatesString))
            {
                prompt += $" Presentation Template Names: {presentationTemplatesString}.";
                prompt +=
                    " If the user gives you a template, make sure the name exactly matches one of these.";
            }

            return prompt;
        }

        // Create a new chat
        public void RefreshChat()
        {
            string systemPrompt = LoadSystemPrompt();

            ExternalChat = new Chat(Client, systemPrompt);
            ToolService.RefreshChat();
            _documentService.ClearDocumentsInUse();
        }

        // Run Ollama
        public async Task StartAsync()
        {
            OllamaStatus = "Loading AI model...";
            await StopExistingOllamaProcesses();
            await StartOllamaServerAsync();
            bool modelLoaded = await CheckModelLoadedAsync();

            Debug.WriteLine($"Model loaded: {modelLoaded}");

            if (!modelLoaded)
            {
                OllamaReady = await Task.Run(() => PullModelAsync());
            }
            else
            {
                OllamaReady = true;
                OllamaStatus = null;
            }
        }

        private async Task StartOllamaServerAsync()
        {
            Debug.WriteLine("Starting Ollama server");
            await Task.Run(() =>
            {
                var psi = new ProcessStartInfo
                {
                    FileName = _config.OllamaPath,
                    Arguments = "serve",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                };

                psi.EnvironmentVariables["OLLAMA_MODELS"] = _config.OllamaModelsDir;

                _ollamaProcess = new Process { StartInfo = psi, EnableRaisingEvents = true };

                _ollamaProcess.OutputDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        Debug.WriteLine($"Ollama: {e.Data}");
                };

                _ollamaProcess.ErrorDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        Debug.WriteLine($"Ollama: {e.Data}");
                };

                _ollamaProcess.Start();
                _ollamaProcess.BeginOutputReadLine();
                _ollamaProcess.BeginErrorReadLine();
            });
        }

        // Stop the Ollama process
        public void Stop()
        {
            if (_ollamaProcess != null && !_ollamaProcess.HasExited)
            {
                try
                {
                    _ollamaProcess.Kill(true);
                    _ollamaProcess.Dispose();
                }
                catch
                {
                    Debug.WriteLine("Error stopping Ollama");
                }
            }
        }

        public void Dispose()
        {
            Stop();
            GC.SuppressFinalize(this);
        }

        // Verify that the correct model exists in the models folder
        public async Task<bool> CheckModelLoadedAsync()
        {
            Debug.WriteLine("Checking if model loaded");

            try
            {
                var models = await Client.ListLocalModelsAsync();

                Debug.WriteLine(
                    $"Available models: {string.Join(", ", models.Select(m => m.Name))}"
                );

                bool modelFound = models.Any(m =>
                    m.Name.Contains(_config.SelectedModel, StringComparison.OrdinalIgnoreCase)
                );

                Debug.WriteLine($"Model '{_config.SelectedModel}' found: {modelFound}");

                return modelFound;
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine(
                    $"HTTP error checking models (server might not be ready): {ex.Message}"
                );
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error checking if model loaded: {ex.Message}");
                return false;
            }
        }

        public async Task<bool> CheckModelExists(string modelName)
        {
            try
            {
                await foreach (var response in Client.PullModelAsync(modelName))
                {
                    // If it is possible to pull any of the model, then it exists
                    if (response?.Completed > 0)
                        return true;
                }
                // If the stream completes without yielding, treat as not available
                return false;
            }
            catch (OllamaSharp.Models.Exceptions.ResponseError)
            {
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error checking if model can be pulled: {ex.Message}");
                return false;
            }
        }

        private async Task<bool> PullModelAsync()
        {
            Debug.WriteLine($"Pulling ollama model: {_config.SelectedModel}");

            OllamaStatus = $"Pulling ollama model: {_config.SelectedModel}";

            double lastPercent = -1; // Track the last percentage to avoid duplicate updates

            try
            {
                await foreach (var response in Client.PullModelAsync(_config.SelectedModel))
                {
                    // Show update when percentage has changed significantly
                    if (response?.Percent > 0 && Math.Abs(response.Percent - lastPercent) >= 0.1)
                    {
                        lastPercent = response.Percent;
                        Debug.WriteLine($"Pull progress: {response.Percent:F1}%");

                        OllamaStatus =
                            $"Pulling ollama model: {_config.SelectedModel} - {response.Percent:F1}% complete.";
                        ModelPercentage = response.Percent;
                    }
                }

                Debug.WriteLine($"Successfully pulled model: {_config.SelectedModel}");
                OllamaStatus = "";
                return true;
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine($"HTTP error pulling model: {ex.Message}");
                return false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error pulling model: {ex.Message}");
                return false;
            }
        }

        private static async Task StopExistingOllamaProcesses()
        {
            Debug.WriteLine("Stopping existing Ollama Processes");
            try
            {
                var processNames = new[] { "ollama", "ollama app" };

                foreach (var name in processNames)
                {
                    var processes = Process.GetProcessesByName(name);
                    foreach (var process in processes)
                    {
                        try
                        {
                            process.Kill();
                            process.WaitForExit(5000); // Wait up to 5 seconds
                        }
                        catch (Exception ex)
                        {
                            Debug.WriteLine(
                                $"Failed to stop Ollama process {process.Id}: {ex.Message}"
                            );
                        }
                    }
                }

                await Task.Delay(1000);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error stopping existing Ollama processes: {ex.Message}");
            }
        }

        // If the selected Model is updated, the OllamaService must be refreshed
        public async Task RefreshAsync()
        {
            OllamaReady = false;
            OllamaStatus = null;

            // Recreate HttpClient
            var httpClient = new HttpClient()
            {
                BaseAddress = _config.OllamaUri,
                Timeout = TimeSpan.FromMinutes(5),
            };

            // Update client with the new model
            Client = new OllamaApiClient(httpClient, _config.SelectedModel);

            // Reload prompts
            string newSystemPrompt = LoadSystemPrompt();
            string newIntentPrompt = File.ReadAllText(_config.IntentPromptPath);

            // Recreate chats
            ExternalChat = new Chat(Client, newSystemPrompt);
            InternalChat = new Chat(Client, newIntentPrompt);

            // Recreate ToolService
            ToolService = new ToolService(InternalChat, _config);

            // Clear documents in use
            _documentService.ClearDocumentsInUse();

            // Check if the model is loaded, pull if not
            OllamaStatus = "Checking model...";
            bool modelLoaded = await CheckModelLoadedAsync();
            if (!modelLoaded)
            {
                OllamaReady = await Task.Run(() => PullModelAsync());
            }
            else
            {
                OllamaReady = true;
                OllamaStatus = null;
            }
        }
    }
}
