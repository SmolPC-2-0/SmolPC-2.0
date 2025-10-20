using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using LibreOfficeAI.Models;
using LibreOfficeAI.Services;
using Microsoft.UI.Dispatching;

namespace LibreOfficeAI.ViewModels
{
    public partial class MainViewModel : ObservableObject
    {
        private readonly OllamaService _ollamaService;
        private readonly DocumentService _documentService;
        private readonly ChatService _chatService;
        private readonly UserPromptService _userPromptService;
        private readonly DispatcherQueue _dispatcherQueue;
        private readonly AudioService _audioService;
        private readonly WhisperService _whisperService;

        // Properties needed for UI
        public bool AppLoaded => OllamaReady && ToolsLoaded;
        public bool OllamaReady => _ollamaService.OllamaReady;
        public string? OllamaStatus => _ollamaService.OllamaStatus;
        public double ModelPercentage => _ollamaService.ModelPercentage;
        public bool ToolsLoaded => _ollamaService.ToolService.ToolsLoaded;
        public string? ToolsStatus => _ollamaService.ToolService.ToolsStatus;
        public string? ToolsError => _ollamaService.ToolService.ToolsError;
        public bool ShowWelcomeScreen => ChatMessages.Count == 0;
        public bool IsRecording => _audioService.IsRecording;
        public bool IsTranscribing => _whisperService.IsTranscribing;

        // Prompt handled by userPromptService
        public string PromptText
        {
            get => _userPromptService.PromptText;
            set => _userPromptService.PromptText = value;
        }
        public bool IsSendButtonVisible => _userPromptService.IsSendButtonVisible;

        // Chat handled by ChatService
        public ObservableCollection<ChatMessage> ChatMessages => _chatService.ChatMessages;
        public bool AiTurn => _chatService.AiTurn;

        // Enable/disable typing
        public bool CanType => !IsRecording && !IsTranscribing && !AiTurn;

        // Documents
        public ObservableCollection<Document> DocumentsInUse => _documentService.DocumentsInUse;

        // Events
        public event Action? RequestScrollToBottom
        {
            add => _chatService.RequestScrollToBottom += value;
            remove => _chatService.RequestScrollToBottom -= value;
        }

        public event Action? FocusTextBox
        {
            add => _userPromptService.FocusTextBox += value;
            remove => _userPromptService.FocusTextBox -= value;
        }

        public event Action? OnRequestNavigateToSettings;
        public event Action? OnRequestNavigateToHelp;

        public event Action? RecordingStateChanged;

        public MainViewModel(
            OllamaService ollamaService,
            DocumentService documentService,
            ChatService chatService,
            UserPromptService userPromptService,
            AudioService audioService,
            WhisperService whisperService,
            Func<DispatcherQueue> dispatcherQueueFactory
        )
        {
            _ollamaService = ollamaService;
            _documentService = documentService;
            _chatService = chatService;
            _userPromptService = userPromptService;
            _audioService = audioService;
            _whisperService = whisperService;
            _dispatcherQueue = dispatcherQueueFactory();

            // Subscribe to property changes for UI updates
            _ollamaService.PropertyChanged += OnServicePropertyChanged;
            _ollamaService.ToolService.PropertyChanged += OnServicePropertyChanged;

            _userPromptService.PropertyChanged += OnUIStatePropertyChanged;

            _chatService.PropertyChanged += OnChatServicePropertyChanged;
            _chatService.RequestCommandRefresh += OnRequestCommandRefresh;
            _chatService.RequestFocusTextBox += OnRequestFocusTextBox;
            _chatService.ChatMessages.CollectionChanged += (s, e) =>
            {
                _dispatcherQueue.TryEnqueue(() =>
                {
                    OnPropertyChanged(nameof(ShowWelcomeScreen));
                });
            };

            _audioService.RecordingStateChanged += OnAudioRecordingStateChanged;

            _whisperService.IsTranscribingChanged += () =>
            {
                _dispatcherQueue.TryEnqueue(() =>
                {
                    OnPropertyChanged(nameof(IsTranscribing));
                    OnPropertyChanged(nameof(CanType));
                });
            };
        }

        // Commands

        // Chat Service
        // Sends a message to the AI Chat service
        [RelayCommand(CanExecute = nameof(CanSendMessage))]
        private async Task SendMessageAsync()
        {
            string userInput = PromptText.Trim();
            if (string.IsNullOrEmpty(userInput))
                return;

            // Delegate to services
            _userPromptService.ClearPrompt();
            await _chatService.SendMessageAsync(userInput);
            _userPromptService.RequestFocus();
        }

        // Determines if a message can be sent based on current state
        private bool CanSendMessage() => _chatService.CanSendMessage(PromptText);

        [RelayCommand]
        private void CancelPrompt()
        {
            _chatService.CancelPrompt();
            SendMessageCommand.NotifyCanExecuteChanged();
        }

        [RelayCommand]
        private void NewChat()
        {
            _chatService.NewChat();
        }

        // Buttons
        [RelayCommand]
        private void SettingsButton_Click()
        {
            OnRequestNavigateToSettings?.Invoke();
        }

        [RelayCommand]
        private void HelpButton_Click()
        {
            OnRequestNavigateToHelp?.Invoke();
        }

        //Audio Service
        [RelayCommand]
        private async Task ToggleMicrophoneAsync()
        {
            await _audioService.ToggleRecordingAsync();
        }

        // Property change handlers
        private void OnServicePropertyChanged(
            object? sender,
            System.ComponentModel.PropertyChangedEventArgs e
        )
        {
            _dispatcherQueue.TryEnqueue(() =>
            {
                switch (e.PropertyName)
                {
                    case nameof(OllamaService.OllamaReady):
                        OnPropertyChanged(nameof(OllamaReady));
                        OnPropertyChanged(nameof(AppLoaded));
                        SendMessageCommand.NotifyCanExecuteChanged();
                        break;
                    case nameof(OllamaService.OllamaStatus):
                        OnPropertyChanged(nameof(OllamaStatus));
                        break;
                    case nameof(OllamaService.ModelPercentage):
                        OnPropertyChanged(nameof(ModelPercentage));
                        break;
                    case nameof(OllamaService.ToolService.ToolsLoaded):
                        OnPropertyChanged(nameof(ToolsLoaded));
                        OnPropertyChanged(nameof(AppLoaded));
                        SendMessageCommand.NotifyCanExecuteChanged();
                        break;
                    case nameof(OllamaService.ToolService.ToolsStatus):
                        OnPropertyChanged(nameof(ToolsStatus));
                        break;
                    case nameof(OllamaService.ToolService.ToolsError):
                        OnPropertyChanged(nameof(ToolsError));
                        break;
                }
            });
        }

        private void OnUIStatePropertyChanged(
            object? sender,
            System.ComponentModel.PropertyChangedEventArgs e
        )
        {
            _dispatcherQueue.TryEnqueue(() =>
            {
                OnPropertyChanged(nameof(PromptText));
                OnPropertyChanged(nameof(IsSendButtonVisible));
                SendMessageCommand.NotifyCanExecuteChanged();
            });
        }

        private void OnChatServicePropertyChanged(
            object? sender,
            System.ComponentModel.PropertyChangedEventArgs e
        )
        {
            _dispatcherQueue.TryEnqueue(() =>
            {
                OnPropertyChanged(nameof(AiTurn));
                OnPropertyChanged(nameof(CanType));
                OnPropertyChanged(nameof(ShowWelcomeScreen));
                SendMessageCommand.NotifyCanExecuteChanged();
            });
        }

        private void OnAudioRecordingStateChanged()
        {
            _dispatcherQueue.TryEnqueue(() =>
            {
                OnPropertyChanged(nameof(IsRecording));
                OnPropertyChanged(nameof(CanType));
                RecordingStateChanged?.Invoke();
            });
        }

        // Event handlers for ChatService events
        private void OnRequestCommandRefresh()
        {
            _dispatcherQueue.TryEnqueue(() =>
            {
                SendMessageCommand.NotifyCanExecuteChanged();
            });
        }

        private void OnRequestFocusTextBox()
        {
            _userPromptService.RequestFocus();
        }
    }
}
