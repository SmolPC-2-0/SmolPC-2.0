using System;
using LibreOfficeAI.ViewModels;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Documents;
using Windows.Storage;
using Windows.Storage.Pickers;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace LibreOfficeAI.Views
{
    /// <summary>
    /// An empty page that can be used on its own or navigated to within a Frame.
    /// </summary>
    public sealed partial class SettingsPage : Page
    {
        public SettingsViewModel ViewModel { get; }

        public SettingsPage()
        {
            InitializeComponent();

            ViewModel = App.Services.GetRequiredService<SettingsViewModel>();

            RootGrid.DataContext = ViewModel;
        }

        private async void PickFolderButton_Click(object sender, RoutedEventArgs e)
        {
            //disable the button to avoid double-clicking
            var senderButton = sender as Button;
            senderButton.IsEnabled = false;

            // Create a folder picker
            FolderPicker openPicker = new();

            // See the sample code below for how to make the window accessible from the App class.
            var window = App.MainWindow;

            // Retrieve the window handle (HWND) of the current WinUI 3 window.
            var hWnd = WinRT.Interop.WindowNative.GetWindowHandle(window);

            // Initialize the folder picker with the window handle (HWND).
            WinRT.Interop.InitializeWithWindow.Initialize(openPicker, hWnd);

            // Set options for your folder picker
            openPicker.SuggestedStartLocation = PickerLocationId.Desktop;
            openPicker.FileTypeFilter.Add("*");

            // Open the picker for the user to pick a folder
            StorageFolder folder = await openPicker.PickSingleFolderAsync();
            if (folder != null)
            {
                if (senderButton.Name == "PickDocumentsFolderButton")
                {
                    ViewModel.DocumentsPath = folder.Path;
                }
                else if (senderButton.Name == "PickTemplatesFolderButton")
                {
                    ViewModel.AddedPresentationTemplatesPaths.Add(folder.Path);
                }
            }

            //re-enable the button
            senderButton.IsEnabled = true;
        }

        // Open TeachingTip elements when info buttons are clicked
        private void Info_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.Tag is string tipName)
            {
                if (FindName(tipName) is TeachingTip tip)
                {
                    tip.IsOpen = true;
                }
            }
        }

        // Open links
        private void OnTeachingTipLinkClick(Hyperlink sender, HyperlinkClickEventArgs e)
        {
            var uri = sender.NavigateUri;
            if (uri != null)
            {
                Windows.System.Launcher.LaunchUriAsync(uri);
            }
        }

        private void RemovePath_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button button && button.Tag is string path)
            {
                ViewModel.RemovePresentationTemplatePathCommand.Execute(path);
            }
        }
    }
}
