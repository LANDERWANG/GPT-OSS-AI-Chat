# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GPT-OSS Ollama is a local AI chat system that provides a web-based interface for conversing with the Ollama-hosted GPT-OSS:20B model. It uses a three-tier architecture: frontend (HTML/JS), backend (FastAPI), and AI service (Ollama).

## Essential Commands

### Starting the System
```bash
# Primary method - includes all checks and setup
python start_ollama.py

# Direct backend start (for development)
python -m backend.app_ollama

# Install dependencies
pip install -r requirements.txt
```

### Ollama Operations
```bash
# Check Ollama service
ollama --version
curl http://localhost:11434/api/tags

# Start Ollama service (if not auto-started)
ollama serve

# Verify GPT-OSS model
ollama list | findstr gpt-oss
ollama pull gpt-oss:20b  # If model missing
```

### Port Management
```bash
# Kill processes on port 8000 (Windows)
python kill_port_8000.py
# Or use the batch file
kill_port_8000.bat

# Check port usage
netstat -ano | findstr :8000
```

### Testing API Endpoints
```bash
# System status
curl http://127.0.0.1:8000/status

# Available models
curl http://127.0.0.1:8000/models

# Conversations list
curl http://127.0.0.1:8000/conversations

# Test Ollama directly
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss:20b\",\"prompt\":\"Hello\",\"stream\":false}"
```

## Architecture & Key Components

### Core Architecture Flow
```
Frontend (SPA) ↔ WebSocket ↔ FastAPI Backend ↔ HTTP API ↔ Ollama Service ↔ GPT-OSS:20B Model
```

### Backend Service (`backend/app_ollama.py`)
- **Main Application**: FastAPI app serving on port 8000
- **WebSocket Handler**: `/ws/{session_id}` for real-time chat
- **Ollama Integration**: Non-streaming API calls to `http://localhost:11434`
- **Conversation Management**: In-memory (10 recent) + persistent storage
- **Key Configuration**: `OLLAMA_BASE_URL`, `OLLAMA_MODEL = "gpt-oss:20b"`

### Conversation Storage (`backend/conversation_storage.py`)
- **File-based persistence**: JSON files in `conversations/data/`
- **Index management**: `conversations/index.json` tracks all conversations
- **Storage pattern**: Each conversation gets unique UUID filename
- **Auto-cleanup**: Creates directories and index if missing

### Frontend (`frontend/index_new.html`)
- **Single Page Application**: No external dependencies
- **WebSocket Client**: Connects to `/ws/{session_id}`
- **UI Components**: Sidebar (conversations), main chat area, settings panel
- **Response Modes**: balanced, creative, focused, detailed
- **Auto-reconnection**: 3-second retry on disconnect

### Startup Script (`start_ollama.py`)
- **Environment validation**: Checks Ollama service, model, dependencies
- **Port cleanup**: Kills existing processes on port 8000
- **Service orchestration**: Starts backend and opens browser
- **Error handling**: User-friendly messages for common issues

## Important Implementation Details

### WebSocket Message Flow
1. **User message** → `type: "chat"` with message and settings
2. **Backend processing** → Creates/loads conversation, builds context
3. **Ollama API call** → Non-streaming request with conversation history
4. **Response handling** → Saves to storage, sends via WebSocket
5. **Progress updates** → Heartbeat every 5 seconds during generation

### Async Task Management
- **Critical fix**: Removed `asyncio.wait_for()` timeout that was canceling tasks
- **Heartbeat system**: Uses `asyncio.sleep(5)` instead of task cancellation
- **Error boundaries**: Separate handling for `CancelledError` vs other exceptions
- **Connection cleanup**: Tasks cancelled only when WebSocket disconnects

### Context Management
- **Memory limit**: 10 most recent conversation turns kept in memory
- **History building**: `build_context_prompt()` includes last 3 conversations
- **Session isolation**: Each WebSocket session has independent conversation history
- **Persistence**: Full conversations saved to JSON, memory used for performance

### Key Configuration Points
- **Model**: `gpt-oss:20b` (13GB download required)
- **Ports**: Backend on 8000, Ollama on 11434
- **Timeouts**: 300 seconds for Ollama API calls
- **Context length**: 4096 tokens max
- **Response modes**: Control temperature, top_p, top_k, repeat_penalty

## Development Considerations

### When Making Backend Changes
- The WebSocket connection is persistent - test reconnection scenarios
- Async task cancellation must be handled gracefully
- Conversation storage is file-based - consider concurrent access
- Frontend caches are aggressive - force refresh (Ctrl+F5) after changes

### When Modifying Frontend
- WebSocket reconnection logic is critical for user experience
- Settings are applied per-message, not globally
- Progress messages help users understand long response times (20B model)
- Browser compatibility: Uses modern JS but no external frameworks

### Ollama Integration Patterns
- Always check service availability before API calls
- Use non-streaming mode for stability (streaming had issues)
- Handle model loading delays (first request can take 30+ seconds)
- Ollama service must be running before backend starts

### Common Error Patterns
- **Import errors**: Check relative imports in `backend/app_ollama.py`
- **Port conflicts**: Multiple instances or crashed processes
- **Model not found**: Ollama service running but model not pulled
- **WebSocket drops**: Usually network/browser, auto-reconnect handles it
- **Unicode issues**: Fixed in `start_ollama.py` for Windows console

## File Structure Significance
```
backend/app_ollama.py          # Main FastAPI application
backend/conversation_storage.py # Persistent storage manager
frontend/index_new.html        # Complete SPA (no build process)
start_ollama.py               # System orchestrator and health checker
conversations/                # Persistent conversation data
requirements.txt              # Core dependencies for Ollama version
```

The system is designed for local deployment with privacy in mind - all data stays on the local machine and no external API calls are made during normal operation.