# macOS Setup Guide - SmolPC 2.0

**Status:** Tested and working on macOS 14.4, M3 Pro  
**Last Updated:** October 20, 2025

## Overview

This guide explains how to set up the LibreOffice AI assistant on macOS. The main challenge on Mac is that LibreOffice's Python cannot be run standalone due to code signing restrictions. The solution is to run the helper as a LibreOffice macro.

## Prerequisites

- macOS 10.15 or later
- At least 8GB RAM (16GB recommended)
- 10GB free disk space
- Admin access to install software

## Installation Steps

### 1. Install Homebrew (if not already installed)

bash

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions to add Homebrew to your PATH.

### 2. Install Ollama

bash

```bash
brew install ollama
```

Start Ollama in a terminal window (keep this running):

bash

```bash
ollama serve
```

In a new terminal window, download the AI model:

bash

```bash
ollama pull phi3
```

This downloads approximately 2.3GB and may take several minutes.

Verify installation:

bash

```bash
ollama run phi3
```

Type a test message. If you get a response, Ollama is working. Type `/bye` to exit.

### 3. Install LibreOffice

bash

```bash
brew install --cask libreoffice
```

Or download manually from: [https://www.libreoffice.org/download/download-libreoffice/](https://www.libreoffice.org/download/download-libreoffice/)

### 4. Clone Repository and Install Python Dependencies

bash

```bash
# Clone the repository
git clone https://github.com/mts934/SmolPC-2.0.git
cd SmolPC-2.0

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install mcp httpx
```

### 5. Copy Helper Files to LibreOffice

bash

```bash
# Create LibreOffice scripts directory
mkdir -p ~/Library/Application\ Support/LibreOffice/4/user/Scripts/python

# Copy helper files
cp apps/libreoffice/helper*.py ~/Library/Application\ Support/LibreOffice/4/user/Scripts/python/

# Rename main helper file
mv ~/Library/Application\ Support/LibreOffice/4/user/Scripts/python/helper.py \
   ~/Library/Application\ Support/LibreOffice/4/user/Scripts/python/mcp_helper.py
```

### 6. Modify Helper Code for macOS Compatibility

Open the helper file in your preferred editor:

bash

```bash
open -a "Visual Studio Code" ~/Library/Application\ Support/LibreOffice/4/user/Scripts/python/mcp_helper.py
```

#### Modification 1: Fix `__file__` Issue

Find the following code (around line 8-12):

python

```python
script_dir = os.path.dirname(__file__)
```

Replace with:

python

```python
try:
    script_dir = os.path.dirname(__file__)
except NameError:
    # Running as LibreOffice macro - __file__ not available
    import uno
    ctx = uno.getComponentContext()
    script_dir = os.path.expanduser("~/Library/Application Support/LibreOffice/4/user/Scripts/python")
```

#### Modification 2: Remove Length Header from Response

Find the following code (around line 3377-3382):

python

```python
response_json = json.dumps(response)
response_bytes = response_json.encode("utf-8")
# Send response length first, then data
length_header = len(response_bytes).to_bytes(4, byteorder="big")
client_socket.send(length_header + response_bytes)
```

Replace with:

python

```python
response_json = json.dumps(response)
response_bytes = response_json.encode("utf-8")
# Send just the JSON (no length header for compatibility with libre.py)
client_socket.send(response_bytes)
```

#### Modification 3: Wrap Server Loop in Function

Find the section with the comment `# Main server loop` (around line 3292).

Before this line, add:

python

```python
def run_server():
    """Run the main server loop"""
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("localhost", 8765))
    server_socket.listen(1)
    
    print("LibreOffice helper listening on port 8765")
```

Then indent everything from `print("Starting command processing loop...")` to the end of the file by 4 spaces so it is inside the `run_server()` function.

Find the original server socket creation code (around line 3275-3280) that is now outside the function and delete those lines, as they have been moved inside `run_server()`.

#### Modification 4: Add Background Thread Entry Point

At the very end of the file, add:

python

```python
def start_helper(*args):
    """Entry point for LibreOffice macro - starts helper in background thread"""
    import threading
    
    # Start server in background daemon thread
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    return "MCP Helper started in background thread"

# Make it available to LibreOffice
g_exportedScripts = (start_helper,)
```

Save the file.

### 7. Install and Configure Claude Desktop

Download Claude Desktop from: [https://claude.ai/download](https://claude.ai/download)

Create the configuration file:

bash

```bash
mkdir -p ~/Library/Application\ Support/Claude
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add the following content (replace `YOUR_USERNAME` with your actual macOS username):

json

```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "/Users/YOUR_USERNAME/SmolPC-2.0/venv/bin/python3",
      "args": [
        "/Users/YOUR_USERNAME/SmolPC-2.0/apps/libreoffice/libre.py"
      ],
      "cwd": "/Users/YOUR_USERNAME/SmolPC-2.0/apps/libreoffice"
    }
  }
}
```

To find your username:

bash

```bash
echo $HOME
```

Save the file: Ctrl+O, Enter, Ctrl+X

## Running the Application

### Terminal 1: Start Ollama

bash

```bash
ollama serve
```

Keep this terminal window open.

### Terminal 2: Start LibreOffice with Socket

bash

````bash
/Applications/LibreOffice.app/Contents/MacOS/soffice --accept="socket,host=localhost,port=2002;urp;" &
```

Wait a few seconds for the LibreOffice GUI to open.

### In LibreOffice: Start the Helper Macro

1. Open LibreOffice (if not already open)
2. Go to: Tools → Macros → Organize Python Scripts
3. Expand "My Macros" → "mcp_helper"
4. Select `start_helper`
5. Click "Run"
6. The dialog should close immediately with the message "MCP Helper started in background thread"
7. Close the macro organizer dialog

### Open Claude Desktop

Launch Claude Desktop and try:
```
Create a new document called "test"
````

If successful, you should see a confirmation and the document will be created in your Documents folder.

## Verification

Check that all components are running:

bash

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Check helper is listening
lsof -i :8765
# Should show: soffice ... TCP localhost:8765 (LISTEN)

# Check LibreOffice UNO socket
lsof -i :2002
# Should show: soffice ... TCP localhost:2002 (LISTEN)
```

## Troubleshooting

### "Connection refused" Error in Claude Desktop

- Verify the helper macro is running: `lsof -i :8765`
- If not running, restart the helper macro in LibreOffice
- Ensure LibreOffice was started with the socket flag

### "Failed to connect to LibreOffice desktop" Error

- Verify LibreOffice is running with socket enabled: `lsof -i :2002`
- Restart LibreOffice with the correct command line arguments

### Helper Macro Runs Indefinitely

- The server loop was not properly wrapped in the `run_server()` function
- Check the indentation in mcp_helper.py
- Ensure the `start_helper()` function uses threading

### Claude Desktop Shows "Server disconnected"

- Verify the config file path is correct
- Ensure the virtual environment exists and has required packages installed
- Try restarting Claude Desktop

### Ollama Not Responding

bash

```bash
pkill ollama
ollama serve
```

## Startup Script (Optional)

Create a convenience script to start all components:

bash

```bash
nano ~/start-libreoffice-ai.sh
```

Add:

bash

```bash
#!/bin/bash
echo "Starting LibreOffice AI components..."

# Start LibreOffice with socket
/Applications/LibreOffice.app/Contents/MacOS/soffice --accept="socket,host=localhost,port=2002;urp;" &

sleep 3
echo "LibreOffice started"
echo ""
echo "Next steps:"
echo "1. Tools → Macros → Organize Python Scripts"
echo "2. Run 'start_helper'"
echo "3. Open Claude Desktop"
echo "4. Try: 'Create a document called test'"
```

Make executable:

bash

```bash
chmod +x ~/start-libreoffice-ai.sh
```

Usage:

bash

```bash
ollama serve &
~/start-libreoffice-ai.sh
```