# SmolPC 2.0 - Unified App Migration Plan

**Created:** 2025-11-12
**Target Demo Date:** March 3, 2025 (111 days)
**Goal:** Migrate three standalone apps into one unified Tauri+Svelte suite

---

## Executive Summary

### Current State Analysis

| App | Tech Stack | LOC | MCP? | Status | Frontend |
|-----|-----------|-----|------|--------|----------|
| **LibreOfficeAI** | WPF/C# + Python | ~13,000 | ✅ Full | Production MVP | WPF/XAML (Windows-only) |
| **CodeHelper** | Tauri + Rust + JS | ~2,100 | ❌ None | 85% Complete | Vanilla JS (Svelte branch exists) |
| **BlenderHelper** | Tauri + Rust + Python | ~1,200 | ❌ None | Alpha (many bugs) | Vanilla JS (minimal) |

### Critical Findings

1. **CodeHelper** already has:
   - ✅ Production-ready Tauri+Rust architecture
   - ✅ Streaming Ollama integration
   - ✅ Excellent student-focused UI
   - ✅ Active Svelte 5 migration branch
   - ✅ 85% feature complete

2. **LibreOfficeAI** has:
   - ✅ Complete MCP integration (36 tools)
   - ✅ Robust Python backend (8,218 LOC)
   - ✅ Production-quality architecture
   - ❌ Windows-only WPF frontend (must be completely rewritten)

3. **BlenderHelper** has:
   - ✅ Working Blender addon pattern
   - ✅ Tauri+Rust foundation
   - ❌ No MCP integration
   - ❌ Early alpha state ("a lot of bugs")

### Recommended Approach

**Foundation:** Use CodeHelper's Tauri+Svelte architecture as the unified shell
**Backend:** Preserve LibreOfficeAI's Python MCP servers
**Strategy:** Shell-First Sequential Migration (hybrid of Options A & B)

---

## Architecture Comparison

### Option A: LibreOfficeAI as Foundation ❌ (REJECTED)
- **Pro:** Mature MCP integration, complete backend
- **Con:** WPF is Windows-only, requires 100% frontend rewrite
- **Con:** No Tauri experience in codebase
- **Con:** Would need to port CodeHelper features to WPF first, then migrate to Tauri later (double work)

### Option B: CodeHelper as Foundation ✅ (RECOMMENDED)
- **Pro:** Already Tauri+Svelte, cross-platform
- **Pro:** 85% complete with excellent UX
- **Pro:** Svelte migration branch ready to use
- **Pro:** Proven Ollama integration with streaming
- **Con:** No MCP integration yet (but we'll add it)
- **Con:** Needs tool selection UI

### Option C: Start Fresh ❌ (REJECTED - TOO RISKY)
- **Con:** 111 days until demo is too tight for ground-up rebuild
- **Con:** Would waste existing working code

---

## Migration Strategy: Shell-First Sequential Integration

### Phase Overview

```
Timeline: 111 days (15.8 weeks) until March 3, 2025

Phase 1: Foundation (2 weeks)    [Weeks 1-2]   Dec 16 - Dec 29
Phase 2: CodeHelper Core (3 weeks) [Weeks 3-5]   Dec 30 - Jan 19
Phase 3: LibreOffice Integration (4 weeks) [Weeks 6-9]   Jan 20 - Feb 16
Phase 4: Blender Integration (2 weeks) [Weeks 10-11] Feb 17 - Mar 2
Phase 5: Polish & Demo Prep (1 week) [Week 12]      Mar 3 (Demo Day)

Buffer: 3.8 weeks built into schedule
```

---

## Detailed Phase Plans

## Phase 1: Foundation (2 weeks) - Dec 16 to Dec 29

### Goal
Create the unified Tauri+Svelte shell with tool selection and MCP hub architecture.

### Starting Point
Branch from CodeHelper's `claude/svelte-migration-011CV2uFPUy46pKDhLKPXz3s` branch (already has Svelte 5).

### Tasks

#### Week 1: Repository Setup & Shell Structure
**Days 1-3:**
- [ ] Create new repository: `SmolPC-2-0/smolpc-unified`
- [ ] Clone CodeHelper's Svelte migration branch as base
- [ ] Rename project in `package.json`, `Cargo.toml`, `tauri.conf.json`
- [ ] Update branding (logos, colors, app name)
- [ ] Set up multi-adapter directory structure:
  ```
  smolpc-unified/
  ├── src/                    # Svelte frontend
  ├── src-tauri/              # Rust backend
  ├── adapters/               # MCP servers
  │   ├── codehelper/        # New: CodeHelper as MCP server
  │   ├── libreoffice/       # Migrated from existing repo
  │   └── blender/           # Migrated from BlenderHelper
  └── shared/                 # Shared configs & prompts
  ```

**Days 4-7:**
- [ ] Design tool selection UI (Svelte component):
  ```svelte
  <ToolSelector>
    - CodeHelper tile (icon, description)
    - LibreOffice tile (Writer + Impress icons)
    - Blender tile (Blender logo)
  </ToolSelector>
  ```
- [ ] Implement routing:
  ```
  / → Tool selection screen
  /codehelper → Chat interface (existing)
  /libreoffice → LibreOffice chat (new)
  /blender → Blender chat (new)
  ```
- [ ] Add navigation:
  - Back button to return to tool selection
  - Settings page (global + per-tool settings)
  - Help page

#### Week 2: MCP Hub Architecture
**Days 8-10:**
- [ ] Add Rust dependencies for MCP:
  ```toml
  [dependencies]
  # Add to Cargo.toml
  tokio = { version = "1", features = ["full", "process"] }
  tokio-util = "0.7"
  serde = { version = "1", features = ["derive"] }
  serde_json = "1.0"
  ```
- [ ] Create `src-tauri/src/mcp_hub.rs`:
  ```rust
  pub struct McpHub {
      servers: HashMap<String, McpServer>,
      client: reqwest::Client,
  }

  impl McpHub {
      pub async fn start_server(&self, name: &str) -> Result<()>
      pub async fn list_tools(&self, server: &str) -> Result<Vec<Tool>>
      pub async fn call_tool(&self, server: &str, tool: &str, args: Value) -> Result<Value>
  }
  ```
- [ ] Implement MCP stdio protocol (JSON-RPC 2.0):
  - Tool discovery
  - Tool invocation
  - Error handling

**Days 11-14:**
- [ ] Create server configuration system:
  ```json
  // config/servers.json
  {
    "codehelper": {
      "command": "ollama",  // Special: direct Ollama
      "type": "ollama"
    },
    "libreoffice": {
      "command": "./adapters/libreoffice/main.py",
      "args": [],
      "type": "mcp"
    },
    "blender": {
      "command": "./adapters/blender/main.py",
      "args": [],
      "type": "mcp"
    }
  }
  ```
- [ ] Implement server lifecycle management:
  - Auto-start on tool selection
  - Health checks
  - Graceful shutdown
- [ ] Add Tauri commands:
  ```rust
  #[tauri::command]
  async fn select_tool(tool: String) -> Result<ToolInfo>

  #[tauri::command]
  async fn get_available_tools(server: String) -> Result<Vec<Tool>>
  ```

### Deliverables
- ✅ Unified repository structure
- ✅ Tool selection UI (functional)
- ✅ MCP hub architecture (working with mock data)
- ✅ Navigation system
- ✅ Basic settings page

### Testing
- Verify tool selection screen loads
- Test navigation between tools
- Verify MCP hub can be instantiated (even without real servers yet)

---

## Phase 2: CodeHelper as First Tool (3 weeks) - Dec 30 to Jan 19

### Goal
Migrate CodeHelper into the unified app as the first working tool, establishing patterns for other tools.

### Tasks

#### Week 3: CodeHelper MCP Wrapper
**Why MCP wrapper?** Even though CodeHelper talks directly to Ollama, wrapping it in MCP creates a consistent interface with the other tools.

**Days 15-17:**
- [ ] Create `/adapters/codehelper/` directory
- [ ] Implement `codehelper_mcp.py`:
  ```python
  # Python MCP server that wraps CodeHelper's Ollama logic
  from mcp.server.fastmcp import FastMCP

  mcp = FastMCP("CodeHelper MCP Server")

  @mcp.tool()
  async def generate_code(prompt: str, language: str, context: list[str] = None):
      """Generate code based on student's request"""
      # Call Ollama directly
      # Return formatted response

  @mcp.tool()
  async def explain_code(code: str, language: str):
      """Explain existing code to student"""
      # Call Ollama with explanation prompt

  @mcp.tool()
  async def debug_code(code: str, error: str, language: str):
      """Help student fix broken code"""
      # Call Ollama with debugging prompt
  ```
- [ ] Port Rust Ollama client logic from CodeHelper's `lib.rs` to Python
- [ ] Migrate system prompt from CodeHelper:
  ```python
  SYSTEM_PROMPT = """
  You are a friendly, encouraging coding tutor for secondary school
  students aged 11–18...
  """
  ```

**Days 18-21:**
- [ ] Update Svelte frontend for `/codehelper` route
- [ ] Migrate CodeHelper UI components to Svelte:
  ```
  src/lib/components/codehelper/
  ├── CodeChat.svelte          # Main chat interface
  ├── QuickExamples.svelte     # Example prompts
  ├── ContextToggle.svelte     # Context on/off
  ├── ModelSelector.svelte     # Qwen vs DeepSeek
  └── CodeBlock.svelte         # Syntax-highlighted code display
  ```
- [ ] Connect frontend to MCP hub:
  ```typescript
  // Frontend calls MCP hub instead of direct Ollama
  const response = await invoke('call_mcp_tool', {
    server: 'codehelper',
    tool: 'generate_code',
    args: { prompt, language: 'python', context }
  });
  ```

#### Week 4: Streaming & Polish
**Days 22-24:**
- [ ] Implement MCP streaming for CodeHelper:
  ```rust
  // In mcp_hub.rs
  pub async fn call_tool_stream(
      &self,
      server: &str,
      tool: &str,
      args: Value,
      window: tauri::Window
  ) -> Result<()> {
      // Stream chunks via Tauri events
      window.emit("tool_chunk", chunk)?;
  }
  ```
- [ ] Connect streaming to Svelte UI
- [ ] Test with Qwen 2.5 Coder 7B and DeepSeek Coder 6.7B

**Days 25-28:**
- [ ] Migrate chat history/persistence
- [ ] Migrate save/copy functionality
- [ ] Migrate quick examples
- [ ] Test on Windows, macOS (if available), Linux
- [ ] Fix any rendering issues

#### Week 5: Testing & Documentation
**Days 29-35:**
- [ ] Integration testing:
  - Create new chat
  - Generate code with streaming
  - Toggle context on/off
  - Switch models
  - Save code to file
  - Rename/delete chats
- [ ] User testing with students (if possible)
- [ ] Document CodeHelper MCP server
- [ ] Write migration guide for other tools

### Deliverables
- ✅ CodeHelper fully working in unified app
- ✅ MCP wrapper architecture proven
- ✅ Streaming working end-to-end
- ✅ Svelte components established
- ✅ Pattern documented for LibreOffice/Blender

### Testing
- 5 students test CodeHelper functionality
- Verify all features from standalone CodeHelper work
- Performance: Response time < 5s on Intel N200

---

## Phase 3: LibreOffice Integration (4 weeks) - Jan 20 to Feb 16

### Goal
Migrate LibreOfficeAI into the unified app, reusing its excellent Python MCP backend.

### Tasks

#### Week 6: Backend Migration
**Days 36-38:**
- [ ] Copy `/adapters/libreoffice/` from LibreOfficeAI repo:
  ```bash
  cp -r ~/SmolPC-2.0/adapters/libreoffice ./adapters/
  ```
- [ ] Update paths in `main.py`, `helper.py` to work in unified app
- [ ] Test MCP server standalone:
  ```bash
  cd adapters/libreoffice
  python main.py  # Should start LibreOffice + helper + MCP server
  ```
- [ ] Verify all 36 tools discoverable via MCP hub

**Days 39-42:**
- [ ] Create LibreOffice settings in unified settings panel:
  ```svelte
  <LibreOfficeSettings>
    - Documents folder path picker
    - Presentation template paths
    - Template type selector (Writer vs Impress)
  </LibreOfficeSettings>
  ```
- [ ] Migrate `SystemPrompt.txt` and `IntentPrompt.txt` to `/shared/prompts/libreoffice/`
- [ ] Update MCP hub to start LibreOffice server on demand

#### Week 7: Frontend - Writer Support
**Days 43-45:**
- [ ] Create `/src/lib/components/libreoffice/` directory
- [ ] Build LibreOffice chat interface (reuse CodeHelper's chat component):
  ```svelte
  <LibreOfficeChat>
    - Inherits from BaseChat.svelte
    - Custom: Document list panel
    - Custom: Template selector
  </LibreOfficeChat>
  ```
- [ ] Implement document context injection:
  ```typescript
  // Add available documents to AI context
  const systemPrompt = await invoke('get_libreoffice_system_prompt', {
    documentsFolder: settings.documentsPath,
    activeDocuments: currentDocuments
  });
  ```

**Days 46-49:**
- [ ] Implement Writer-specific UI:
  ```svelte
  <DocumentPanel>
    - List of documents in Documents folder
    - "Documents in use" section (clickable file paths)
    - Create document button
  </DocumentPanel>
  ```
- [ ] Wire up Writer tools to MCP:
  - `create_blank_document`
  - `add_text`
  - `format_text`
  - `add_table`
  - `insert_image`
- [ ] Test: "Create a letter about science homework" → verify .odt file created

#### Week 8: Frontend - Impress Support
**Days 50-52:**
- [ ] Add Impress template selector:
  ```svelte
  <TemplateSelector>
    - Built-in templates
    - Custom template paths from settings
    - Preview thumbnails (if possible)
  </TemplateSelector>
  ```
- [ ] Wire up Impress tools:
  - `create_blank_presentation`
  - `add_slide`
  - `edit_slide_content`
  - `apply_presentation_template`

**Days 53-56:**
- [ ] Implement AI tool selection logic (port from LibreOfficeAI's ToolService):
  ```rust
  async fn select_tools_for_prompt(prompt: &str) -> Vec<String> {
      // Call Ollama with IntentPrompt.txt
      // Parse response for tool names
      // Return filtered tool list
  }
  ```
- [ ] Test multi-tool workflows:
  - "Create a presentation about planets with 5 slides"
  - "Add a table to my report document"

#### Week 9: Voice Input & Polish
**Days 57-59:**
- [ ] Add Whisper integration:
  ```toml
  # Option 1: Use whisper.cpp bindings
  whisper-rs = "0.12"

  # Option 2: Call Python whisper via subprocess
  # (reuse LibreOfficeAI's WhisperService approach)
  ```
- [ ] Implement voice recording:
  ```rust
  #[tauri::command]
  async fn start_voice_recording() -> Result<()>

  #[tauri::command]
  async fn stop_voice_recording() -> Result<String>  // Returns transcribed text
  ```
- [ ] Add microphone button to UI (spacebar shortcut)

**Days 60-63:**
- [ ] Integration testing:
  - Create Writer document
  - Create Impress presentation
  - Apply formatting
  - Insert images and tables
  - Voice input workflow
- [ ] Test on target hardware (Intel N200, ~8GB RAM)
- [ ] Performance optimization if needed

### Deliverables
- ✅ LibreOffice Writer fully working
- ✅ LibreOffice Impress fully working
- ✅ 36 MCP tools accessible
- ✅ Voice input functional
- ✅ Document management UI
- ✅ Template system working

### Testing
- Create 10 different document types via chat
- Test all 36 tools at least once
- Voice input accuracy > 85%
- Response time < 5s per tool call

---

## Phase 4: Blender Integration (2 weeks) - Feb 17 to Mar 2

### Goal
Integrate BlenderHelper as the third tool, fixing bugs and adding MCP support.

### Tasks

#### Week 10: Blender MCP Server
**Days 64-66:**
- [ ] Create `/adapters/blender/` directory
- [ ] Convert BlenderHelper's REST API to MCP server:
  ```python
  # blender_mcp.py
  from mcp.server.fastmcp import FastMCP

  mcp = FastMCP("Blender MCP Server")

  @mcp.tool()
  async def create_object(obj_type: str, name: str, location: tuple, size: float):
      """Create a 3D object in Blender"""
      # Send command to blender_helper.py via socket/HTTP

  @mcp.tool()
  async def next_step(goal: str) -> str:
      """Get step-by-step plan for modeling goal"""
      # Use QuickBuilder + Ollama

  @mcp.tool()
  async def generate_bpy_code(goal: str) -> str:
      """Generate executable bpy Python code"""
      # Use existing blender_bridge.rs prompt logic
  ```
- [ ] Migrate Blender addon from BlenderHelper:
  - Copy `blender_addon/blender_helper.py`
  - Update to communicate with MCP server instead of REST API

**Days 67-70:**
- [ ] Port QuickBuilder pattern matching to Python MCP server
- [ ] Implement socket/HTTP communication (blender_mcp.py ↔ blender_helper.py)
- [ ] Test Blender addon connects to MCP server
- [ ] Fix "a lot of bugs" mentioned in BlenderHelper README:
  - Code sanitization improvements
  - Error handling for invalid bpy commands
  - Safety checks before exec()

#### Week 11: Blender UI & Integration
**Days 71-73:**
- [ ] Create Blender chat interface:
  ```svelte
  <BlenderChat>
    - Inherits from BaseChat.svelte
    - Custom: QuickBuilder examples ("cube", "pyramid on sphere")
    - Custom: "Next Step" vs "Do It" toggle
    - Custom: Generated code preview
  </BlenderChat>
  ```
- [ ] Wire up Blender MCP tools to frontend
- [ ] Add Blender-specific settings:
  - Blender executable path detection
  - Default object sizes
  - QuickBuilder enable/disable

**Days 74-77:**
- [ ] Integration testing:
  - Create simple shapes (cube, sphere, pyramid)
  - Complex combinations ("duck on pyramid")
  - Step-by-step mode
  - Direct execution mode
- [ ] Test with real Blender install
- [ ] Fix any addon loading issues
- [ ] Performance testing on target hardware

### Deliverables
- ✅ Blender MCP server working
- ✅ Blender addon updated
- ✅ QuickBuilder functional
- ✅ Blender UI integrated
- ✅ Bug fixes from original BlenderHelper

### Testing
- Create 20 different 3D models via chat
- Test QuickBuilder pattern matching
- Verify code safety (no malicious exec)
- Blender addon loads without errors

---

## Phase 5: Polish & Demo Prep (1 week) - Mar 3 (Demo Day)

### Goal
Final polish, testing, documentation, and demo preparation for March 3 partner presentation.

### Tasks

#### Days 78-84 (Feb 24 - Mar 2):
**Days 78-79: Performance Optimization**
- [ ] Profile app on Intel N200 with ~8GB RAM
- [ ] Optimize Tauri bundle size (target: < 100MB)
- [ ] Test memory usage (target: < 500MB idle, < 2GB with models loaded)
- [ ] Reduce startup time (target: < 5s)

**Days 80-81: Cross-Platform Testing**
- [ ] Test on Windows 10/11
- [ ] Test on macOS (if available)
- [ ] Test on Linux (Ubuntu/Debian)
- [ ] Fix platform-specific bugs

**Days 82-83: Documentation**
- [ ] User manual (PDF):
  - Installation guide
  - Tool selection walkthrough
  - CodeHelper tutorial
  - LibreOffice tutorial
  - Blender tutorial
  - Troubleshooting
- [ ] Developer documentation:
  - Architecture diagram
  - Adding new tools guide
  - MCP server development guide
- [ ] README with screenshots

**Day 84: Demo Preparation**
- [ ] Create demo script:
  1. Tool selection showcase (0:30)
  2. CodeHelper: Student writes Python calculator (2:00)
  3. LibreOffice: Create science report with images (3:00)
  4. Blender: Build 3D classroom model (3:00)
  5. Unified experience: Switch between tools seamlessly (1:30)
  6. Technical highlights: MCP architecture, offline AI, accessibility (2:00)
- [ ] Record demo video (backup)
- [ ] Prepare slide deck (10 slides)
- [ ] Test demo on actual demo hardware
- [ ] Rehearse with team

**Demo Day (March 3, 2025):**
- [ ] 12-minute live demonstration
- [ ] Q&A with partners (Intel, Microsoft, Qualcomm)
- [ ] Handout materials (architecture diagram, roadmap)

### Deliverables
- ✅ Production-ready unified app
- ✅ User manual (PDF)
- ✅ Developer documentation
- ✅ Demo video
- ✅ Slide deck
- ✅ Rehearsed presentation

---

## Technical Architecture

### Final Unified App Structure

```
smolpc-unified/
├── src/                           # Svelte 5 frontend
│   ├── lib/
│   │   ├── components/
│   │   │   ├── common/           # Shared components
│   │   │   │   ├── BaseChat.svelte
│   │   │   │   ├── MessageList.svelte
│   │   │   │   ├── ChatInput.svelte
│   │   │   │   ├── Sidebar.svelte
│   │   │   │   └── Settings.svelte
│   │   │   ├── codehelper/      # CodeHelper-specific
│   │   │   │   ├── CodeChat.svelte
│   │   │   │   ├── QuickExamples.svelte
│   │   │   │   └── CodeBlock.svelte
│   │   │   ├── libreoffice/     # LibreOffice-specific
│   │   │   │   ├── LibreOfficeChat.svelte
│   │   │   │   ├── DocumentPanel.svelte
│   │   │   │   └── TemplateSelector.svelte
│   │   │   └── blender/         # Blender-specific
│   │   │       ├── BlenderChat.svelte
│   │   │       └── QuickBuilder.svelte
│   │   ├── stores/              # Svelte stores
│   │   │   ├── chatStore.ts
│   │   │   ├── settingsStore.ts
│   │   │   └── mcpStore.ts
│   │   └── utils/
│   │       ├── markdown.ts
│   │       └── ollama.ts
│   ├── routes/
│   │   ├── +layout.svelte       # Root layout
│   │   ├── +page.svelte         # Tool selection
│   │   ├── codehelper/
│   │   │   └── +page.svelte
│   │   ├── libreoffice/
│   │   │   └── +page.svelte
│   │   ├── blender/
│   │   │   └── +page.svelte
│   │   └── settings/
│   │       └── +page.svelte
│   └── app.html
│
├── src-tauri/                     # Rust backend
│   ├── src/
│   │   ├── main.rs               # Entry point
│   │   ├── lib.rs                # Core logic
│   │   ├── mcp_hub.rs            # MCP server manager
│   │   ├── ollama.rs             # Ollama client
│   │   ├── settings.rs           # Settings management
│   │   └── voice.rs              # Voice input (Whisper)
│   ├── Cargo.toml
│   └── tauri.conf.json
│
├── adapters/                      # MCP servers (Python)
│   ├── codehelper/
│   │   ├── codehelper_mcp.py     # MCP server
│   │   └── pyproject.toml
│   ├── libreoffice/
│   │   ├── main.py               # Process manager
│   │   ├── libre.py              # MCP server (36 tools)
│   │   ├── helper.py             # UNO API bridge
│   │   ├── helper_utils.py
│   │   └── pyproject.toml
│   └── blender/
│       ├── main.py               # MCP server launcher
│       ├── blender_mcp.py        # MCP server
│       ├── blender_helper.py     # Blender addon
│       └── pyproject.toml
│
├── shared/                        # Shared resources
│   ├── prompts/
│   │   ├── codehelper/
│   │   │   └── system_prompt.txt
│   │   ├── libreoffice/
│   │   │   ├── SystemPrompt.txt
│   │   │   └── IntentPrompt.txt
│   │   └── blender/
│   │       └── system_prompt.txt
│   └── config/
│       ├── servers.json          # MCP server configuration
│       └── settings.json         # App settings
│
├── docs/
│   ├── USER_MANUAL.md
│   ├── DEVELOPER_GUIDE.md
│   ├── ARCHITECTURE.md
│   └── MIGRATION_NOTES.md
│
├── package.json
├── svelte.config.js
├── vite.config.ts
└── README.md
```

### Technology Stack Summary

**Frontend:**
- Svelte 5 (using runes, modern reactive system)
- TypeScript
- Vite (build tool)
- SvelteKit (routing)
- TailwindCSS (styling)
- marked.js (markdown rendering)

**Backend:**
- Rust (Tauri 2.0)
- tokio (async runtime)
- reqwest (HTTP client)
- serde/serde_json (serialization)
- whisper.cpp bindings (voice input)

**MCP Servers:**
- Python 3.12+
- FastMCP framework
- httpx (async HTTP)
- LibreOffice UNO API
- Blender bpy API

**AI:**
- Ollama (localhost:11434)
- Qwen 2.5 Coder 7B
- DeepSeek Coder 6.7B

---

## Migration Decision: Sequential vs Parallel

### ❌ Parallel Migration (All at Once)
**Rejected because:**
- High risk of integration issues
- Hard to debug when everything breaks
- Team coordination overhead
- No working demo until all three are done

### ✅ Sequential Migration (Recommended)
**Chosen because:**
- Lower risk (one tool at a time)
- Can demo progress incrementally
- Learn and improve with each tool
- Always have a working version
- Easier to debug issues

**Order:**
1. **CodeHelper first** - Simplest, already 85% done, establishes patterns
2. **LibreOffice second** - Most complex backend, but backend is ready
3. **Blender last** - Needs most work (bug fixes + MCP), but smallest codebase

---

## Should We Migrate LibreOffice from WPF First?

### Question: Migrate LibreOffice to Tauri/Svelte standalone before unifying?

### ❌ NO - Don't Migrate LibreOffice Standalone First

**Reasons:**
1. **Double work:** WPF → Tauri, then Tauri standalone → Tauri unified
2. **Time waste:** 111 days is tight, can't afford detours
3. **No value:** Standalone LibreOffice Tauri app isn't the goal
4. **Risk:** Might run out of time before unification

### ✅ YES - Keep LibreOffice Backend, Build New Frontend in Unified App

**Approach:**
1. Copy entire `/adapters/libreoffice/` Python backend (already MCP-ready)
2. Build new Svelte frontend directly in unified app
3. Connect Svelte → MCP Hub → LibreOffice backend
4. WPF frontend is simply discarded (not migrated)

**Advantages:**
- Backend is production-ready, zero changes needed
- Frontend built once, in final location
- No intermediate steps
- Faster timeline

---

## Risk Assessment & Mitigation

### High Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Timeline too aggressive** | High | High | Built 3.8 weeks buffer; prioritize MVP features; cut Blender if needed |
| **MCP integration complexity** | Medium | High | Start with CodeHelper (simplest); test MCP hub early; have fallback (direct Ollama) |
| **Svelte 5 learning curve** | Medium | Medium | Use CodeHelper's existing migration as template; pair programming; focus on components not runes |
| **Performance on ~8GB RAM** | Medium | High | Test weekly on target hardware; model streaming; single-app mode fallback |
| **Cross-platform bugs** | Medium | Medium | Test on all platforms bi-weekly; use Tauri best practices; CI/CD for each platform |

### Medium Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **LibreOffice UNO API issues** | Low | Medium | Backend already works; just reuse; have LibreOffice expert on call |
| **Blender addon bugs** | High | Low | Fix during integration; extensive testing; QuickBuilder is fallback |
| **Whisper model size** | Medium | Low | Use base model (~150MB); lazy loading; optional feature |
| **Voice input quality** | Medium | Low | Test with students; threshold tuning; text fallback always available |

### Mitigation Strategies

1. **Weekly demos** - Show progress to team/advisor every Friday
2. **Daily standups** - 15-minute sync each morning
3. **Feature flags** - Can disable incomplete tools for demo
4. **Fallback modes:**
   - If MCP fails → Direct Ollama calls
   - If voice fails → Text input only
   - If Blender not ready → CodeHelper + LibreOffice still impressive
5. **Early testing** - Get student feedback by Feb 1 (1 month before demo)

---

## Team Allocation

### Roles & Responsibilities

**Mathias Tidball (Team Lead):**
- Phase 1: MCP hub architecture (Rust)
- Phase 3: LibreOffice backend integration
- Phase 5: Demo coordination
- Ongoing: Code reviews, architecture decisions

**Stefanos Ioannidis (Backend Lead + CodeHelper):**
- Phase 1: Repository setup
- Phase 2: CodeHelper migration (lead)
- Phase 3: Ollama integration patterns
- Ongoing: Backend code reviews

**Siddhant Murugkar (Blender Lead):**
- Phase 2: Svelte components (assist)
- Phase 4: Blender migration (lead)
- Phase 5: Blender demo script
- Ongoing: Testing on macOS (if available)

**[Team Member 4] (MCP Integration Lead):**
- Phase 1: MCP hub development
- Phase 2-4: MCP server integrations
- Phase 3: LibreOffice MCP testing
- Ongoing: MCP protocol expertise

**[Team Member 5] (Frontend & Testing):**
- Phase 1: Tool selection UI
- Phase 2-4: Svelte components
- Phase 5: User testing coordination
- Ongoing: QA, accessibility testing

### Workload Distribution

```
Phase 1 (2 weeks):
- Mathias: MCP hub (Rust) - 30 hrs
- Stefanos: Repo setup + navigation - 20 hrs
- [TM4]: MCP protocol research - 20 hrs
- [TM5]: Tool selection UI - 25 hrs
- Siddhant: Design review + testing - 10 hrs

Phase 2 (3 weeks):
- Stefanos: CodeHelper migration - 50 hrs (lead)
- [TM5]: Svelte components - 40 hrs
- Mathias: MCP wrapper - 20 hrs
- [TM4]: Streaming support - 20 hrs
- Siddhant: Testing - 15 hrs

Phase 3 (4 weeks):
- Mathias: LibreOffice backend - 40 hrs (lead)
- [TM5]: LibreOffice UI - 50 hrs
- [TM4]: Tool selection AI - 30 hrs
- Stefanos: Voice input - 30 hrs
- Siddhant: Testing + docs - 20 hrs

Phase 4 (2 weeks):
- Siddhant: Blender migration - 40 hrs (lead)
- [TM4]: Blender MCP - 25 hrs
- [TM5]: Blender UI - 20 hrs
- Mathias: Bug fixes - 15 hrs
- Stefanos: Integration testing - 15 hrs

Phase 5 (1 week):
- ALL: Testing, documentation, demo prep - 20 hrs each
```

---

## Success Criteria

### MVP (Must Have for Demo)
- ✅ All three tools accessible from unified app
- ✅ CodeHelper: Generate code, streaming works, chat history
- ✅ LibreOffice: Create Writer docs and Impress presentations
- ✅ Blender: Create basic 3D objects
- ✅ MCP hub connects to all three backends
- ✅ Settings page functional
- ✅ Runs on Windows with Intel N200 + ~8GB RAM
- ✅ < 5s response time for simple requests
- ✅ 12-minute demo executes flawlessly

### Nice to Have (Stretch Goals)
- 🎯 Voice input working for all tools
- 🎯 Cross-platform (Windows + macOS)
- 🎯 Advanced LibreOffice features (complex tables, templates)
- 🎯 Blender QuickBuilder extensive library
- 🎯 Dark mode
- 🎯 Accessibility features (screen reader support)

### Quality Metrics
- **Performance:** < 5s response time on target hardware
- **Stability:** < 1% crash rate during testing
- **Usability:** SUS score ≥ 70 (if time for user testing)
- **Bundle Size:** < 100MB (excluding AI models)
- **Memory:** < 2GB with models loaded
- **Test Coverage:** ≥ 50% for critical paths

---

## Alternative Approaches Considered

### Alternative 1: Keep Three Separate Apps + Launcher
**Idea:** Build a simple launcher that opens CodeHelper, LibreOffice, or Blender apps separately.

**Pros:**
- Less integration work
- Lower risk
- Can reuse existing apps mostly as-is

**Cons:**
- Not a "unified app" (doesn't meet spec)
- No shared settings
- No MCP hub benefits
- Separate installations
- Poor user experience

**Decision:** ❌ Rejected - Doesn't align with project vision

### Alternative 2: Web App (Electron)
**Idea:** Build unified app as Electron web app instead of Tauri.

**Pros:**
- Easier for web developers
- Larger ecosystem
- More libraries available

**Cons:**
- Much larger bundle size (>200MB vs <50MB)
- Higher memory usage (Chromium overhead)
- Against project goals (lightweight, resource-efficient)
- Team already has Tauri experience (CodeHelper, Blender)

**Decision:** ❌ Rejected - Tauri aligns better with SmolPC goals

### Alternative 3: Keep WPF, Add Blender/CodeHelper to it
**Idea:** Migrate CodeHelper and Blender into the LibreOfficeAI WPF app.

**Pros:**
- LibreOffice frontend already done
- Mature codebase

**Cons:**
- Windows-only (fails cross-platform requirement)
- Against Tauri migration plan in spec
- Requires porting CodeHelper/Blender to C#
- Larger bundle size
- Not the team's strategic direction

**Decision:** ❌ Rejected - Doesn't meet cross-platform requirement

---

## Open Questions

1. **Who are Team Members 4 and 5?**
   - Need names/skills to finalize allocation
   - Assumption: Both have full-stack capability

2. **Do we have macOS/Linux test machines?**
   - Critical for cross-platform testing
   - Can use VMs if not

3. **Is there budget for Whisper model hosting?**
   - ~150MB model file
   - Could host on UCL servers or bundle in installer

4. **What's the minimum viable demo?**
   - Can we cut Blender if timeline is tight?
   - CodeHelper + LibreOffice might be sufficient for impact

5. **Do we have access to student testers?**
   - Recommended: 5-10 students for Phase 3 testing
   - Ages 11-18, various skill levels

6. **What's the distribution plan after demo?**
   - GitHub releases?
   - UCL internal only?
   - Public beta?

---

## Next Steps (Immediate Actions)

### This Week (Week 0: Dec 9-15)
1. **Team meeting** - Review this plan, assign roles, get buy-in
2. **Create unified repo** - `SmolPC-2-0/smolpc-unified`
3. **Set up project board** - GitHub Projects with all tasks
4. **Environment setup:**
   - Everyone installs: Rust, Node.js, Python 3.12, Tauri CLI
   - Everyone clones: CodeHelper (Svelte branch), LibreOfficeAI, BlenderHelper
5. **Baseline testing:**
   - Test LibreOfficeAI MCP backend standalone
   - Test CodeHelper standalone
   - Test BlenderHelper standalone
6. **Design mockups:**
   - Tool selection screen
   - Navigation UI
   - Settings page layout

### Week 1 (Dec 16-22) - Start Phase 1
- Begin repository setup (see Phase 1 tasks)
- Daily standups at 9:00 AM
- First demo: Friday Dec 20 (tool selection screen mockup)

---

## Appendix A: Dependency Matrix

### Shared Dependencies (All Tools)
- Ollama (localhost:11434)
- Python 3.12+
- Rust/Cargo
- Node.js/npm
- Tauri CLI

### Tool-Specific Dependencies

**CodeHelper:**
- Qwen 2.5 Coder 7B model (~4.7GB)
- DeepSeek Coder 6.7B model (~3.8GB)

**LibreOffice:**
- LibreOffice 7.6+ or Collabora Office
- Python UNO bindings (usually bundled with LibreOffice)
- LibreOffice headless mode support
- Qwen model (or other 7B model)

**Blender:**
- Blender 3.6+ with Python API
- bpy module
- Llama 3.2 model (or Qwen 2.5 Coder)

### Platform-Specific

**Windows:**
- MSVC build tools (for Rust)
- Windows SDK
- .NET 8 runtime (for testing LibreOfficeAI comparison)

**macOS:**
- Xcode command line tools
- macOS 10.15+ (Catalina or later)

**Linux:**
- build-essential
- libssl-dev, libgtk-3-dev
- libreoffice package

---

## Appendix B: File Size Estimates

### Unified App Bundle Sizes (Excluding Models)

**Windows:**
- Tauri executable: ~15MB
- Embedded assets: ~5MB
- Python adapters: ~2MB
- **Total:** ~22MB

**macOS:**
- .app bundle: ~18MB
- Python adapters: ~2MB
- **Total:** ~20MB

**Linux:**
- AppImage: ~20MB
- Python adapters: ~2MB
- **Total:** ~22MB

### AI Models (Downloaded Separately)
- Qwen 2.5 Coder 7B: ~4.7GB
- DeepSeek Coder 6.7B: ~3.8GB
- Whisper base: ~150MB
- **Total (if all downloaded):** ~8.65GB

### Recommended Distribution
- Base app: ~22MB download
- Models: Downloaded on first run (with progress bar)
- Total installation: ~9GB with all models

---

## Appendix C: Testing Checklist

### Phase 2 Testing (CodeHelper)
- [ ] Generate Python code (calculator, loops, functions)
- [ ] Generate JavaScript code (DOM manipulation, events)
- [ ] Generate HTML/CSS (simple webpage)
- [ ] Debug broken code (syntax errors, logic errors)
- [ ] Context toggle on/off
- [ ] Model switching (Qwen ↔ DeepSeek)
- [ ] Chat history (create, load, rename, delete)
- [ ] Save code to file (.py, .js, .html)
- [ ] Copy code to clipboard
- [ ] Streaming response (chunks arrive smoothly)
- [ ] Quick examples work
- [ ] Settings persist across restarts

### Phase 3 Testing (LibreOffice)
**Writer:**
- [ ] Create blank document
- [ ] Add text with formatting (bold, italic, underline, colors)
- [ ] Add headings (H1, H2, H3)
- [ ] Add tables (2x2, 3x5, with formatting)
- [ ] Insert images (PNG, JPEG)
- [ ] Insert page breaks
- [ ] Search and replace text
- [ ] Delete paragraphs
- [ ] Apply document styles

**Impress:**
- [ ] Create blank presentation
- [ ] Add slides (title, content, blank)
- [ ] Edit slide titles
- [ ] Edit slide content (bullet points)
- [ ] Delete slides
- [ ] Apply templates
- [ ] Format slide text (colors, sizes)
- [ ] Insert images on slides

**General:**
- [ ] Document list updates
- [ ] File paths clickable
- [ ] Multiple documents in use
- [ ] Voice input (if implemented)
- [ ] AI tool selection accuracy (picks right tools)

### Phase 4 Testing (Blender)
- [ ] Create primitives (cube, sphere, cylinder, cone)
- [ ] QuickBuilder patterns ("pyramid", "duck", "cube on sphere")
- [ ] Transform objects (move, rotate, scale)
- [ ] Multi-step plans ("Next Step" mode)
- [ ] Direct execution ("Do It" mode)
- [ ] Code preview (view generated bpy code)
- [ ] Blender addon loads without errors
- [ ] Safety checks (no malicious code execution)

### Phase 5 Testing (Integration)
- [ ] Switch between all three tools seamlessly
- [ ] Settings apply to all tools
- [ ] Navigation works (back button, sidebar)
- [ ] Performance on Intel N200 + ~8GB RAM
- [ ] Memory usage < 2GB
- [ ] Cross-platform (Windows, macOS, Linux)
- [ ] Demo script runs flawlessly (5 rehearsals)

---

## Summary & Recommendation

### Recommended Path Forward

**Strategy:** Shell-First Sequential Migration
- **Week 1-2:** Build unified Tauri+Svelte shell + MCP hub
- **Week 3-5:** Migrate CodeHelper (establishes patterns)
- **Week 6-9:** Integrate LibreOffice (reuse backend, new frontend)
- **Week 10-11:** Integrate Blender (fix bugs, add MCP)
- **Week 12:** Polish and demo prep

**Foundation:** CodeHelper's Svelte migration branch
- Already has Tauri 2.0 + Svelte 5
- Proven Ollama integration
- Excellent UX

**Backend:** Preserve all Python MCP servers
- LibreOffice: Copy existing (production-ready)
- Blender: Convert REST API to MCP
- CodeHelper: Wrap Ollama in MCP (new)

**Timeline:** 12 weeks (84 days) with 3.8 weeks buffer

**Risk Level:** Medium (mitigated by sequential approach + buffer time)

**Success Probability:** 85% (assuming team availability + no major blockers)

---

## Final Thought

This migration is ambitious but achievable. The key to success is:
1. **Don't reinvent** - Reuse working backends (especially LibreOffice)
2. **Start simple** - CodeHelper first to prove the pattern
3. **Test early** - Weekly hardware testing prevents late surprises
4. **Stay flexible** - Feature flags allow graceful degradation
5. **Ship MVP** - Even CodeHelper + LibreOffice is impressive for demo

**The March 3 demo is achievable if we start this week.**

Good luck! 🚀
