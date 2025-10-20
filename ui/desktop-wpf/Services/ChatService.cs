using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using LibreOfficeAI.Models;
using Microsoft.UI.Dispatching;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides functionality for managing chat interactions, including sending messages, handling AI responses, and
    /// managing chat-related events and state.
    /// </summary>
    /// <remarks>The <see cref="ChatService"/> class facilitates communication between the user and an AI
    /// system. It manages the chat message collection, handles AI responses, and provides methods for sending messages,
    /// canceling prompts, and starting new chats. This class also raises events to notify the UI of changes, such as
    /// scrolling to the bottom of the chat or refreshing commands.  This service depends on several other services,
    /// including <see cref="OllamaService"/> for AI interactions, <see cref="DocumentService"/> for managing documents
    /// in use, and <see cref="ConfigurationService"/> for configuration settings.</remarks>
    public partial class ChatService : ObservableObject
    {
        private readonly OllamaService ollamaService;
        private readonly DocumentService documentService;
        private readonly ConfigurationService config;
        private readonly DispatcherQueue dispatcherQueue;

        [ObservableProperty]
        private bool _aiTurn = false;

        [ObservableProperty]
        private ObservableCollection<ChatMessage> _chatMessages = [];

        public bool CanSendMessage(string promptText) =>
            !AiTurn
            && !string.IsNullOrWhiteSpace(promptText)
            && ollamaService.ToolService.ToolsLoaded;

        // Cancellation token
        private CancellationTokenSource _cts = new();

        // Events
        public event Action? RequestScrollToBottom;
        public event Action? RequestFocusTextBox;
        public event Action? RequestCommandRefresh;

        public ChatService(
            OllamaService ollamaService,
            DocumentService documentService,
            ConfigurationService config,
            Func<DispatcherQueue> dispatcherQueueFactory
        )
        {
            this.ollamaService = ollamaService;
            this.documentService = documentService;
            this.dispatcherQueue = dispatcherQueueFactory();
            this.config = config;

            SetupToolEventHandlers();

            ChatMessages.CollectionChanged += (sender, e) =>
            {
                OnPropertyChanged(nameof(ChatMessages));
            };
        }

        // Create ChatMessage and send input to AI
        public async Task SendMessageAsync(string userInput)
        {
            // Add user message
            ChatMessages.Add(new ChatMessage { Text = userInput, Type = MessageType.User });
            RequestScrollToBottom?.Invoke();

            // Send to AI
            await SendPromptAsync(userInput);
        }

        public void CancelPrompt()
        {
            _cts.Cancel();
            if (ChatMessages.Count > 0)
                ChatMessages.RemoveAt(ChatMessages.Count - 1);

            AiTurn = false;
            _cts = new CancellationTokenSource();
        }

        public void NewChat()
        {
            ollamaService.RefreshChat();
            ChatMessages.Clear();
            SetupToolEventHandlers();
        }

        private async Task SendPromptAsync(string prompt)
        {
            // Check that the service is running
            try
            {
                bool connected = await ollamaService.Client.IsRunningAsync();
                if (connected)
                    Debug.WriteLine("Ollama Client running");
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine(ex.Message);
                SendErrorMessage("Could not find the AI service.");
                return;
            }

            // Create a new AI message
            AiTurn = true;
            var aiMessage = new ChatMessage
            {
                Text = "",
                Type = MessageType.AI,
                IsLoading = true,
                IsThinking = false,
            };
            ChatMessages.Add(aiMessage);

            // Wait for UI to update
            await Task.Delay(2);
            RequestScrollToBottom?.Invoke();

            var response = new StringBuilder();

            // Full response for debugging
            var fullResponse = new StringBuilder();

            try
            {
                // First run the prompt on the internal chat, to find useful tools
                var toolsToCall = await Task.Run(() =>
                    ollamaService.ToolService.FindNeededTools(prompt)
                );

                // Log all suggested tools
                if (toolsToCall != null)
                {
                    foreach (var tool in toolsToCall)
                    {
                        Debug.WriteLine(tool?.Function?.Name);
                    }
                }

                // If any documents are in use, add the file paths to the user prompt
                string documentsInUseString = documentService.GetDocumentsInUseString();
                if (!string.IsNullOrEmpty(documentsInUseString))
                {
                    prompt += $" Current documents: {documentsInUseString}.";
                }

                // Stream the AI response and update the message for each token
                await Task.Run(async () =>
                {
                    await foreach (
                        var answerToken in ollamaService.ExternalChat.SendAsync(
                            prompt,
                            toolsToCall,
                            null, // imagesAsBase64
                            null, // format
                            _cts.Token
                        )
                    )
                    {
                        fullResponse.Append(answerToken);

                        if (aiMessage.IsLoading)
                        {
                            dispatcherQueue.TryEnqueue(() => aiMessage.IsLoading = false);
                        }

                        // Check if the model has started thinking
                        if (answerToken == "<think>")
                        {
                            dispatcherQueue.TryEnqueue(() => aiMessage.IsThinking = true);
                            continue;
                        }

                        // If the model has stopped thinking, we can show the next token
                        if (answerToken == "</think>")
                        {
                            dispatcherQueue.TryEnqueue(() => aiMessage.IsThinking = false);
                            continue;
                        }

                        // If the model is not thinking, print tokens
                        if (!aiMessage.IsThinking)
                        {
                            // Prevent newlines being added after thinking
                            if (response.Length != 0 || !string.IsNullOrWhiteSpace(answerToken))
                            {
                                response.Append(answerToken);
                                dispatcherQueue.TryEnqueue(() =>
                                {
                                    aiMessage.Text = response.ToString();

                                    // Scroll to the bottom
                                    RequestScrollToBottom?.Invoke();
                                });
                            }

                            await Task.Delay(10); // Slightly longer delay for better visual effect
                        }
                    }
                });
            }
            catch (HttpRequestException)
            {
                aiMessage.IsLoading = false;
                AiTurn = false;
                SendErrorMessage("Error connecting to AI - please restart application.");
            }

            Debug.WriteLine(fullResponse);
            AiTurn = false;
            RequestCommandRefresh?.Invoke();
            RequestFocusTextBox?.Invoke();
        }

        private void SendErrorMessage(string message)
        {
            var errorMessage = new ChatMessage { Text = message, Type = MessageType.Error };
            ChatMessages.Add(errorMessage);
        }

        public void RegisterToolCall(string tool)
        {
            dispatcherQueue.TryEnqueue(() =>
            {
                var currentMessage = ChatMessages[^1];
                currentMessage.ToolCalls.Add(tool);
                Debug.WriteLine(tool);
            });
        }

        private void SetupToolEventHandlers()
        {
            // Add event listener for tool calls
            ollamaService.ExternalChat.OnToolCall += (sender, toolCall) =>
            {
                if (toolCall.Function?.Name != null)
                {
                    Debug.WriteLine($"Tool called: {toolCall.Function.Name}");
                    RegisterToolCall(toolCall.Function.Name);

                    foreach (var argument in toolCall.Function.Arguments)
                    {
                        Debug.WriteLine(argument.ToString());
                    }
                }
            };

            // Add event listener for tool results
            ollamaService.ExternalChat.OnToolResult += (sender, result) =>
            {
                Debug.WriteLine($"Tool result: {result.Result}");

                var arguments = result.ToolCall.Function?.Arguments;
                var function = result.ToolCall.Function?.Name;

                // Add any documents used to the list of current documents
                if (arguments != null)
                {
                    foreach (var key in new[] { "file_path", "source_path", "target_path" })
                    {
                        if (arguments.TryGetValue(key, out var value))
                        {
                            // value is returned as an object
                            var filePath = value as string ?? value?.ToString();
                            if (!string.IsNullOrEmpty(filePath))
                            {
                                Debug.WriteLine($"Adding file to docs in use: {filePath}");
                                dispatcherQueue.TryEnqueue(() =>
                                {
                                    documentService.AddDocumentInUse(filePath);
                                });
                            }
                        }
                    }

                    // Specific to create_blank_document and create_blank_presentation functions
                    if (arguments.TryGetValue("filename", out var fileNameObj))
                    {
                        // value is returned as an object - cast to string
                        string? fileName = fileNameObj as string ?? fileNameObj?.ToString();
                        if (string.IsNullOrEmpty(fileName))
                            return;

                        // Add file extension if not included in the fileName
                        if (function == "create_blank_document")
                        {
                            string? fileExtension = documentService.writerExtensions.FirstOrDefault(
                                ext => fileName.EndsWith(ext, StringComparison.OrdinalIgnoreCase)
                            );

                            if (string.IsNullOrEmpty(fileExtension))
                            {
                                fileExtension = ".odt";
                                fileName += fileExtension;
                            }
                        }

                        if (function == "create_blank_presentation")
                        {
                            string? fileExtension =
                                documentService.impressExtensions.FirstOrDefault(ext =>
                                    fileName.EndsWith(ext, StringComparison.OrdinalIgnoreCase)
                                );

                            if (string.IsNullOrEmpty(fileExtension))
                            {
                                fileExtension = ".odp";
                                fileName += fileExtension;
                            }
                        }

                        // Add the base documents path
                        string filePath = $"{config.DocumentsPath}\\{fileName}";

                        Debug.WriteLine($"Adding file to docs in use: {filePath}");
                        dispatcherQueue.TryEnqueue(() =>
                        {
                            documentService.AddDocumentInUse(filePath);
                        });
                    }
                }
            };
        }
    }
}
