# SmolPC 2.0 - Architecture Documentation

## Overview

SmolPC 2.0 is a Windows native desktop application that brings conversational AI assistance to LibreOffice applications. Built as a university project by the UCL team in partnership with IBM, Intel, Qualcomm, and Microsoft, it demonstrates local-first AI capabilities for educational users.

**Key Features:**
- AI-powered LibreOffice Writer and Impress control via natural language
- Local LLM inference using embedded Ollama (no cloud dependencies)
- Voice input via Whisper speech-to-text
- Document context awareness
- Educational focus with content filtering for appropriate reading levels

## Project Structure

```
SmolPC-2.0/
├── adapters/           # Backend MCP servers for application integration
│   └── libreoffice/   # LibreOffice Writer & Impress adapter
├── ui/                # User interface implementations
│   └── desktop-wpf/   # Windows WPF native application
├── docs/              # Documentation and setup guides
└── .github/           # GitHub workflows for CI/CD
```

**Statistics:**
- 20 C# source files
- 13 Python files
- 6 XAML UI definition files
- 3,462 lines in helper.py (UNO API bridge)
- 1,605 lines in libre.py (MCP server)

## Technology Stack

### Frontend (C#/.NET)
- **.NET 8.0** targeting Windows (net8.0-windows10.0.19041.0)
- **Windows App SDK 1.7** for modern Windows UI
- **WinUI 3** for native Windows controls
- **MVVM Pattern** using CommunityToolkit.Mvvm (8.4.0)
- **Dependency Injection** via Microsoft.Extensions.DependencyInjection (9.0.7)

### AI & ML Components
- **OllamaSharp (5.3.6)** - Ollama API client for local LLM interaction
- **OllamaSharp.ModelContextProtocol (5.3.6)** - MCP tool integration
- **Whisper.net (1.8.1)** - Local speech-to-text transcription
- **Multiple Whisper runtimes:** CUDA, OpenVINO, Vulkan, NoAvx support

### Audio Processing
- **NAudio (2.2.1)** - Audio recording and processing

### Backend (Python)
- **Python 3.12+** required
- **MCP (Model Context Protocol) 1.6.0+** - Tool orchestration
- **httpx (0.28.1+)** - HTTP client for async operations
- **Pillow (11.3.0+)** - Image processing
- **LibreOffice UNO API** - Direct LibreOffice integration

### Additional Libraries
- **Newtonsoft.Json (13.0.3)** - JSON serialization
- **CommunityToolkit.WinUI.Converters (8.2.250402)** - UI data binding converters

## Architecture

### High-Level Data Flow

```
User Interface (WPF)
      ↓
MainViewModel → ChatService
      ↓
UserPromptService → OllamaService (ExternalChat)
      ↓
ToolService → Determines needed tools via InternalChat
      ↓
OllamaSharp.MCP → Calls MCP tools
      ↓
libre.py (MCP Server) → Queue-based request processing
      ↓
Socket Communication (localhost:8765)
      ↓
helper.py (UNO Bridge) → Executes via UNO API
      ↓
LibreOffice (Headless, port 2002)
```

### Communication Layers

1. **UI Layer (C#/WPF)**
   - MVVM pattern with CommunityToolkit
   - Dependency injection for service composition
   - Event-driven communication between ViewModels

2. **Service Layer (C#)**
   - Business logic and state management
   - AI orchestration via OllamaSharp
   - Async/await for non-blocking operations

3. **MCP Protocol Layer**
   - JSON-RPC style communication
   - Tool discovery and invocation
   - Defined in server_config.json

4. **Socket Layer (Python)**
   - TCP socket on localhost:8765
   - JSON request/response format
   - Thread-safe queue processing

5. **UNO API Layer (Python)**
   - Direct LibreOffice automation
   - Connection via UNO bridge on port 2002
   - Document manipulation via COM-like interface

### Key Interaction Patterns

- **AI Decision Flow:** User prompt → External AI → Intent AI determines tools → Tool execution → Response formatting
- **Document Context:** DocumentService tracks active documents, provides context to AI via system prompt
- **Error Handling:** Multiple retry mechanisms, detailed logging, user-friendly error messages
- **Voice Input:** AudioService → WhisperService → UserPromptService → ChatService

## Key Components

### C# Application Layer (`/ui/desktop-wpf`)

#### Entry Point & Initialization

**App.xaml.cs** (`/ui/desktop-wpf/App.xaml.cs`)
- Application entry point
- Configures dependency injection container
- Registers all services and ViewModels
- Handles unhandled exceptions with detailed logging
- Starts OllamaService on launch

**MainWindow.xaml.cs** (`/ui/desktop-wpf/MainWindow.xaml.cs`)
- Main application window and navigation controller
- Manages page navigation (Main, Settings, Help)
- Handles keyboard shortcuts (spacebar for microphone)
- Coordinates ViewModel communication

#### Services (`/ui/desktop-wpf/Services/`)

**OllamaService.cs** - AI orchestration hub
- Manages embedded Ollama instance
- Initializes AI chat interfaces (ExternalChat for user, InternalChat for tool selection)
- Handles model downloading and status monitoring
- Loads system and intent prompts
- Manages ToolService integration

**ChatService.cs** - Conversation management
- Manages chat message collection
- Sends user prompts to AI
- Handles AI response streaming
- Manages cancellation tokens
- Coordinates with DocumentService for context

**DocumentService.cs** - Document tracking
- Tracks documents in use during chat session
- Lists available documents from Documents folder
- Manages presentation templates
- Distinguishes Writer (.odt, .docx) vs Impress (.odp, .pptx) documents

**ToolService.cs** - MCP tool coordination
- Discovers tools from MCP servers via server_config.json
- Determines which tools are needed for a given prompt
- Manages tool lifecycle and status
- Handles connection retries and port management

**WhisperService.cs** - Speech-to-text
- Downloads Whisper model (ggml-base.bin) if not present
- Transcribes audio files with automatic language detection
- Manages transcription state

**AudioService.cs** - Audio recording
- Records user audio via microphone
- Saves recordings as WAV files
- Integrates with WhisperService for transcription

**UserPromptService.cs** - User input management
- Manages prompt text state
- Controls send button visibility
- Handles text box focus

**ConfigurationService.cs** - Application configuration
- Loads settings from settings.json and server_config.json
- Manages paths (Documents, Ollama, models, prompts)
- Provides default fallbacks
- Handles Debug vs Release path differences

#### ViewModels (`/ui/desktop-wpf/ViewModels/`)

**MainViewModel.cs** - Main page orchestrator
- Aggregates state from all services
- Manages UI visibility (loading, welcome screen, recording)
- Handles user commands (send message, toggle microphone, new chat)
- Coordinates navigation events

**SettingsViewModel.cs** - Settings management
- Manages Documents folder path
- Handles AI model selection
- Manages presentation template paths
- Saves configuration changes

**HelpViewModel.cs** - Help page controller
- Manages help content display

#### Models (`/ui/desktop-wpf/Models/`)

**ChatMessage.cs** - Chat message data structure with MessageType enum (User, AI, Error)

**DocTemplateSelector.cs** - XAML template selector for document display

**MessageTemplateSelector.cs** - XAML template selector for chat messages

#### Views (`/ui/desktop-wpf/Views/`)

**MainPage.xaml** - Chat interface

**SettingsPage.xaml** - Configuration UI

**HelpPage.xaml** - User help and documentation

**HelpContent.xaml** - Detailed help content

#### Controls (`/ui/desktop-wpf/Controls/`)

**HandCursorStackPanel.cs** - Custom control for cursor behavior

### Python Backend Layer (`/adapters/libreoffice`)

**main.py** (`/adapters/libreoffice/main.py`)
- Entry point for MCP server
- Starts LibreOffice in headless mode (port 2002)
- Starts helper.py socket server (port 8765)
- Launches libre.py MCP server
- Manages process lifecycle and cleanup
- Cross-platform path detection (Windows/Linux)

**libre.py** (`/adapters/libreoffice/libre.py`)
- MCP server implementation (1,605 lines)
- Exposes LibreOffice tools via Model Context Protocol
- Uses queue-based request processing for thread safety
- Communicates with helper.py via socket (localhost:8765)
- Implements 36+ tools for Writer and Impress
- Handles JSON request/response serialization

**helper.py** (`/adapters/libreoffice/helper.py`)
- UNO API bridge (3,462 lines)
- Socket server listening on port 8765
- Direct LibreOffice UNO API integration
- Implements all document manipulation functions:
  - Document creation, reading, copying
  - Text manipulation (add, format, search/replace, delete)
  - Paragraph and heading management
  - Table creation and formatting
  - Image insertion
  - Page breaks
  - Presentation slide management
  - Template application

**helper_utils.py** (`/adapters/libreoffice/helper_utils.py`)
- Utility functions for UNO operations
- Path normalization and validation
- UNO desktop connection management
- Property value creation helpers
- Custom HelperError exception class

**helper_test_functions.py** (`/adapters/libreoffice/helper_test_functions.py`)
- Test and verification functions
- Text formatting inspection
- Table information extraction
- Image detection
- Page break verification
- Template information retrieval

## Application Startup Sequence

1. **App.xaml.cs Constructor**
   - Initialize XAML components
   - Create Host.CreateDefaultBuilder()
   - Register services in DI container
   - Build host

2. **OnLaunched()**
   - Retrieve OllamaService from DI container
   - Start Ollama asynchronously (OllamaService.StartAsync())
   - Create MainWindow with services
   - Register window.Closed event to dispose Ollama
   - Activate window

3. **OllamaService Initialization**
   - Load configuration (settings.json)
   - Create OllamaApiClient with HttpClient (5-minute timeout)
   - Load SystemPrompt.txt and append document context
   - Create ExternalChat (user-facing AI)
   - Load IntentPrompt.txt
   - Create InternalChat (tool selection AI)
   - Initialize ToolService

4. **ToolService.FindTools()** (Background Task)
   - Connect to MCP servers via server_config.json
   - Retry up to 3 times with port cleanup
   - Load available tools from MCP servers
   - Set ToolsLoaded = true

5. **MCP Server Startup** (main.exe)
   ```
   main.py execution:
   - Check if LibreOffice headless is running (port 2002)
   - Start LibreOffice: soffice.exe --headless --accept=socket,port=2002
   - Check if helper is running (port 8765)
   - Start helper: python helper.py
   - Start MCP server: python libre.py
   ```

6. **Helper Script** (helper.py)
   - Import UNO libraries
   - Create socket server on port 8765
   - Listen for JSON commands
   - Process commands using UNO API
   - Return JSON responses

7. **MCP Server** (libre.py)
   - Start queue worker thread
   - Register MCP tools (36 LibreOffice functions)
   - Listen for tool invocation requests
   - Queue commands to helper via socket
   - Return responses via MCP protocol

8. **UI Display**
   - MainWindow.InitializeComponent()
   - Navigate to MainPage
   - Display loading screen until OllamaReady and ToolsLoaded
   - Show welcome screen when ChatMessages.Count == 0

## User Interaction Flow

### Text Input Flow

```
User types → PromptTextBox → UserPromptService.PromptText
→ Send button click → MainViewModel.SendMessageCommand
→ ChatService.SendMessageAsync()
→ OllamaService.ExternalChat.SendAsync()
→ AI determines tools via ToolService
→ Tools executed via MCP → libre.py → helper.py → LibreOffice
→ Response streamed back to ChatService
→ UI updates via ObservableCollection binding
```

### Voice Input Flow

```
User presses spacebar → MainViewModel.ToggleMicrophoneCommand
→ AudioService.StartRecording() → NAudio captures microphone
→ User releases spacebar → AudioService.StopRecording()
→ Save to temp WAV file
→ WhisperService.Transcribe(wavPath)
→ Whisper model processes audio
→ Transcribed text → UserPromptService.PromptText
→ Continue as text input flow
```

### Document Context Flow

```
On tool execution (e.g., create_document):
- libre.py calls helper.py function
- helper.py creates document via UNO
- Returns document path
- ChatService receives tool call notification
- DocumentService.AddDocument() updates DocumentsInUse
- UI displays clickable document links
```

## Configuration Files

### settings.json (`/ui/desktop-wpf/settings.json`)
User-configurable application settings:
- `documentsFolderPath`: Location for document operations
- `addedPresentationTemplatesPaths`: Custom presentation template paths
- `ollamaUri`: Ollama server URI (default: http://localhost:11434)
- `selectedModel`: AI model name (default: qwen3:8b)

### server_config.json (`/ui/desktop-wpf/server_config.json`)
MCP server configuration:
- Defines MCP server commands and arguments
- Dynamically updated by ConfigurationService on launch

### SystemPrompt.txt (`/ui/desktop-wpf/SystemPrompt.txt`)
AI system instructions for user-facing chat:
- Instructs AI to work with LibreOffice
- Provides guidelines for parameter handling
- Tells AI to be proactive (don't ask for confirmation)
- Dynamically appended with Documents folder path and available documents

### IntentPrompt.txt (`/ui/desktop-wpf/IntentPrompt.txt`)
AI instructions for tool selection:
- Lists all 36 available LibreOffice tools
- Organized by category (General, Writer, Impress)
- Instructs AI to select relevant tools for each user request

### pyproject.toml (`/adapters/libreoffice/pyproject.toml`)
Python project metadata and dependencies:
```toml
[project]
name = "libre"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.28.1", "mcp[cli]>=1.6.0", "pillow>=11.3.0"]
```

### LibreOfficeAI.csproj (`/ui/desktop-wpf/LibreOfficeAI.csproj`)
.NET project file defining:
- Target framework (net8.0-windows)
- NuGet package dependencies
- Build configurations
- Asset and content file inclusions
- Publish settings

## Build and Deployment

### Development Build (Visual Studio)

**Prerequisites:**
- Visual Studio 2022 with .NET desktop development workload
- Python development workload
- MSVC C++ x64/x86 build tools

**Required Setup:**
1. Create `/ui/desktop-wpf/Ollama/` folder
2. Download and extract ollama-windows-amd64.zip
3. Create `/ui/desktop-wpf/WhisperModels/` folder
4. Download ggml-base.bin (~150MB)

**Build Process:**
1. Open LibreOfficeAI.sln in Visual Studio
2. Restore NuGet packages
3. Build solution (Debug or Release)

### Publishing (Distribution)

**Publish via Visual Studio:**
- Right-click project → Publish
- Target: Folder
- Configuration: Release
- Output: Self-contained with dependencies

**Embedded Components:**
- Ollama binaries (ollama.exe + dependencies)
- Whisper model (ggml-base.bin)
- Python MCP server executables (main.exe, libre.exe compiled with Nuitka)
- Python helper scripts (helper.py, helper_utils.py, helper_test_functions.py)
- Configuration files (settings.json, server_config.json)
- Prompt files (SystemPrompt.txt, IntentPrompt.txt)

**Nuitka Compilation:**
- main.py → main.exe
- libre.py → libre.exe
- Note: May trigger false positives in antivirus software

**Distribution:**
- Single folder with LibreOfficeAI.exe as entry point
- No installer required (xcopy deployment)
- Users need LibreOffice installed separately

### Cross-Platform Deployment (Experimental)

Located on `cross-platform` branch:
- Python-only backend (no WPF)
- Integration with Claude Desktop
- Future Tauri UI planned

## Important Directories

### /adapters/libreoffice/
Python MCP server for LibreOffice integration
- Core Python scripts (main.py, libre.py, helper.py)
- Utility modules (helper_utils.py, helper_test_functions.py)
- Python dependencies (pyproject.toml, uv.lock)

### /ui/desktop-wpf/
WPF application source code
- Application files (App.xaml.cs, MainWindow.xaml.cs)
- Services/ - 8 service classes
- ViewModels/ - 3 ViewModel classes
- Views/ - 4 XAML pages
- Models/ - 3 model classes
- Controls/ - Custom controls
- Assets/ - Images (UCL, Intel, LibreOffice logos)
- MCPServer/ - Embedded Python files and executables

### /docs/
Setup and configuration documentation
- SETUP_MAC.md - macOS installation guide
- SETUP_WINDOWS_MCP.md - Windows MCP setup
- WPF_UI_SETUP.md - WPF application build guide

### /.github/workflows/
CI/CD automation
- claude.yml - Claude Code assistant integration
- claude-code-review.yml - Automated code review workflow

## Future Expansion

**Planned Adapters:**
- `/adapters/blender/` - 3D modeling control
- `/adapters/gimp/` - Image editing control

**Planned Directories:**
- `/deployment/` - Packaging and installers
- `/core/` - Shared routing and AI engine code
- `/educational/` - Content filtering and reading level adjustment

## Shutdown Sequence

```
User closes window → MainWindow.Closed event
→ OllamaService.Dispose()
→ Kill Ollama process
→ MCP server receives termination signal
→ main.py cleanup_processes()
→ Terminate helper.py
→ Terminate LibreOffice headless instance
→ Application exits
```

## Summary

SmolPC 2.0 demonstrates:
- Modern .NET development with WPF/WinUI 3, MVVM, and dependency injection
- Local-first AI via embedded Ollama, eliminating cloud dependencies
- Advanced integration patterns using Model Context Protocol for tool orchestration
- Cross-language architecture (C# frontend, Python backend) bridged via sockets and MCP
- Accessibility features including voice transcription via Whisper
- Educational focus with content designed for learning and accessibility
- Enterprise partnership with industry leaders (Intel, Microsoft, Qualcomm, IBM)

The codebase is well-structured for future expansion with planned support for additional applications and educational features.
