using System;
using System.IO;
using LibreOfficeAI.Services;
using LibreOfficeAI.ViewModels;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace LibreOfficeAI
{
    /// <summary>
    /// Provides application-specific behavior to supplement the default Application class.
    /// </summary>
    public partial class App : Application
    {
        private Window? _window;
        private readonly IHost _host;

        public static Window MainWindow => ((App)Current)._window;

        /// <summary>
        /// Initializes the singleton application object.  This is the first line of authored code
        /// executed, and as such is the logical equivalent of main() or WinMain().
        /// </summary>
        public App()
        {
            this.UnhandledException += App_UnhandledException;

            try
            {
                InitializeComponent();
            }
            catch (Exception ex)
            {
                // Capture any exception during InitializeComponent
                File.WriteAllText(
                    "app_initialization_exception.txt",
                    $"Exception during App.InitializeComponent():\n"
                        + $"Message: {ex.Message}\n"
                        + $"Stack Trace: {ex.StackTrace}\n"
                        + $"Inner Exception: {ex.InnerException?.ToString() ?? "None"}\n"
                        + $"HResult: {ex.HResult}\n"
                        + $"Source: {ex.Source}"
                );
                throw;
            }

            // Configure dependency injection
            _host = Host.CreateDefaultBuilder()
                .ConfigureServices(
                    (context, services) =>
                    {
                        // Configuration
                        services.AddSingleton<ConfigurationService>();

                        // Core services
                        services.AddSingleton<DocumentService>();
                        services.AddSingleton<OllamaService>();
                        services.AddSingleton<ChatService>();
                        services.AddSingleton<UserPromptService>();
                        services.AddSingleton<AudioService>();
                        services.AddSingleton<WhisperService>();

                        // DispatcherQueue factory
                        services.AddSingleton<Func<DispatcherQueue>>(provider =>
                            () =>
                            {
                                return DispatcherQueue.GetForCurrentThread();
                            }
                        );

                        // ViewModels
                        services.AddSingleton<MainViewModel>();
                        services.AddSingleton<SettingsViewModel>();
                        services.AddSingleton<HelpViewModel>();
                    }
                )
                .Build();
        }

        private void App_UnhandledException(
            object sender,
            Microsoft.UI.Xaml.UnhandledExceptionEventArgs e
        )
        {
            try
            {
                var detailedInfo =
                    $"Unhandled Exception:\n"
                    + $"Message: {e.Exception.Message}\n"
                    + $"Stack Trace: {e.Exception.StackTrace}\n"
                    + $"Inner Exception: {e.Exception.InnerException?.ToString() ?? "None"}\n"
                    + $"HResult: {e.Exception.HResult}\n"
                    + $"Source: {e.Exception.Source}\n"
                    + $"Type: {e.Exception.GetType().FullName}\n"
                    + $"Handled: {e.Handled}";

                File.WriteAllText("unhandled_exception.txt", detailedInfo);
            }
            catch { }
        }

        /// <summary>
        /// Invoked when the application is launched.
        /// </summary>
        /// <param name="args">Details about the launch request and process.</param>
        protected override void OnLaunched(Microsoft.UI.Xaml.LaunchActivatedEventArgs args)
        {
            try
            {
                var ollamaService = _host.Services.GetRequiredService<OllamaService>();
                _ = ollamaService.StartAsync();

                _window = new MainWindow(_host.Services, ollamaService);

                // Dispose of Ollama when app is closed
                _window.Closed += (s, e) =>
                {
                    ollamaService.Dispose();
                };

                _window.Activate();
            }
            catch (Exception ex)
            {
                File.WriteAllText(
                    "launch_exception.txt",
                    $"Exception during OnLaunched:\n"
                        + $"Message: {ex.Message}\n"
                        + $"Stack Trace: {ex.StackTrace}\n"
                        + $"Inner Exception: {ex.InnerException?.ToString() ?? "None"}\n"
                        + $"HResult: {ex.HResult}\n"
                        + $"Source: {ex.Source}"
                );
                throw;
            }
        }

        // Expose service provider for other components
        public static IServiceProvider Services => ((App)Current)._host.Services;
    }
}
