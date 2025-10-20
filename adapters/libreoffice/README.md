# LibreOffice MCP Server

A Model Context Protocol (MCP) server that enables Claude and other AI assistants to interact with LibreOffice documents and presentations directly.

The server builds on the implementation by [harshithb3304](https://github.com/harshithb3304/libre-office-mcp), adding the ability to work with presentations as well as improvements to the code structure and original functions.

## Overview

This MCP server provides a bridge between AI assistants like Claude and LibreOffice, allowing the AI to create, read, edit, and format LibreOffice documents and presentations. Built on the [Model Context Protocol](https://modelcontextprotocol.io/), it exposes LibreOffice functionality as tools that can be called by compatible AI applications.

## Features

### LibreOffice Suite Support

- [x] **LibreWriter**
  - **Implemented:**
    - [x] Create new documents
    - [x] Open and read text documents
    - [x] Copy documents
    - [x] List documents in a directory
    - [x] Get document properties and metadata
    - [x] Add text to documents
    - [x] Add headings with different levels
    - [x] Add formatted paragraphs
    - [x] Add tables with data
    - [x] Format tables with borders, colors, and header rows
    - [x] Search and replace text
    - [x] Delete specific text
    - [x] Delete paragraphs
    - [x] Insert page breaks (partial implementation)
    - [x] Insert images
    - [x] Format specific text (bold, italic, color, size)
  
    
- [ ] **LibreCalc**
- [X] **LibreImpress**
    - [x] Create a new presentation
    - [x] Open and read presentations
    - [x] Add a new slide to a presentation
    - [x] Edit the main text content of a
specific slide
    - [x] Edit the title of a specific slide
    - [x] Delete a slide from a presentation
    - [x] Apply a built-in LibreOffice template
to a presentation
    - [x] Format the content text of a specific
slide
    - [x] Format the title text of a specific
slide
    - [x] Insert an image into a specific slide
of a presentation

## Installation

### Requirements
- Python 3.10 or higher
- LibreOffice installed
- Claude for Desktop (or another MCP-compatible client)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/bthompson-dev/libre-office-mcp.git
   cd libre-office-mcp/libre-writer
   ```

2. **Set up Python environment**
   ```bash
   UV Installation 

   #For Windows  
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   #For MacOS/Linux 
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # With uv (recommended)
   uv init
   uv venv
   uv add mcp[cli] httpx
   
   # With pip
   pip install "mcp[cli]" httpx
   ```

3. **Install LibreOffice**
   - Windows: [Download from LibreOffice website](https://www.libreoffice.org/download/download-libreoffice/)
   - macOS: 
     ```bash
     brew install --cask libreoffice
     ```

## Usage with Claude for Desktop

1. **Configure Claude for Desktop**

   Add the following to your Claude for Desktop configuration file:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "libreoffice-server": {
         "command": "uv",
         "args": [
           "--directory",
           "C:\\path\\to\\libreoffice-mcp-server",
           "run",
           "main.py"
         ]
       }
     }
   }
   ``` 
   or 
   ```json 
   {
     "mcpServers": {
       "libreoffice-server": {
          "command": "python",
          "args": [
            "C:\\path\\to\\the\\main.py"
          ]
        }
      }
   }
   
   ```

   > ⚠️ **Note**: Replace `C:\\path\\to\\libreoffice-mcp-server` with the actual path to where you cloned the repository.

2. **Restart Claude for Desktop**

3. **Interact with LibreOffice**

   You can now ask Claude to perform actions like:
   - "Create a new document with a title and three paragraphs"
   - "List all the documents in my Documents folder"
   - "Open my report.odt file and add a table with 4 columns and 5 rows"

## How It Works

The server consists of three main components:

1. **LibreOffice Helper (`helper.py`)**: A Python script that communicates directly with LibreOffice using the UNO bridge API.

2. **MCP Server (`libre.py`)**: The main MCP server that exposes LibreOffice functionality as tools for AI assistants.

3. **Launcher (`main.py`)**: A script that launches both the helper and the MCP server.

When a request comes in from Claude:

1. The MCP server receives the request
2. It forwards the command to the LibreOffice helper via a socket connection
3. The helper executes the command using LibreOffice's UNO API
4. The result is sent back to the MCP server and then to Claude

## Configuration Options

The server will use your Documents folder as the default location for creating new documents if no path is specified. You can change this by modifying the `get_default_document_path` function in `libre.py`.

## Usage Examples

The table below gives examples of how to use each of the individual tools.

| **Purpose** | **Example Prompt** |
|------------|--------------------|
| Look at document properties | “Can you tell me the properties of the ‘True story’ document?” |
| List all documents | “Can you list all of the available documents?” |
| Make a copy of a document | “Can you make a copy of the Sales Pitch document?” |
| Create a new document | “Can you make a new document called ‘Board Meeting’?” |
| Read contents of a document | “Can you give me a summary of the Meeting Notes document?” |
| Add text | “Can you add the sentence ‘All is fair in love and war’ to the quotes document?” |
| Add headings | “Can you add a new heading, ‘How I found my true self’, to the Meditation document?” |
| Add paragraphs | “Can you add a paragraph about dogs to the animals document?” |
| Add tables | “Can you add a table about the pros and cons of capitalism?” |
| Insert page breaks | “Insert a page break at the end of the Freedom document” |
| Format text | “Please use a bigger font for the text ‘Things can only get better’ – make it green and use the Georgia font” |
| Find and replace text | “Can you replace the phrase ‘We shouldn’t speak any more’ with ‘You know where to find me’” |
| Delete specific text | “Please delete ‘The time has come’ from the proposal document” |
| Format a table | “Please give a header row and thicker borders to the second table in the ‘Product Review’ document” |
| Delete paragraphs | “Delete the first paragraph in the ‘Bird Species’ document” |
| Apply styling to a document | “Please give the ‘Party invitation’ document a fun styling, with big colourful text” |
| Insert images into a document | “Please insert the following image into the ‘Animals’ document: C:\Users\username\Downloads\monkey.png” |
| Create a new presentation | “Can you create me a presentation called ‘Business Proposal’?” |
| Read contents of a presentation | “Can you give me a summary of the ‘Team Agenda’ presentation?” |
| Add a slide with title and content | “Can you add a slide about AI training to the Onboarding presentation?” |
| Change slide title | “Can you change the title of the second slide to ‘Supporting other team members’?” |
| Change slide content | “Can you change the content of the second slide to a list of how to support other members of your team?” |
| Delete a slide | “Delete the fourth slide” |
| Apply a presentation template | “Please apply the Blue Curve template to the Lesson Plan presentation” |
| Format slide title | “Please make the title of the first slide bold, blue and centred” |
| Format slide content | “Please make the content of the first slide smaller and in italics, with a light blue background” |
| Insert image into a slide | “Please insert this image into the 5th slide of the ‘Roadmap’ presentation: C:\Users\username\Pictures\roadmap_diagram.jpeg” |

> ⚠️ **Presentations**: When working with presentations, the AI assistant is limited to a simple slide layout with a title and content textbox. For more sophisticated layouts, you will need to make changes directly in Impress.

> ⚠️ **Images and Presentation Templates**: Images and presentation templates require the exact path of the image or template you want to use. For example, if you wanted to insert an image from your desktop, you should include C:\Users\<username>\Desktop in your message.

## Troubleshooting

### Common Issues

- **"LibreOffice helper is not running"**  
  Make sure LibreOffice is installed and the path to the LibreOffice Python executable is correct in `main.py`.

- **"Connection refused"**  
  The helper script may not have started correctly. Check if port 8765 is already in use.

- **"Failed to connect to LibreOffice desktop"**  
  LibreOffice may not be running in headless mode. Check if port 2002 is available.

## Contributing

All contributions and issues are welcome - please add a PR or raise an issue above.
