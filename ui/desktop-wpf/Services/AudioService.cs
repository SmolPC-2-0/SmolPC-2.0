using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;
using Windows.Media.Capture;
using Windows.Storage;

namespace LibreOfficeAI.Services
{
    /// <summary>
    /// Provides functionality for audio recording, transcription, and integration with user prompts.
    /// </summary>
    /// <remarks>The <see cref="AudioService"/> class manages audio recording using the device's microphone,
    /// transcribes the recorded audio, and updates the user prompt with the transcribed text. It supports toggling
    /// between recording states and raises an event when the recording state changes.</remarks>
    /// <param name="userPromptService"></param>
    /// <param name="whisperService"></param>
    public class AudioService(UserPromptService userPromptService, WhisperService whisperService)
    {
        private readonly UserPromptService _userPromptService = userPromptService;
        private readonly WhisperService _whisperService = whisperService;
        private MediaCapture? _mediaCapture;
        public bool IsRecording { get; private set; } = false;

        public event Action? RecordingStateChanged;

        private async Task InitialiseMediaCapture()
        {
            Debug.WriteLine("Initializing MediaCapture...");
            _mediaCapture = new MediaCapture();

            // Explicitly specify audio capture settings
            var settings = new Windows.Media.Capture.MediaCaptureInitializationSettings
            {
                StreamingCaptureMode = Windows.Media.Capture.StreamingCaptureMode.Audio,
            };

            await _mediaCapture.InitializeAsync(settings);
            Debug.WriteLine("MediaCapture initialized successfully");
        }

        private async Task StartRecording()
        {
            try
            {
                Debug.WriteLine("Starting recording...");
                IsRecording = true;
                RecordingStateChanged?.Invoke();

                // Use temp folder to store audio file
                var tempPath = Path.GetTempPath();
                Debug.WriteLine($"Temp path: {tempPath}");

                var tempFolder = await StorageFolder.GetFolderFromPathAsync(tempPath);
                Debug.WriteLine("Got temp folder successfully");

                var audioFile = await tempFolder.CreateFileAsync(
                    "recordedAudio.wav",
                    CreationCollisionOption.ReplaceExisting
                );
                Debug.WriteLine($"Created audio file: {audioFile.Path}");

                await _mediaCapture.StartRecordToStorageFileAsync(
                    Windows.Media.MediaProperties.MediaEncodingProfile.CreateWav(
                        Windows.Media.MediaProperties.AudioEncodingQuality.Auto
                    ),
                    audioFile
                );

                Debug.WriteLine("Recording started successfully");
            }
            catch (UnauthorizedAccessException ex)
            {
                Debug.WriteLine($"Microphone access denied: {ex.Message}");
                // Revert state on error
                IsRecording = false;
                RecordingStateChanged?.Invoke();
                throw;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Failed to start recording: {ex.Message}");
                // Revert state on error
                IsRecording = false;
                RecordingStateChanged?.Invoke();
                throw;
            }
        }

        private async Task StopRecording()
        {
            try
            {
                Debug.WriteLine("Stopping recording...");
                IsRecording = false;

                await _mediaCapture.StopRecordAsync();
                Debug.WriteLine("Recording stopped successfully");

                // Log the final file location
                var tempPath = Path.GetTempPath();
                var audioFilePath = Path.Combine(tempPath, "recordedAudio.wav");
                if (File.Exists(audioFilePath))
                {
                    var fileInfo = new FileInfo(audioFilePath);
                    Debug.WriteLine($"Audio file created successfully at: {audioFilePath}");
                    Debug.WriteLine($"File size: {fileInfo.Length} bytes");

                    var convertedPath = Path.Combine(tempPath, "recordedAudio_16kHz.wav");
                    AudioService.ConvertWav(audioFilePath, convertedPath);

                    string? transcribedMessage = await _whisperService.Transcribe(convertedPath);

                    // Delay the event so that UI is consistent
                    RecordingStateChanged?.Invoke();

                    if (transcribedMessage != null)
                    {
                        string trimmedMessage = transcribedMessage.TrimStart();
                        if (trimmedMessage != "[BLANK_AUDIO]")
                        {
                            _userPromptService.PromptText = trimmedMessage;
                            _userPromptService.RequestFocus();
                        }
                    }
                }
                else
                {
                    Debug.WriteLine($"Audio file NOT found at expected location: {audioFilePath}");
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error stopping recording: {ex.Message}");
                // Ensure state is still set to false even if stop fails
                IsRecording = false;
                RecordingStateChanged?.Invoke();
                throw;
            }
        }

        public async Task ToggleRecordingAsync()
        {
            try
            {
                if (_mediaCapture == null)
                {
                    await InitialiseMediaCapture();
                }

                if (!IsRecording)
                {
                    await StartRecording();
                }
                else
                {
                    await StopRecording();
                }
            }
            catch (ObjectDisposedException ex)
            {
                Debug.WriteLine($"MediaCapture was disposed: {ex.Message}");
                _mediaCapture = null; // Reset so it can be recreated
                IsRecording = false;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Audio recording error: {ex}");
                Debug.WriteLine($"Exception type: {ex.GetType().Name}");
                Debug.WriteLine($"Stack trace: {ex.StackTrace}");

                // Reset state on error
                IsRecording = false;
                if (_mediaCapture != null)
                {
                    try
                    {
                        _mediaCapture.Dispose();
                    }
                    catch { }
                    _mediaCapture = null;
                }
            }
        }

        private static void ConvertWav(string inputPath, string outputPath)
        {
            using var reader = new AudioFileReader(inputPath);
            var resampler = new WdlResamplingSampleProvider(reader, 16000);
            WaveFileWriter.CreateWaveFile16(outputPath, resampler);
        }
    }
}
