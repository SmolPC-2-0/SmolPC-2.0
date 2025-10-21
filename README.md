# SmolPC-2.0
AI-powered educational assistants for open source applications (LibreOffice, Blender, GIMP). Designed for accessibility and offline use.

## Credits

Based on the original [SmolPC](https://github.com/bthompson-dev/SmolPC) project by Ben Thompson.

LibreOffice integration adapted from [libre-office-mcp](https://github.com/bthompson-dev/libre-office-mcp).

## Team

University College London
- Mathias Tidball
- Stefanos Ioannidis
- Siddhant Murugkar
- Rabiyah Mon
- Aishah Mohammed

## Partners

- IBM
- Intel
- Qualcomm  
- Microsoft

## Platform Support

### Windows (Primary - Main Branch)
**Status:** Active development  
**UI:** WPF native application  
**Target:** Showcase for Intel, Microsoft, Qualcomm partners  
**Setup:** See `docs/SETUP_WINDOWS.md`

### macOS/Linux (Cross-Platform Branch)
**Status:** Experimental  
**Branch:** `cross-platform`  
**UI:** Claude Desktop (current) / Tauri (planned)  
**Setup:** See `docs/SETUP_MAC.md`

**Note:** Backend (MCP adapters) is fully cross-platform. Platform differences are UI-only.

---

## Repository Structure
```
SmolPC-2.0/
├── adapters/              # MCP adapters for different applications
│   └── libreoffice/      # LibreOffice Writer & Impress adapter
│       ├── helper.py     # UNO API bridge to LibreOffice
│       ├── libre.py      # MCP server exposing tools
│       └── main.py       # Launcher script
│
├── ui/                   # User interfaces
│   └── desktop-wpf/      # Windows native WPF application
│       ├── MainWindow.xaml
│       ├── Services/     # Ollama, Whisper, Document services
│       └── ViewModels/   # MVVM architecture
│
├── docs/                 # Documentation
│   ├── SETUP_WINDOWS.md  # Windows installation (coming soon)
│   ├── SETUP_MAC.md      # macOS installation
│   └── ARCHITECTURE.md   # System design (coming soon)
│
└── deployment/           # Packaging & installers (planned)
```

### Key Components

**Adapters** (`adapters/`)
- Self-contained MCP servers for each application
- Communicate with apps via their native APIs (UNO for LibreOffice, bpy for Blender)
- Cross-platform Python code

**UI** (`ui/`)
- Windows: WPF desktop application (main showcase)
- Cross-platform: Experimental (see `cross-platform` branch)

**Future Additions:**
- `adapters/blender/` - 3D modeling control
- `adapters/gimp/` - Image editing control
- `core/` - Shared routing and AI engine code
- `educational/` - Content filtering, reading level adjustment

---

## Development Workflow

### For Windows Developers
1. Follow `docs/SETUP_WINDOWS.md`
2. Work on `main` branch
3. Focus on WPF UI polish

### For Mac/Linux Developers  
1. Follow `docs/SETUP_MAC.md`
2. Work on backend adapters (cross-platform)
3. Optionally experiment with Tauri UI on `cross-platform` branch
4. Use Claude Desktop for testing

### For Everyone
- Backend code (adapters) works on all platforms
- Contribute adapters, educational features, core logic
- Platform differences are UI-only