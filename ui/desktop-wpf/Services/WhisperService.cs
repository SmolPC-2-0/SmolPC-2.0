using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Whisper.net;
using Whisper.net.Ggml;
using Whisper.net.Logger;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides functionality for transcribing audio files into text using the Whisper model.
    /// </summary>
    /// <remarks>The <see cref="WhisperService"/> class manages the lifecycle of the Whisper model, including
    /// downloading the model if it is not already present, and processing audio files for transcription. It supports
    /// automatic language detection and raises an event when the transcription state changes.</remarks>
    public class WhisperService : IDisposable
    {
        private readonly WhisperFactory whisperFactory;
        private readonly WhisperProcessor processor;
        private readonly IDisposable whisperLogger;
        private readonly string modelsDirectory;
        private readonly string modelFilePath;

        public bool IsTranscribing { get; private set; } = false;
        public event Action? IsTranscribingChanged;

        public WhisperService()
        {
            // Create a dedicated directory for Whisper models
#if DEBUG
            modelsDirectory = Path.Combine(
                Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location)
                    ?? ".",
                "WhisperModels"
            );
#else
            modelsDirectory = Path.Combine(AppContext.BaseDirectory, "WhisperModels");
#endif
            // Ensure the models directory exists
            Directory.CreateDirectory(modelsDirectory);

            var ggmlType = GgmlType.Base;
            var modelFileName = "ggml-base.bin";
            modelFilePath = Path.Combine(modelsDirectory, modelFileName);

            if (!File.Exists(modelFilePath))
            {
                Debug.WriteLine($"Whisper model not found at {modelFilePath}, downloading...");
                DownloadModel(modelFilePath, ggmlType).GetAwaiter().GetResult();
            }
            else
            {
                Debug.WriteLine($"Using existing Whisper model at {modelFilePath}");
            }

            whisperLogger = LogProvider.AddConsoleLogging(WhisperLogLevel.Debug);
            whisperFactory = WhisperFactory.FromPath(modelFilePath);
            processor = whisperFactory.CreateBuilder().WithLanguage("auto").Build();
        }

        public async Task<string?> Transcribe(string wavFilePath)
        {
            try
            {
                IsTranscribing = true;
                IsTranscribingChanged?.Invoke();

                using var fileStream = File.OpenRead(wavFilePath);

                var userMessage = new StringBuilder();

                // This section processes the audio file and prints the results (start time, end time and text) to the console.
                await foreach (var result in processor.ProcessAsync(fileStream))
                {
                    Debug.WriteLine($"{result.Start}->{result.End}: {result.Text}");
                    userMessage.Append(result.Text);
                }

                IsTranscribing = false;
                IsTranscribingChanged?.Invoke();

                return userMessage.ToString();
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex.ToString());
                IsTranscribing = false;
                IsTranscribingChanged?.Invoke();
                return null;
            }
        }

        private static async Task DownloadModel(string filePath, GgmlType ggmlType)
        {
            Debug.WriteLine($"Downloading Whisper model to {filePath}");
            try
            {
                using var modelStream = await WhisperGgmlDownloader.Default.GetGgmlModelAsync(
                    ggmlType
                );
                using var fileWriter = File.OpenWrite(filePath);
                await modelStream.CopyToAsync(fileWriter);
                Debug.WriteLine("Whisper model download completed successfully.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error downloading Whisper model: {ex.Message}");
                throw;
            }
        }

        public void Dispose()
        {
            processor?.Dispose();
            whisperFactory?.Dispose();
            whisperLogger?.Dispose();
        }
    }
}
