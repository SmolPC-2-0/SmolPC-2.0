using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using LibreOfficeAI.Services;

namespace LibreOfficeAI.ViewModels
{
    public partial class SettingsViewModel : ObservableObject
    {
        private readonly ConfigurationService _config;
        private readonly OllamaService _ollamaService;

        [ObservableProperty]
        private string? settingsChangedMessage = null;

        [ObservableProperty]
        private string documentsPath;

        [ObservableProperty]
        private string selectedModel;
        public bool SelectedModelChanged { get; private set; } = false;

        public IEnumerable<string> DefaultPresentationTemplatesPaths =>
            _config.defaultTemplatesPaths.AsEnumerable();

        public ObservableCollection<string> AddedPresentationTemplatesPaths;

        public event Action? OnRequestNavigateToMainPage;

        public SettingsViewModel(ConfigurationService config, OllamaService ollamaService)
        {
            _config = config;
            _ollamaService = ollamaService;
            DocumentsPath = config.DocumentsPath;
            SelectedModel = config.SelectedModel;
            AddedPresentationTemplatesPaths = new ObservableCollection<string>(
                config.AddedPresentationTemplatesPaths
            );
        }

        [RelayCommand]
        private async Task Save()
        {
            // Check if nothing has changed
            if (
                DocumentsPath == _config.DocumentsPath
                && SelectedModel == _config.SelectedModel
                && AddedPresentationTemplatesPaths.SequenceEqual(
                    _config.AddedPresentationTemplatesPaths
                )
            )
            {
                ShowSettingsChangedMessageAsync("ℹ️ No changes made");
                return;
            }

            // If user has changed the AI model
            if (SelectedModel != _config.SelectedModel)
            {
                bool validModel = await _ollamaService.CheckModelExists(SelectedModel);

                if (validModel)
                {
                    SelectedModelChanged = true;
                }
                else
                {
                    ShowSettingsChangedMessageAsync("❌ AI model could not be found.");
                    return;
                }
            }

            bool settingsSaved = await _config.SaveChangedSettings(
                DocumentsPath,
                SelectedModel,
                [.. AddedPresentationTemplatesPaths]
            );

            if (settingsSaved)
            {
                await ShowSettingsChangedMessageAsync("✅ Changes saved");
            }
            else
            {
                await ShowSettingsChangedMessageAsync("❌ Error saving changes");
            }
        }

        [RelayCommand]
        private void ResetDefaults()
        {
            DocumentsPath = _config.defaultDocumentsPath;
            SelectedModel = _config.defaultModel;
            AddedPresentationTemplatesPaths.Clear();
        }

        [RelayCommand]
        private void BackButton_Click()
        {
            OnRequestNavigateToMainPage?.Invoke();
        }

        [RelayCommand]
        private void RemovePresentationTemplatePath(string? path)
        {
            if (!string.IsNullOrWhiteSpace(path) && AddedPresentationTemplatesPaths.Contains(path))
            {
                AddedPresentationTemplatesPaths.Remove(path);
            }
        }

        public void RefreshFromConfig()
        {
            DocumentsPath = _config.DocumentsPath;
            SelectedModel = _config.SelectedModel;
            AddedPresentationTemplatesPaths = new ObservableCollection<string>(
                _config.AddedPresentationTemplatesPaths
            );
        }

        private async Task ShowSettingsChangedMessageAsync(string message)
        {
            SettingsChangedMessage = message;
            await Task.Delay(5000);
            SettingsChangedMessage = null;
        }
    }
}
