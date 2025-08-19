# GPT-OSS Ollama Edition

A local AI chat system powered by Ollama, providing a fast and stable conversational AI experience with complete privacy protection.

![GPT-OSS Logo](https://img.shields.io/badge/GPT--OSS-Ollama-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-teal?style=for-the-badge&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-AI-purple?style=for-the-badge)

## ✨ Features

- 🔒 **Complete Privacy**: Runs entirely locally, no data leaves your machine
- ⚡ **High Performance**: Powered by GPT-OSS:20B model (13GB)
- 🎨 **Modern UI**: Clean, responsive web interface inspired by Ollama
- 💬 **Real-time Chat**: WebSocket-based instant messaging
- 📚 **Conversation History**: Persistent storage and context management
- ⚙️ **Customizable Settings**: Adjustable temperature, response modes, and length
- 🚀 **One-Click Start**: Automatic environment checking and service startup

## 🏗️ Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐    HTTP API    ┌─────────────────┐
│   Frontend      │ ◄──────────────► │   Backend       │ ◄─────────────► │  Ollama Service │
│  (HTML/JS SPA)  │                  │  (FastAPI)      │                │  (gpt-oss:20b)  │
└─────────────────┘                  └─────────────────┘                └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama**: Download from [https://ollama.ai](https://ollama.ai)
2. **Download the model**:
   ```bash
   ollama pull gpt-oss:20b
   ```
3. **Python 3.8+**: Ensure Python is installed

### Installation & Running

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/GPT-OSS-Ollama.git
   cd GPT-OSS-Ollama
   ```

2. **Start the system**:
   ```bash
   python start_ollama.py
   ```

3. **Access the application**: Browser will automatically open at `http://127.0.0.1:8000`

The startup script will automatically:
- ✅ Check Ollama service status
- ✅ Verify model availability
- ✅ Install Python dependencies
- ✅ Clean up port conflicts
- ✅ Start the web server
- ✅ Open your browser

## 🎛️ Configuration

### Response Modes
- **Balanced** (recommended): Optimal balance of creativity and accuracy
- **Creative**: More diverse and creative responses
- **Focused**: More accurate and focused responses
- **Detailed**: Comprehensive explanations

### Adjustable Parameters
- **Response Length**: 512 - 4096 tokens
- **Temperature**: 0.1 - 1.5 (creativity level)
- **Context History**: Automatically managed

## 📁 Project Structure

```
GPT-OSS-Ollama/
├── start_ollama.py              # 🚀 Main startup script
├── backend/
│   ├── app_ollama.py           # FastAPI web server
│   ├── conversation_storage.py # Conversation persistence
│   └── conversations/          # Stored chat history
├── frontend/
│   └── index_new.html          # Complete SPA interface
├── requirements.txt            # Python dependencies
├── ARCHITECTURE.md             # Detailed architecture docs
└── CLAUDE.md                   # Development guidelines
```

## 🔧 Development

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main web interface |
| GET | `/status` | System health check |
| GET | `/models` | Available AI models |
| GET | `/conversations` | Chat history list |
| WS | `/ws/{session_id}` | Real-time chat WebSocket |

### Running in Development Mode

```bash
# Direct backend start
python -m backend.app_ollama

# Install dependencies only
pip install -r requirements.txt

# Check Ollama connection
curl http://localhost:11434/api/tags
```

## 📋 System Requirements

### Hardware
- **CPU**: 8+ cores recommended
- **RAM**: 16GB minimum (32GB recommended)
- **Storage**: 20GB free space (13GB for model)
- **GPU**: Optional (CUDA support for acceleration)

### Software
- **OS**: Windows 10/11, macOS, Linux
- **Python**: 3.8 or higher
- **Ollama**: Latest version with gpt-oss:20b support

## 🐛 Troubleshooting

### Common Issues

**🔴 "ModuleNotFoundError: No module named 'conversation_storage'"**
- **Solution**: Use relative imports, run from project root

**🔴 "Failed to load resolver for the server responded with a status of 404"**
- **Solution**: Ensure Ollama service is running: `ollama serve`

**🔴 "Sorry, the response generation was interrupted"**
- **Solution**: Fixed in latest version - async task management improved

**🔴 Port 8000 already in use**
- **Solution**: Run `python kill_port_8000.py` or restart system

### Debug Commands

```bash
# Check Ollama service
ollama --version
curl http://localhost:11434/api/tags

# Check port usage
netstat -ano | findstr :8000

# Test API directly
curl http://127.0.0.1:8000/status
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Test thoroughly with `python start_ollama.py`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) for the excellent local AI infrastructure
- [FastAPI](https://fastapi.tiangolo.com/) for the modern web framework
- The open-source community for inspiration and tools

## 🔗 Related Projects

- [Original GPT-OSS](https://github.com/yourusername/GPT-OSS)
- [Ollama](https://github.com/jmorganca/ollama)
- [FastAPI](https://github.com/tiangolo/fastapi)

---

⭐ **If this project helps you, please consider giving it a star!** ⭐