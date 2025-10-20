using System;
using System.Diagnostics;
using LibreOfficeAI.Services;
using LibreOfficeAI.ViewModels;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;

namespace LibreOfficeAI
{
    /// <summary>
    /// An empty window that can be used on its own or navigated to within a Frame.
    /// </summary>
    public sealed partial class MainWindow : Window
    {
        public MainViewModel ViewModel { get; }
        public SettingsViewModel SettingsVM { get; }
        public HelpViewModel HelpVM { get; }

        public MainWindow(IServiceProvider serviceProvider, OllamaService ollamaService)
        {
            try
            {
                InitializeComponent();
                MainFrame.Navigate(typeof(LibreOfficeAI.Views.MainPage));

                // Get ViewModel from dependency injection container
                ViewModel = serviceProvider.GetRequiredService<MainViewModel>();
                SettingsVM = serviceProvider.GetRequiredService<SettingsViewModel>();
                HelpVM = serviceProvider.GetRequiredService<HelpViewModel>();

                // Subscribe to navigation events
                MainFrame.Navigating += (s, e) =>
                {
                    // Hide welcome elements during navigation
                    if (MainFrame.Content is LibreOfficeAI.Views.MainPage mainPage)
                    {
                        var welcomeContainer =
                            mainPage.FindName("WelcomeContainer") as FrameworkElement;
                        if (welcomeContainer != null)
                        {
                            welcomeContainer.Visibility = Visibility.Collapsed;
                        }
                    }
                };

                MainFrame.Navigated += (s, e) =>
                {
                    // Restore visibility after navigation completes
                    if (MainFrame.Content is LibreOfficeAI.Views.MainPage mainPage)
                    {
                        // Let the binding handle visibility
                    }
                };

                ViewModel.OnRequestNavigateToSettings += () =>
                {
                    SettingsVM.RefreshFromConfig();
                    MainFrame.Navigate(typeof(LibreOfficeAI.Views.SettingsPage));
                };

                ViewModel.OnRequestNavigateToHelp += () =>
                {
                    MainFrame.Navigate(typeof(LibreOfficeAI.Views.HelpPage));
                };

                SettingsVM.OnRequestNavigateToMainPage += () =>
                {
                    if (SettingsVM.SelectedModelChanged)
                    {
                        ollamaService.RefreshAsync();
                    }
                    MainFrame.Navigate(typeof(LibreOfficeAI.Views.MainPage));
                };

                HelpVM.OnRequestNavigateToMainPage += () =>
                {
                    MainFrame.Navigate(typeof(LibreOfficeAI.Views.MainPage));
                };
            }
            catch (Exception ex)
            {
                System.IO.File.WriteAllText("mainwindow_exception.txt", ex.ToString());
                throw;
            }
        }

        private async void SpaceAccelerator_Invoked(
            KeyboardAccelerator sender,
            KeyboardAcceleratorInvokedEventArgs args
        )
        {
            Debug.WriteLine("Space accelerator invoked");

            // Only handle spacebar on the MainPage
            if (MainFrame.Content is LibreOfficeAI.Views.MainPage mainPage)
            {
                // Check if TextBox has focus - if so, don't handle the accelerator
                var focusedElement = FocusManager.GetFocusedElement(this.Content.XamlRoot);
                Debug.WriteLine(
                    $"Window level - Currently focused element: {focusedElement?.GetType().Name}"
                );

                // Get the PromptTextBox from the MainPage
                var promptTextBox = mainPage.FindName("PromptTextBox") as TextBox;

                if (focusedElement == promptTextBox)
                {
                    Debug.WriteLine("TextBox has focus, not handling spacebar accelerator");
                    args.Handled = false; // Let the TextBox handle the space
                    return;
                }

                // Trigger microphone
                if (ViewModel.ToggleMicrophoneCommand.CanExecute(null))
                {
                    Debug.WriteLine(
                        "Window level - Executing ToggleMicrophone command via accelerator"
                    );
                    await ViewModel.ToggleMicrophoneCommand.ExecuteAsync(null);
                    args.Handled = true; // Mark as handled so space doesn't propagate
                }
                else
                {
                    Debug.WriteLine("Window level - ToggleMicrophone command cannot execute");
                    args.Handled = false;
                }
            }
            else
            {
                args.Handled = false; // Not on MainPage, don't handle
            }
        }
    }
}
