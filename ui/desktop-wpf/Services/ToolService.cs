using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using Microsoft.Extensions.Logging;
using OllamaSharp;
using OllamaSharp.ModelContextProtocol;
using OllamaSharp.ModelContextProtocol.Server;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides functionality for managing and interacting with tools retrieved from MCP servers.
    /// </summary>
    /// <remarks>The <see cref="ToolService"/> class is responsible for discovering available tools from MCP
    /// servers, determining which tools are needed based on user prompts, and managing the state of these tools. It
    /// also provides methods for refreshing the internal chat context and handling processes on specific
    /// ports.</remarks>
    public partial class ToolService : ObservableObject
    {
        private readonly ConfigurationService _config;
        private McpClientTool[]? AvailableTools { get; set; }
        private HashSet<McpClientTool> NeededTools { get; set; } = [];

        [ObservableProperty]
        public string? _toolsStatus = null;

        [ObservableProperty]
        public bool _toolsLoaded = false;

        [ObservableProperty]
        public string? _toolsError = null;

        private Chat InternalChat { get; set; }

        public ToolService(Chat internalChat, ConfigurationService config)
        {
            // Async call to find tools from MCP server
            _ = Task.Run(async () => await FindTools());
            InternalChat = internalChat;
            _config = config;
        }

        // Get list of tools from MCP Server
        private async Task FindTools()
        {
            const int maxRetries = 3;
            const int portToKill = 8765;

            for (int attempt = 1; attempt <= maxRetries; attempt++)
            {
                try
                {
                    ToolsStatus =
                        attempt == 1
                            ? "Connecting to LibreOffice..."
                            : $"Retrying connection (attempt {attempt})...";

                    // Detailed logging for McpClient
                    var loggerFactory = LoggerFactory.Create(builder =>
                    {
                        builder.AddDebug().SetMinimumLevel(LogLevel.Debug);
                    });

                    var options = new McpClientOptions { LoggerFactory = loggerFactory };

                    AvailableTools = await Tools.GetFromMcpServers(
                        _config.ServerConfigPath,
                        options
                    );

                    ToolsLoaded = true;
                    ToolsStatus = null;
                    Debug.WriteLine("Tools loaded");
                    return;
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"Attempt {attempt} failed: {ex}");

                    if (attempt < maxRetries)
                    {
                        Debug.WriteLine($"Killing process on port {portToKill} and retrying...");
                        KillProcessOnPort(portToKill);

                        // Optional: Add a small delay before retry
                        await Task.Delay(1000);
                    }
                    else
                    {
                        // Final attempt failed
                        ToolsError = $"Error after {maxRetries} attempts: {ex}";
                        Debug.WriteLine(ex.ToString());
                    }
                }
            }
        }

        // Use internal chat to decide which tools the user may need
        public async Task<McpClientTool[]?> FindNeededTools(string prompt)
        {
            if (AvailableTools == null)
                return null;

            Debug.WriteLine("Checking for needed tools");

            var neededToolsResponse = new StringBuilder();
            bool thinking = false;

            await foreach (var answerToken in InternalChat.SendAsync(prompt))
            {
                // If the model uses thinking, discount output within thinking tags
                if (answerToken == "<think>")
                    thinking = true;

                if (answerToken == "</think>")
                {
                    thinking = false;
                    continue;
                }

                if (!thinking)
                    neededToolsResponse.Append(answerToken);
            }

            var responseString = neededToolsResponse.ToString();
            Debug.WriteLine(responseString);

            foreach (McpClientTool tool in AvailableTools)
            {
                if (tool.Function?.Name != null && responseString.Contains(tool.Function.Name))
                {
                    NeededTools.Add(tool);
                }
            }

            return [.. NeededTools];
        }

        public void RefreshChat()
        {
            Debug.WriteLine(InternalChat.Messages.Count);
            // Remove all messages except the first which is the intent prompt
            InternalChat.Messages.RemoveRange(1, InternalChat.Messages.Count - 1);
            Debug.WriteLine(InternalChat.Messages.Count);
            NeededTools.Clear();
        }

        public static void KillProcessOnPort(int port)
        {
            // Step 1: Find the PID using netstat
            var netstat = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "netstat",
                    Arguments = $"-ano | findstr :{port}",
                    RedirectStandardOutput = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                },
            };
            netstat.Start();
            string output = netstat.StandardOutput.ReadToEnd();
            netstat.WaitForExit();

            // Step 2: Parse the PID from netstat output
            var lines = output.Split([Environment.NewLine], StringSplitOptions.RemoveEmptyEntries);
            foreach (var line in lines)
            {
                var parts = line.Split([' '], StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length >= 5)
                {
                    if (int.TryParse(parts[4], out int pid))
                    {
                        // Step 3: Kill the process
                        try
                        {
                            Process.GetProcessById(pid).Kill();
                            Console.WriteLine($"Killed process {pid} on port {port}");
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Failed to kill process {pid}: {ex.Message}");
                        }
                    }
                }
            }
        }
    }
}
