# SmolPC 2.0 - WPF UI Setup Guide (Windows)

Complete guide for building and running the native Windows WPF user interface for SmolPC 2.0.

## Prerequisites

Before starting, you must have completed the basic setup from **SETUP_WINDOWS.md**. This includes:
- ✅ Python installed
- ✅ Git installed
- ✅ LibreOffice installed
- ✅ Ollama installed with models (llama3.2, phi3)
- ✅ Repository cloned
- ✅ Backend Python dependencies installed
- ✅ helper.py fixed for Windows

If you haven't done the basic setup, **stop here** and complete `SETUP_WINDOWS.md` first.

---

## Additional Requirements for WPF UI

### 1. Visual Studio 2022 Community Edition

**Download and Install:**
1. Go to: https://visualstudio.microsoft.com/downloads/
2. Download **"Visual Studio Community 2022"** (the stable release, NOT Insiders)
3. Run the installer

**Required Workloads:**
During installation, select these workloads:
- ✅ **.NET desktop development**
- ✅ **Desktop development with C++**

**Installation time:** ~15-20 minutes

---

## Project Setup

### Step 1: Navigate to the WPF Project

```powershell
cd C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\ui\desktop-wpf
```

Replace `YOUR_USERNAME` with your actual Windows username.

---

### Step 2: Create Required Folders

The WPF app needs Ollama binaries and the Whisper model bundled with it.

#### A. Create Ollama Folder

```powershell
mkdir Ollama
cd Ollama
```

**Download Ollama binaries:**
1. Go to: https://github.com/ollama/ollama/releases
2. Download the latest `ollama-windows-amd64.zip`
3. Extract all contents into the `Ollama` folder

Or use PowerShell:
```powershell
Invoke-WebRequest -Uri "https://github.com/ollama/ollama/releases/download/v0.4.8/ollama-windows-amd64.zip" -OutFile "ollama-windows-amd64.zip"
Expand-Archive ollama-windows-amd64.zip -DestinationPath .
Remove-Item ollama-windows-amd64.zip
```

**Verify:** You should now have `ollama.exe` in the Ollama folder.

---

#### B. Create WhisperModels Folder

```powershell
cd ..
mkdir WhisperModels
cd WhisperModels
```

**Download Whisper model (~150MB):**
```powershell
Invoke-WebRequest -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin" -OutFile "ggml-base.bin"
```

This takes 2-5 minutes depending on your internet speed.

**Verify:** You should have `ggml-base.bin` in the WhisperModels folder.

---

### Step 3: Update Configuration Files

The project has hardcoded paths from the original developer that need updating.

#### A. Update settings.json

```powershell
cd C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\ui\desktop-wpf
notepad settings.json
```

Change the content to:
```json
{
  "documentsFolderPath": "C:\\Users\\YOUR_USERNAME\\Documents",
  "addedPresentationTemplatesPaths": [],
  "ollamaUri": "http://localhost:11434",
  "selectedModel": "llama3.2"
}
```

**Important:**
- Replace `YOUR_USERNAME` with your actual username
- Use `llama3.2` as the model (not `phi3` - it doesn't support tool calling)

---

#### B. Update server_config.json

```powershell
notepad server_config.json
```

Change to:
```json
{
  "mcpServers": {
    "libreoffice-server": {
      "command": "python",
      "args": [
        "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\adapters\\libreoffice\\libre.py"
      ]
    }
  }
}
```

Replace `YOUR_USERNAME` with your actual username.

---

### Step 4: Update ConfigurationService.cs

The code has hardcoded DEBUG paths that need updating.

**Open Visual Studio 2022:**
1. Launch Visual Studio 2022 (Run as Administrator - right-click → "Run as administrator")
2. Click "Open a project or solution"
3. Navigate to: `C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\ui\desktop-wpf\`
4. Open `LibreOfficeAI.sln`

**Edit ConfigurationService.cs:**
1. In Solution Explorer (right side), expand the **Services** folder
2. Double-click **ConfigurationService.cs**
3. Find the `#if DEBUG` section (around line 60)
4. Replace **ALL** the paths with yours:

```csharp
#if DEBUG
    // Use hardcoded paths in Debug Mode
    OllamaPath = "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\ui\\desktop-wpf\\Ollama\\ollama.exe";
    OllamaModelsDir = "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\ui\\desktop-wpf\\Ollama\\lib\\models\\";

    string settingsPath = "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\ui\\desktop-wpf\\settings.json";
    ServerConfigPath = "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\ui\\desktop-wpf\\server_config.json";
    string serverCommand = "python";

    SystemPromptPath = "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\ui\\desktop-wpf\\SystemPrompt.txt";
    IntentPromptPath = "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\ui\\desktop-wpf\\IntentPrompt.txt";
#else
```

Replace **ALL** instances of `YOUR_USERNAME` with your actual Windows username.

**Save:** Press `Ctrl+S`

---

### Step 5: Update Project File to Remove main.exe Dependency

The project tries to copy `main.exe` which we're not using (we're using the Python script directly).

1. In Solution Explorer, right-click on the project → **"Edit Project File"**
2. Press `Ctrl+F` to search
3. Search for: `main.exe`
4. Find the section that looks like:
   ```xml
   <Content Include="MCPServer\main.exe">
     <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
   </Content>
   ```
5. Comment it out:
   ```xml
   <!-- <Content Include="MCPServer\main.exe">
     <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
   </Content> -->
   ```
6. Also search for `libre.exe` and comment that out too if you find it
7. Save: `Ctrl+S`

---

### Step 6: Add Compatibility Tools to libre.py

The WPF app expects certain tool names that don't exist in the current libre.py. We need to add compatibility wrappers.

```powershell
cd C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\adapters\libreoffice
notepad libre.py
```

**Scroll to the very end of the file**, right before the `async def main():` function.

**Add these tools:**

```python
# ===================================================================
# Compatibility tools for WPF UI
# These wrapper tools provide compatibility with the WPF app's
# expected tool interface
# ===================================================================

@mcp.tool()
async def create_text(content: str, document_id: str = "0", author: str = "") -> str:
    """
    Create a text document with content (compatibility wrapper for WPF UI).
    
    Args:
        content: Initial content/heading for the document
        document_id: Document identifier (used for tracking)
        author: Document author
    """
    # Generate a filename from content or use a default
    import re
    safe_name = re.sub(r'[^\w\s-]', '', content)[:50]
    if not safe_name:
        safe_name = f"document_{document_id}"
    
    file_path = get_default_document_path(f"{safe_name}.odt")
    
    # Create blank document
    result = await create_blank_document(filename=file_path, title=content, author=author)
    
    # Add the content as a heading
    if "successfully" in result.lower():
        await add_heading(file_path=file_path, text=content, level=1)
    
    return result

@mcp.tool()
async def get_current_documents() -> str:
    """
    Get list of documents in the default Documents folder (compatibility wrapper for WPF UI).
    """
    docs_path = get_default_document_path("")
    docs_path = os.path.dirname(docs_path)  # Get the directory
    return await list_documents(directory=docs_path)
```

**Save and close.**

---

## Building the WPF Application

### Step 1: Clean and Build

In Visual Studio:

1. Go to **Build** menu → **Clean Solution**
2. Wait for it to finish
3. Go to **Build** menu → **Rebuild Solution**

**Build time:** 30-60 seconds

**Expected result:** 
```
========== Rebuild completed at [time] and took [seconds] ==========
```

If you see errors, check the Error List window and ensure all paths are correct.

---

### Step 2: Configure Run Settings

1. At the top of Visual Studio, find the dropdown next to the green Start button
2. It should say **"LibreOfficeAI (Unpackaged)"**
3. If it says "(Package)", click the dropdown and select **(Unpackaged)**

---

## Running the WPF Application

You need **three components** running simultaneously:

### Component 1: LibreOffice with Socket

**PowerShell Window #1:**
```powershell
cd "C:\Program Files\LibreOffice\program"
.\soffice.exe "--accept=socket,host=localhost,port=2002;urp;" --writer --norestore
```

LibreOffice Writer will open. **Keep it running.**

---

### Component 2: Helper Script

**PowerShell Window #2:**
```powershell
cd "C:\Program Files\LibreOffice\program"
.\python.exe C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\adapters\libreoffice\helper.py
```

You should see:
```
Importing UNO...
UNO imported successfully!
Starting LibreOffice Helper Script...
LibreOffice helper listening on port 8765
Waiting for connection...
```

**Keep this running.**

---

### Component 3: WPF Application

**In Visual Studio:**
- Press **F5** or click the green **▶ Start** button

The WPF application should launch and show a loading screen while it loads the AI model.

**First launch takes longer** (30-60 seconds) as Ollama loads the model into memory.

---

## Using the WPF Application

### Main Interface

The app has a chat-style interface at the bottom where you can type commands.

### Sending Commands

**Type your command and press Enter or click "Send Message".**

Examples:
- "Create a new document called my_report.odt with a heading that says Sales Report"
- "Add a paragraph about Q4 results to my_report.odt"
- "Add a table with 5 rows and 3 columns to my_report.odt"
- "Create a presentation called my_presentation.odp with a title slide that says Project Update"

### Voice Input

Click the **"Record Message"** button to use voice transcription via Whisper.

- Click once to start recording (red pulsating glow)
- Click again to stop and transcribe
- Or press **Spacebar** to start/stop (when textbox is not focused)

### Viewing Documents

When a document is created or edited, a clickable filename appears below the LibreOffice logo. Double-click to open the file.

---

## Performance Notes

### Expected Performance

- **First request:** 10-30 seconds (model loading)
- **Subsequent requests:** 5-15 seconds per command
- **RAM usage:** ~3-4GB for Ollama + model

### Performance Depends On:

1. **CPU:** 
   - Intel i5/i7 or AMD Ryzen 5/7 recommended
   - Faster CPU = faster AI responses

2. **RAM:**
   - 8GB minimum
   - 16GB+ recommended for smooth operation

3. **GPU:**
   - **Dedicated NVIDIA GPU:** Much faster with CUDA acceleration
   - **Integrated graphics (Intel/AMD):** Slower, CPU-only processing
   - The WPF app will use GPU automatically if available

### Improving Performance

**Use a smaller/faster model:**

```powershell
ollama pull qwen2.5:3b
```

Then update `settings.json` to use `qwen2.5:3b` instead of `llama3.2`. This is 2-3x faster but slightly lower quality.

**Keep Ollama loaded:**
First request is slowest. Subsequent requests are faster because the model stays in memory.

---

## Troubleshooting

### Build Errors

**Error: "Cannot find Ollama folder"**
- Ensure you created the `Ollama` folder and downloaded the binaries
- Check the folder structure: `ui\desktop-wpf\Ollama\ollama.exe`

**Error: "Cannot copy main.exe"**
- Make sure you commented out the `main.exe` reference in the project file
- Clean and rebuild the solution

**Error: "Missing Windows SDK components"**
- Install the Desktop development with C++ workload in Visual Studio Installer
- Modify your Visual Studio installation to add missing components

---

### Runtime Errors

**App crashes on startup with "ArgumentNullException"**
- Check that `settings.json` and `server_config.json` have correct paths
- Verify `ConfigurationService.cs` has your correct username in DEBUG paths
- Make sure Documents folder exists: `C:\Users\YOUR_USERNAME\Documents`

**"ModelDoesNotSupportToolsException"**
- You're using `phi3` instead of `llama3.2`
- Update `settings.json` to use `"selectedModel": "llama3.2"`

**"MCP server process exited unexpectedly" with virus warning**
- Windows Defender is blocking `main.exe`
- Since we're using Python scripts directly, this shouldn't happen
- If it does, verify `server_config.json` uses `"command": "python"` not `main.exe`

**App is very slow / hangs**
- First request loads the model (30-60 seconds)
- Check Task Manager - is Ollama using 100% CPU? (Normal for integrated graphics)
- Consider using a smaller model like `qwen2.5:3b`
- Ensure you have at least 8GB RAM available

**"Connection refused" errors**
- Verify helper.py is running and shows "Waiting for connection..."
- Check that LibreOffice is running with socket connection
- Make sure no firewall is blocking ports 2002 or 8765

**Commands work but document is empty**
- Connection broke between requests
- Restart all three components in order (LibreOffice → helper.py → WPF app)

---

## Testing the Application

### Basic Test Commands

Once the app is running, try these commands in order:

1. **Document Creation:**
   ```
   Create a new document called test.odt with a heading that says Hello World
   ```

2. **Add Content:**
   ```
   Add a paragraph about artificial intelligence to test.odt
   ```

3. **Tables:**
   ```
   Add a table with 3 rows and 4 columns to test.odt
   ```

4. **Presentations:**
   ```
   Create a presentation called slides.odp with a title slide that says My Project
   ```

5. **Add Slides:**
   ```
   Add a slide about project goals to slides.odp
   ```

### What to Check

- ✅ Commands execute without errors
- ✅ Documents/presentations are created in your Documents folder
- ✅ Content appears in LibreOffice when you open the files
- ✅ Helper.py shows connection and command activity
- ✅ App provides feedback about what it's doing

---

## Known Issues

### Working Features (✅)
- Document creation and management
- Content addition (headings, paragraphs, text)
- Tables
- Presentations (create, add/edit slides)
- Images
- Voice input (Whisper)
- Multiple commands in sequence

### Known Limitations (⚠️)
- **Formatting commands** (bold, colors, fonts) may not work reliably through the WPF app
  - Workaround: Use Claude Desktop for complex formatting
  - These work fine via Claude Desktop, just not through local Ollama
- **Performance** is slower than cloud-based AI (expected for local processing)
- **First request** is always slowest (model loading)

### Not Yet Implemented (❌)
- Spreadsheets (Calc) support
- Blender adapter
- GIMP adapter
- Educational content filtering
- Advanced voice commands

---

## Comparing WPF App vs Claude Desktop

| Feature | WPF App | Claude Desktop |
|---------|---------|----------------|
| **Speed** | Slower (local CPU) | Fast (cloud servers) |
| **Privacy** | 100% local, nothing leaves device | Sends data to Claude API |
| **Internet Required** | No (after setup) | Yes |
| **Cost** | Free | Free tier + paid plans |
| **UI** | Native Windows, fast | Electron-based, heavier |
| **Voice Input** | Whisper (included) | Not available |
| **Formatting** | Limited | Excellent |
| **Best For** | Demos, offline use, privacy | Development, testing, reliability |

**Recommendation:** Use both! WPF for demos and offline scenarios, Claude Desktop for development and testing.

---

## Next Steps After Setup

1. **Test thoroughly** - Try all the commands above
2. **Report issues** - Create GitHub issues for any problems
3. **Share feedback** - Let the team know what works/doesn't work
4. **Performance tuning** - Experiment with different models
5. **Contribute** - Help improve the compatibility layer

---

## File Locations Reference

**Project:** `C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\ui\desktop-wpf\`

**Key Files:**
- `settings.json` - App configuration
- `server_config.json` - MCP server configuration  
- `Services\ConfigurationService.cs` - DEBUG path configuration
- `Ollama\ollama.exe` - Local AI engine
- `WhisperModels\ggml-base.bin` - Voice transcription model

**Backend:**
- `C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\adapters\libreoffice\libre.py` - MCP tools
- `C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\adapters\libreoffice\helper.py` - LibreOffice bridge

**Output Documents:**
- Default location: `C:\Users\YOUR_USERNAME\Documents\`

---

## Getting Help

- **GitHub Issues:** https://github.com/SmolPC-2-0/SmolPC-2.0/issues
- **Main Setup Guide:** See `SETUP_WINDOWS.md` for backend setup
- **Architecture:** See `ARCHITECTURE.md` (when available)
- **Team:** Contact via GitHub

---

## Credits

Based on the original [SmolPC](https://github.com/bthompson-dev/SmolPC) and [LibreOfficeAI](https://github.com/bthompson-dev/LibreOfficeAI) projects by Ben Thompson.

**UCL SmolPC 2.0 Team:**
- Mathias Tidball (Team Lead)
- Stefanos Ioannidis
- Siddhant Murugkar
- Rabiyah Mon
- Aishah Mohammed

**Partners:** Microsoft, Intel, Qualcomm  
**Institution:** University College London

---

**Last Updated:** October 26, 2025  
**Tested On:** Windows 11 23H2  
**Document Version:** 1.0

---

## Appendix: Quick Start Checklist

Use this checklist when setting up on a new Windows machine:

- [ ] Completed basic setup from SETUP_WINDOWS.md
- [ ] Visual Studio 2022 installed with correct workloads
- [ ] Created `Ollama` folder with binaries
- [ ] Created `WhisperModels` folder with model file
- [ ] Updated `settings.json` with your username
- [ ] Updated `server_config.json` with your username
- [ ] Updated `ConfigurationService.cs` DEBUG paths
- [ ] Commented out `main.exe` reference in project file
- [ ] Added compatibility tools to `libre.py`
- [ ] Successfully built the project
- [ ] Started LibreOffice with socket
- [ ] Started helper.py
- [ ] Launched WPF app
- [ ] Tested basic document creation
- [ ] Tested tables
- [ ] Tested presentations

If all boxes are checked, you're ready to use SmolPC 2.0 with the WPF UI! 🎉
