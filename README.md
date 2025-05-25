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
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+ with pgvector
- Redis 6+
- Google Cloud account

### 1. Clone Repository
```bash
git clone https://github.com/lostmind008/lostmindai-platform-v2.git
cd lostmindai-platform-v2
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Google Cloud credentials

# Run database migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Web Client Setup
```bash
cd web-client
npm install

# Start development server
npm run dev
```

### 4. Desktop Client Setup
```bash
cd V2/PyQt6_Gemini_App
pip install -r requirements.txt

# Run desktop app
python src/main.py
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

## 🗂️ Project Structure

```
├── backend/                    # FastAPI backend service
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── core/              # Core configuration
│   │   ├── models/            # Pydantic models
│   │   └── services/          # Business logic
│   ├── alembic/               # Database migrations
│   └── requirements.txt
├── web-client/                # Next.js web application
│   ├── src/
│   │   ├── app/               # App router pages
│   │   ├── components/        # React components
│   │   ├── services/          # API & WebSocket services
│   │   └── types/             # TypeScript definitions
│   └── package.json
├── V2/PyQt6_Gemini_App/       # Desktop application
│   ├── src/
│   │   ├── ui/                # UI components
│   │   └── utils/             # Utility modules
│   └── requirements.txt
└── README.md                  # This file
```

## 🔧 Configuration

### Backend Configuration (backend/.env)
```env
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Database
DATABASE_URL=postgresql://user:pass@localhost/lostmindai
REDIS_URL=redis://localhost:6379

# API Settings
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key
```

### Desktop Configuration (V2/PyQt6_Gemini_App/config/config.json)
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
- [x] FastAPI backend with OpenAPI
- [x] Gemini integration with unified SDK
- [x] Vector store with PostgreSQL
- [x] Desktop client refactoring
- [x] Next.js web client foundation
- [x] RAG implementation with knowledge management

### Phase 2: 🚧 In Progress
- [ ] Advanced RAG features (multi-modal, hybrid search)
- [ ] Production deployment setup
- [ ] Advanced AI features (agents, workflows)

### Phase 3: 📋 Planned
- [ ] lostmindai.com integration
- [ ] User authentication and billing
- [ ] Advanced analytics and monitoring
- [ ] Mobile application
- [ ] Plugin system and integrations

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