# SmolPC 2.0 - Windows Setup Guide

Complete setup guide for running SmolPC 2.0 on Windows 10/11.

## Overview

SmolPC 2.0 is an AI-powered assistant that lets you control LibreOffice (Writer, Impress) using natural language and voice commands. Everything runs locally on your computer - no internet required after setup.

**What you'll be able to do:**
- "Create a new document about solar systems"
- "Add a heading that says 'My Science Project'"
- "Insert a table with 5 rows and 3 columns"
- "Make the heading bold and blue"
- "Create a presentation with 5 slides about climate change"

## Prerequisites

- Windows 10 or Windows 11 (64-bit)
- At least 8GB RAM recommended (4GB minimum)
- 15GB free disk space
- Administrator access for installations

## Installation Steps

### Step 1: Install Python

1. Go to https://www.python.org/downloads/
2. Download the latest Python 3.12.x installer
3. Run the installer
4. **⚠️ IMPORTANT:** Check the box **"Add python.exe to PATH"**
5. Click "Install Now"
6. Wait for installation to complete

**Verify installation:**
```powershell
python --version
```
You should see: `Python 3.12.x`

---

### Step 2: Install Git

1. Go to https://git-scm.com/download/win
2. Download the 64-bit installer
3. Run the installer
4. Click "Next" through all screens (defaults are fine)
5. Click "Install"

**Verify installation:**
```powershell
git --version
```
You should see: `git version 2.x.x`

**Note:** If git command is not found, close and reopen PowerShell.

---

### Step 3: Install LibreOffice

1. Go to https://www.libreoffice.org/download/download-libreoffice/
2. Click "Download" (green button)
3. Run the installer (`LibreOffice_x.x.x_Win_x86-64.msi`)
4. Click "Next" through installation (defaults are fine)
5. Click "Install"

**Verify installation:**
- Press Windows Key
- Type "LibreOffice Writer"
- Open it to confirm it works
- Close it for now

---

### Step 4: Install Ollama (AI Engine)

1. Go to https://ollama.com/download/windows
2. Click "Download for Windows"
3. Run `OllamaSetup.exe`
4. Follow installation prompts
5. Ollama will start automatically in the background

**Verify installation:**
```powershell
ollama --version
```
You should see: `ollama version is 0.x.x`

**Download AI models (this takes 5-10 minutes):**
```powershell
ollama pull phi3
ollama pull llama3.2
```

Wait for both to complete. Verify:
```powershell
ollama list
```

You should see both `phi3` and `llama3.2` listed.

---

### Step 5: Clone the SmolPC Repository

```powershell
cd Documents
git clone https://github.com/SmolPC-2-0/SmolPC-2.0.git
cd SmolPC-2.0
```

---

### Step 6: Install Python Dependencies

```powershell
cd adapters\libreoffice
python -m pip install mcp websockets pywin32
```

This installs the required Python packages for the MCP server.

---

### Step 7: Fix helper.py for Windows

The `helper.py` file needs a small modification to work with Windows.

**Option A - Automated Fix:**
```powershell
python -c "with open('helper.py', 'r') as f: content = f.read(); content = content.replace('length_header = len(response_bytes).to_bytes(4, byteorder=\"big\")\n                client_socket.send(length_header + response_bytes)', 'client_socket.send(response_bytes)'); open('helper.py', 'w').write(content)"
```

**Option B - Manual Fix:**
1. Open `helper.py` in a text editor
2. Go to line 3381-3382
3. Find these two lines:
   ```python
   length_header = len(response_bytes).to_bytes(4, byteorder="big")
   client_socket.send(length_header + response_bytes)
   ```
4. Replace them with just:
   ```python
   client_socket.send(response_bytes)
   ```
5. Save the file

---

### Step 8: Install Claude Desktop

1. Go to https://claude.ai/download
2. Download Claude for Windows
3. Install it
4. Open Claude Desktop once to initialize it
5. Close it

---

### Step 9: Configure Claude Desktop for MCP

Create the configuration file for Claude Desktop:

```powershell
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

When prompted to create a new file, click **"Yes"**.

Paste this configuration (update the path with your username):

```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe",
      "args": [
        "C:\\Users\\YOUR_USERNAME\\Documents\\SmolPC-2.0\\adapters\\libreoffice\\libre.py"
      ]
    }
  }
}
```

**⚠️ IMPORTANT:** Replace `YOUR_USERNAME` with your actual Windows username!

To find your username, run:
```powershell
echo $env:USERNAME
```

**Example:** If your username is `mathi`, the config should be:
```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "C:\\Users\\mathi\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe",
      "args": [
        "C:\\Users\\mathi\\Documents\\SmolPC-2.0\\adapters\\libreoffice\\libre.py"
      ]
    }
  }
}
```

Save (Ctrl+S) and close Notepad.

---

## Running SmolPC 2.0

You need to start 3 components in this order:

### 1. Start LibreOffice with Socket Connection

Open PowerShell window #1:
```powershell
cd "C:\Program Files\LibreOffice\program"
.\soffice.exe "--accept=socket,host=localhost,port=2002;urp;" --writer --norestore
```

LibreOffice Writer will open. **Leave it open and leave this PowerShell window running.**

---

### 2. Start the Helper Script

Open PowerShell window #2:
```powershell
cd "C:\Program Files\LibreOffice\program"
.\python.exe C:\Users\YOUR_USERNAME\Documents\SmolPC-2.0\adapters\libreoffice\helper.py
```

Replace `YOUR_USERNAME` with your actual username.

You should see:
```
Importing UNO...
UNO imported successfully!
Starting LibreOffice Helper Script...
LibreOffice helper listening on port 8765
Waiting for connection...
```

**Leave this PowerShell window running.**

---

### 3. Start Claude Desktop

Open Claude Desktop from the Start menu.

**Verify MCP connection:**
In Claude Desktop, look for "Local MCP servers" in the interface. You should see:
```
libreoffice
running
```

---

## Testing SmolPC

In Claude Desktop, try these commands:

### Basic Document Creation
```
Create a new document at C:\Users\YOUR_USERNAME\Documents\test.odt with a heading that says "Hello SmolPC"
```

### Add Content
```
Add a paragraph about artificial intelligence in education
```

### Formatting
```
Make the heading bold and blue with font size 24
```

### Tables
```
Insert a table with 4 rows and 3 columns
```

### Presentations
```
Create a new presentation at C:\Users\YOUR_USERNAME\Documents\my_presentation.odp with a title slide that says "My Project"
```

Check LibreOffice Writer/Impress to see the changes happen in real-time!

---

## Troubleshooting

### "python is not recognized"
- Close PowerShell and open a new one
- Verify Python is installed: `python --version`
- If still not working, restart your computer

### "git is not recognized"
- Close PowerShell and open a new one
- If still not working, restart your computer

### "Cannot connect to LibreOffice" or helper errors
1. Make sure LibreOffice is running with the socket parameter
2. Make sure helper.py is running (you should see "Waiting for connection...")
3. Check that no firewall is blocking ports 2002 or 8765

### Claude Desktop shows blank screen
- Check the config file for typos
- Make sure all backslashes are doubled: `\\`
- Make sure paths match your actual username
- Fully quit Claude Desktop and restart

### "UNO Import Error"
- Make sure you're using LibreOffice's Python: `"C:\Program Files\LibreOffice\program\python.exe"`
- Do NOT use system Python for helper.py

### MCP server shows as "stopped" in Claude Desktop
- Check `%APPDATA%\Claude\logs\mcp-server-libreoffice.log` for errors
- Verify paths in `claude_desktop_config.json` are correct
- Make sure helper.py is running first

---

## Quick Start Script (Optional)

You can create a batch file to start everything at once.

Create `start_smolpc.bat` in `Documents\SmolPC-2.0\`:

```batch
@echo off
echo Starting LibreOffice...
start "LibreOffice" "C:\Program Files\LibreOffice\program\soffice.exe" "--accept=socket,host=localhost,port=2002;urp;" --writer --norestore

timeout /t 3

echo Starting Helper...
start "Helper" "C:\Program Files\LibreOffice\program\python.exe" "%USERPROFILE%\Documents\SmolPC-2.0\adapters\libreoffice\helper.py"

timeout /t 3

echo Starting Claude Desktop...
start "" "%LOCALAPPDATA%\Programs\Claude\Claude.exe"

echo SmolPC 2.0 is starting...
echo Check that all windows opened successfully.
pause
```

Then just double-click `start_smolpc.bat` to start everything!

---

## Available LibreOffice Tools

SmolPC provides these capabilities through Claude:

### Document Management
- `create_blank_document` - Create new Writer documents
- `open_text_document` - Open existing documents
- `save_document` - Save current document
- `close_document` - Close document

### Content Creation
- `add_heading` - Add formatted headings (levels 1-10)
- `add_paragraph` - Add text paragraphs
- `add_text` - Add plain text
- `insert_table` - Create tables
- `insert_image` - Add images

### Text Formatting
- `format_text` - Apply bold, italic, underline, colors, fonts
- `format_heading` - Format heading styles
- `search_and_replace` - Find and replace text

### Presentations
- `create_blank_presentation` - Create Impress presentations
- `add_slide` - Add new slides
- `edit_slide` - Modify slide content
- `delete_slide` - Remove slides
- `insert_slide_image` - Add images to slides
- `format_slide_content` - Format slide text

And many more! Ask Claude what it can do.

---

## System Requirements

### Minimum
- Windows 10 64-bit
- Intel Core i3 or equivalent
- 4GB RAM
- 15GB free disk space
- Integrated graphics

### Recommended
- Windows 11 64-bit
- Intel Core i5/i7 or AMD Ryzen 5/7
- 8GB+ RAM
- 20GB free disk space
- Dedicated GPU (for faster AI inference)

---

## Performance Notes

- **First AI response** takes 5-10 seconds (model loading)
- **Subsequent responses** are much faster (1-3 seconds)
- **GPU acceleration** works automatically if you have a compatible NVIDIA GPU
- **RAM usage:** ~2-3GB for Ollama + models when running

---

## Stopping SmolPC

To stop everything:

1. Close Claude Desktop
2. In the helper.py PowerShell window, press `Ctrl+C`
3. Close LibreOffice Writer
4. Ollama runs in the background - it's fine to leave it running

---

## Next Steps

- Read the main [README.md](../README.md) for project overview
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Try different commands and explore features
- Join the team on GitHub: https://github.com/SmolPC-2-0/SmolPC-2.0

---

## Credits

SmolPC 2.0 is based on the original [SmolPC](https://github.com/bthompson-dev/SmolPC) project by Ben Thompson.

**UCL Team:**
- Mathias Tidball (Team Lead)
- Stefanos Ioannidis
- Siddhant Murugkar
- Rabiyah Mon
- Aishah Mohammed

**Partners:**
- Microsoft
- Intel  
- Qualcomm

**Institution:** University College London (UCL)

---

## Getting Help

- **GitHub Issues:** https://github.com/SmolPC-2-0/SmolPC-2.0/issues
- **Documentation:** Check the `/docs` folder
- **Team:** Contact via GitHub

---

**Last Updated:** October 25, 2025  
**Tested On:** Windows 11 22H2, Windows 10 22H2  
**Version:** 1.0
