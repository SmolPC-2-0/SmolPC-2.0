using System;
using CommunityToolkit.Mvvm.ComponentModel;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides functionality for managing user prompts, including text input and related UI interactions.
    /// </summary>
    /// <remarks>This service is designed to handle user input prompts, such as managing the prompt text,
    /// controlling the visibility of the send button based on the input, and triggering UI events like focusing the
    /// text box.</remarks>
    public partial class UserPromptService : ObservableObject
    {
        [ObservableProperty]
        private string _promptText = string.Empty;

        [ObservableProperty]
        private bool _isSendButtonVisible = false;

        // Events for UI interactions
        public event Action? FocusTextBox;

        partial void OnPromptTextChanged(string value)
        {
            IsSendButtonVisible = !string.IsNullOrWhiteSpace(value);
        }

        public void ClearPrompt()
        {
            PromptText = string.Empty;
        }

        public void RequestFocus()
        {
            FocusTextBox?.Invoke();
        }
    }
}
