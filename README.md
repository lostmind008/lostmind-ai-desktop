# LostMindAI Platform v2.0

**Advanced AI Assistant Platform with Desktop & Web Clients**

A comprehensive AI platform featuring Google Gemini integration, sophisticated RAG capabilities, and both desktop (PyQt6) and web (Next.js) interfaces. Built for intelligent conversations enhanced by your own knowledge bases.

## 🚀 Platform Overview

LostMindAI v2.0 is a complete transformation from a simple desktop app to a full-scale AI platform with:
- **FastAPI Backend**: Production-ready API service with WebSocket support
- **PyQt6 Desktop Client**: Modern desktop application 
- **Next.js Web Client**: Responsive web interface with real-time chat
- **RAG System**: Retrieval-Augmented Generation with vector search
- **Knowledge Management**: Create and manage custom knowledge bases
- **Multi-modal AI**: Support for text, images, documents, and videos

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Desktop Client │    │   Web Client    │    │   Mobile App    │
│    (PyQt6)      │    │   (Next.js)     │    │   (Future)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │      FastAPI Backend          │
                 │   (/api/v1/* + WebSocket)     │
                 └───────────────┬───────────────┘
                                 │
      ┌──────────┬─────────────────┼─────────────────┬─────────────┐
      │          │                 │                 │             │
┌─────▼────┐ ┌─────▼────┐ ┌─────────▼──────┐ ┌──────▼──────┐ ┌────▼────┐
│PostgreSQL│ │  Redis   │ │ Google Cloud   │ │Vector Store │ │ Gemini  │
│ Database │ │  Cache   │ │    Storage     │ │(pgvector)   │ │   API   │
└──────────┘ └──────────┘ └────────────────┘ └─────────────┘ └─────────┘
```

## ✨ Key Features

### 🤖 Advanced AI Capabilities
- **Google Gemini 2.0 Integration**: Latest models with thinking process visualization
- **Multi-modal Support**: Text, images, documents, videos, and audio
- **Search Grounding**: Real-time web search integration for enhanced responses
- **Streaming Responses**: Real-time AI responses with typing indicators

### 📚 Knowledge Management & RAG
- **Knowledge Bases**: Create unlimited custom knowledge bases
- **Document Processing**: Support for PDF, text, markdown, CSV, JSON, XML, and images
- **Vector Search**: Semantic search with pgvector and cosine similarity
- **RAG Queries**: Context-aware responses using your documents
- **Multi-KB Search**: Query across multiple knowledge bases simultaneously

### 🖥️ Desktop Application (PyQt6)
- **Modern Interface**: Clean, responsive UI with dark/light themes
- **File Management**: Drag-and-drop file uploads with validation
- **Session Management**: Save, export, and organize chat sessions
- **Settings Panel**: Comprehensive configuration options
- **Offline Capability**: Works without internet for basic functions

### 🌐 Web Application (Next.js)
- **Real-time Chat**: WebSocket-powered instant messaging
- **Responsive Design**: Works on desktop, tablet, and mobile
- **PWA Support**: Install as a progressive web app
- **Session Sync**: Seamless session management across devices
- **Modern UI**: Tailwind CSS with custom LostMindAI branding

### 🔧 Backend Infrastructure
- **FastAPI Service**: High-performance async API with OpenAPI docs
- **WebSocket Support**: Real-time bidirectional communication
- **Database Integration**: PostgreSQL with vector extensions
- **Caching Layer**: Redis for enhanced performance
- **Cloud Storage**: Google Cloud Storage for file management

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern, fast web framework
- **PostgreSQL** - Primary database with pgvector extension
- **Redis** - Caching and session management
- **Google Cloud** - Storage and AI services
- **SQLAlchemy** - ORM with async support
- **Alembic** - Database migrations

### Desktop Client
- **PyQt6** - Modern Qt bindings for Python
- **Markdown Rendering** - Rich text display
- **File Handling** - Multi-format support
- **Configuration Management** - JSON-based settings

### Web Client
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Socket.io** - Real-time communication
- **React Hook Form** - Form management

### AI & ML
- **Google Gemini** - Latest language models
- **Vertex AI** - Enterprise AI platform
- **Text Embeddings** - Vector representations
- **pgvector** - PostgreSQL vector extension

## 📦 Installation & Setup

### Prerequisites
- **Python 3.11+** (tested and verified)
- **Node.js 18+** (tested with v23.9.0)
- **PostgreSQL 14+ with pgvector** (or SQLite with aiosqlite for development)
- **Redis 6+** (optional for caching)
- **Google Cloud account** with Gemini API access

### 1. Clone Repository
```bash
git clone https://github.com/lostmind008/lostmindai-platform-v2.git
cd lostmindai-platform-v2
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment (recommended)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (147 packages)
pip install -r requirements.txt

# Configure environment (SQLite by default for development)
cp .env.example .env
# Edit .env with your Google Cloud credentials

# Run database migrations (if using PostgreSQL)
alembic upgrade head

# Start backend (FastAPI with 38 routes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Web Client Setup
```bash
cd web-client

# Install dependencies (860 packages)
npm install

# Start development server
npm run dev

# Note: Build issues exist (Next.js config deprecations)
# These are non-critical and will be addressed in future updates
```

### 4. Desktop Client Setup
```bash
# From project root directory
# Use same virtual environment as backend or create new one
pip install PyQt6  # Version 6.9.0 tested and working

# Run desktop app (from project root)
python src/main.py

# Alternative with explicit Python path
PYTHONPATH=./src python src/main.py

# Or use the convenience scripts
python run.py           # Cross-platform
./run.sh               # Unix/Linux/macOS  
run.bat                # Windows
```

## 🚀 Usage Examples

### Creating a Knowledge Base
```python
# Using the API
import requests

# Create knowledge base
kb_data = {
    "name": "Company Docs", 
    "description": "Internal documentation"
}
response = requests.post("http://localhost:8000/api/v1/rag/knowledge-bases", json=kb_data)
kb = response.json()

# Add document
doc_data = {
    "title": "Employee Handbook",
    "content": "...",
    "metadata": {
        "title": "Employee Handbook",
        "source": "hr_docs",
        "document_type": "text",
        "tags": ["hr", "policies"]
    }
}
requests.post(f"http://localhost:8000/api/v1/rag/knowledge-bases/{kb['id']}/documents", json=doc_data)
```

### RAG Query
```python
# Query knowledge base
query_data = {
    "query": "What is the vacation policy?",
    "k": 5,
    "similarity_threshold": 0.7
}
response = requests.post(f"http://localhost:8000/api/v1/rag/knowledge-bases/{kb_id}/query", json=query_data)
result = response.json()

print(f"Answer: {result['response']}")
print(f"Sources: {len(result['sources'])}")
```

## 🏁 Quick Start Demo

Run the included demo to see RAG capabilities:

```bash
cd backend
python setup_rag_demo.py
```

This will:
1. Create a sample knowledge base
2. Add demo documents about LostMindAI
3. Run sample queries
4. Generate a report showing RAG performance

## ✅ Testing Your Setup

### Backend Health Check
```bash
# Start backend and verify
curl http://localhost:8000/api/v1/health
# Should return: {"status": "healthy", "version": "1.0.0"}

# Check API documentation
open http://localhost:8000/docs
```

### Desktop Client Test
```bash
# Test imports (from project root)
python -c "
from src.config_manager import ConfigManager
from src.gemini_assistant import GeminiAssistant
from src.ui.main_window import MainWindow
print('✅ All desktop imports successful')
"
```

### Web Client Test
```bash
cd web-client
npm run dev
# Visit http://localhost:3000
```

## 🗂️ Project Structure

```
├── backend/                    # FastAPI backend service
│   ├── app/
│   │   ├── api/               # API endpoints (chat, health, knowledge)
│   │   │   └── endpoints/     # RAG and chat_rag endpoints
│   │   ├── core/              # Core configuration and database
│   │   ├── database/          # Database utilities
│   │   ├── models/            # Pydantic models (chat, RAG)
│   │   ├── services/          # Business logic (Gemini, RAG, GCS)
│   │   ├── utils/             # Utility modules
│   │   └── main.py            # FastAPI application entry
│   ├── alembic/               # Database migrations
│   ├── data/                  # Data storage
│   ├── tests/                 # Test suite
│   ├── uploads/               # File uploads
│   └── requirements.txt       # Backend dependencies (147 packages)
├── src/                       # Desktop application (PyQt6)
│   ├── ui/                    # UI components
│   │   ├── main_window.py     # Main application window
│   │   ├── chat_display.py    # Chat interface
│   │   └── ...                # Other UI components
│   ├── services/              # Desktop services
│   ├── utils/                 # Utility modules
│   ├── config_manager.py      # Configuration management
│   ├── gemini_assistant.py    # AI assistant logic
│   └── main.py                # Desktop app entry point
├── web-client/                # Next.js web application
│   ├── src/
│   │   ├── app/               # App router pages
│   │   ├── components/        # React components
│   │   │   └── Chat/          # Chat interface components
│   │   ├── services/          # API & WebSocket services
│   │   └── types/             # TypeScript definitions
│   ├── node_modules/          # Dependencies (860 packages)
│   └── package.json
├── V2/PyQt6_Gemini_App/       # Legacy desktop structure
│   └── backend/               # Old backend service
├── config/                    # Configuration files
├── logs/                      # Application logs
├── venv_test_py311/          # Python 3.11 testing environment
├── TESTING_LOG.md            # Comprehensive testing documentation
├── CLAUDE_TASKS.md           # Task management and progress
├── start_full_system.py      # Full system startup script
├── requirements.txt          # Root dependencies
└── README.md                 # This file
```

## 🔧 Configuration

### Backend Configuration (backend/.env)
```env
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Database (SQLite for development, PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./lostmindai.db
# DATABASE_URL=postgresql://user:pass@localhost/lostmindai  # For production
REDIS_URL=redis://localhost:6379

# API Settings
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key
DEBUG=true  # Enables mock authentication
```

### Desktop Configuration (config/config.json)
```json
{
  "models": {
    "default_model": "gemini-2.0-flash",
    "temperature": 0.7,
    "max_tokens": 8192
  },
  "ui": {
    "theme": "auto",
    "show_thinking": true
  },
  "backend": {
    "api_url": "http://localhost:8000",
    "websocket_url": "ws://localhost:8000/ws"
  }
}
```

## 🔍 API Endpoints

### Chat Management
- `POST /api/v1/chat/sessions` - Create chat session
- `GET /api/v1/chat/sessions` - List sessions
- `POST /api/v1/chat/sessions/{id}/messages` - Send message

### Knowledge Bases
- `POST /api/v1/rag/knowledge-bases` - Create knowledge base
- `GET /api/v1/rag/knowledge-bases` - List knowledge bases
- `POST /api/v1/rag/knowledge-bases/{id}/documents` - Add document
- `POST /api/v1/rag/knowledge-bases/{id}/query` - RAG query

### RAG Chat
- `POST /api/v1/chat/sessions/{id}/rag` - Chat with RAG context
- `POST /api/v1/chat/sessions/{id}/enable-rag` - Enable RAG for session

### WebSocket
- `/ws` - Real-time chat communication

## 🎯 Roadmap

### Phase 1: ✅ Completed
- [x] FastAPI backend with OpenAPI (38 API routes)
- [x] Gemini integration with unified SDK
- [x] Vector store with PostgreSQL/SQLite support
- [x] Desktop client refactoring (PyQt6)
- [x] Next.js web client foundation
- [x] RAG implementation with knowledge management
- [x] **Comprehensive testing & bug fixes** (13 critical issues resolved)

### Phase 2: 🚧 In Progress  
- [ ] Production deployment setup (Docker + Nginx)
- [ ] Advanced AI features (knowledge graphs, agentic capabilities)
- [ ] Web client build optimizations
- [ ] Advanced RAG features (multi-modal, hybrid search)

### Phase 3: 📋 Planned
- [ ] lostmindai.com integration with SSL
- [ ] User authentication and billing system
- [ ] Advanced analytics and monitoring
- [ ] Mobile application
- [ ] Plugin system and integrations

### 🔥 Current Status
**All core platform functionality is production-ready!**
- Backend service: **Fully operational**
- Desktop client: **Fully functional**  
- Testing framework: **Complete**
- Ready for deployment phase

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software owned by LostMindAI. All rights reserved.

## 🆘 Support

- **Issues**: Report bugs on GitHub Issues
- **Documentation**: Visit our [documentation site](https://docs.lostmindai.com)
- **Community**: Join our [Discord server](https://discord.gg/lostmindai)
- **Email**: support@lostmindai.com

## 🎉 Acknowledgments

- Google Cloud and Vertex AI for powerful AI capabilities
- The open-source community for excellent tools and libraries
- FastAPI, Next.js, and PyQt6 teams for incredible frameworks

---

**Built with ❤️ by the LostMindAI Team**

*Empowering intelligent conversations through advanced AI technology*