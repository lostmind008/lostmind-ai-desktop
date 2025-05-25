# LostMindAI Desktop Application v2.0 - Enhanced with Backend Service

A modern, enterprise-grade AI chat application that seamlessly switches between direct API and backend service modes, featuring advanced capabilities like RAG (Retrieval-Augmented Generation), intelligent caching, and knowledge management.

## 🚀 Key Features

### 🔄 **Dual-Mode Architecture**
- **Direct Mode**: Traditional direct API calls to Gemini
- **Backend Mode**: API-first architecture with FastAPI backend service
- **Seamless Switching**: Change modes without restarting the application

### 🧠 **Advanced AI Capabilities**
- **RAG Integration**: Context-aware responses using knowledge base
- **Intelligent Caching**: Redis-based response and session caching
- **Thinking Budget Optimization**: Adaptive reasoning depth based on query complexity
- **Multi-modal Support**: Text, images, documents, and videos

### 📚 **Knowledge Management**
- **Vector Database**: ChromaDB integration for semantic search
- **Document Upload**: Support for PDFs, text files, code, and more
- **Semantic Search**: Find relevant information across your knowledge base
- **Source Attribution**: Responses cite their knowledge sources

### ⚡ **Performance & Scalability**
- **WebSocket Support**: Real-time streaming responses
- **Concurrent Processing**: Handle multiple requests efficiently
- **Memory Management**: Intelligent caching with TTL controls
- **Health Monitoring**: Real-time service status and statistics

## 🏗️ Architecture Overview

```
┌─────────────────┐    HTTP/WebSocket    ┌──────────────────┐
│   PyQt6 Desktop │ ←─────────────────→ │   FastAPI        │
│   Application   │                     │   Backend        │
└─────────────────┘                     └──────────────────┘
         │                                        │
         │ Direct API (fallback)                  │
         ↓                                        ↓
┌─────────────────┐                     ┌──────────────────┐
│   Google        │                     │   Redis Cache    │
│   Gemini API    │                     │   ChromaDB       │
└─────────────────┘                     └──────────────────┘
```

## 📦 Installation & Setup

### Prerequisites
- Python 3.9+
- Redis (optional, for caching)
- Google Cloud credentials or Gemini API key

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd PyQT6_Gemini_App_v2

# Install backend dependencies
pip install -r backend/requirements.txt

# Install desktop client dependencies
pip install -r requirements.txt
```

### 2. Configuration

#### Backend Configuration (.env file)
```bash
# Google AI Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
# OR
GEMINI_API_KEY=your-api-key

# Redis Configuration (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Vector Database
VECTOR_DB_PATH=./data/vectors.db

# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=false
```

#### Desktop Configuration (config/config.json)
```json
{
  "backend": {
    "url": "http://localhost:8000"
  },
  "models": [...],
  "ui": {...}
}
```

## 🚀 Quick Start

### Option 1: Full System (Recommended)
Start both backend and desktop client together:

```bash
python start_full_system.py --mode full
```

### Option 2: Individual Components

#### Start Backend Only
```bash
# Using the system launcher
python start_full_system.py --mode backend-only

# Or directly
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Start Desktop Client Only
```bash
# Backend mode (requires running backend)
python start_full_system.py --mode frontend-only --frontend-mode backend

# Direct mode (no backend required)
python start_full_system.py --mode direct
```

### Option 3: Enhanced Desktop Client
```bash
# Start with specific mode
python src/main_enhanced.py --mode backend --backend-url http://localhost:8000

# Or direct mode
python src/main_enhanced.py --mode direct
```

## 🎯 Usage Guide

### Basic Chat
1. **Start the application** using any method above
2. **Select mode** in the Backend tab (if using enhanced client)
3. **Create a session** or load existing one
4. **Start chatting** with Gemini AI

### Knowledge Management
1. **Switch to Backend mode** in the UI
2. **Upload documents** via the Knowledge Base tab
3. **Enable RAG** for context-aware responses
4. **Search knowledge base** to find relevant information

### Advanced Features

#### RAG (Retrieval-Augmented Generation)
```python
# Enable RAG in the UI or use API directly
POST /api/v1/chat/sessions/{session_id}/rag
{
  "message": "What did the document say about AI safety?",
  "use_rag": true,
  "rag_limit": 3,
  "rag_threshold": 0.7
}
```

#### Caching
- **Automatic**: Responses are cached automatically in backend mode
- **Manual**: Clear cache via UI or API endpoints
- **Statistics**: Monitor cache performance in real-time

#### File Uploads
- **Chat files**: Drag & drop into chat for immediate use
- **Knowledge base**: Upload documents for long-term reference
- **Supported formats**: PDF, TXT, MD, DOCX, images, videos

## 🔧 API Reference

### Core Endpoints

#### Chat Management
- `POST /api/v1/chat/sessions` - Create new session
- `GET /api/v1/chat/sessions` - List sessions
- `POST /api/v1/chat/sessions/{id}/messages` - Send message
- `POST /api/v1/chat/sessions/{id}/rag` - RAG-enhanced message

#### Knowledge Management
- `POST /api/v1/knowledge/documents` - Create document
- `POST /api/v1/knowledge/upload` - Upload file
- `POST /api/v1/knowledge/search` - Search knowledge base
- `GET /api/v1/knowledge/stats` - Knowledge statistics

#### Cache Management
- `GET /api/v1/knowledge/cache/stats` - Cache statistics
- `POST /api/v1/knowledge/cache/clear` - Clear cache

### WebSocket
- `WS /ws/{session_id}` - Real-time chat communication

Full API documentation available at: `http://localhost:8000/docs`

## 🔒 Security & Production

### Security Features
- **Input validation** with Pydantic models
- **Rate limiting** and request size limits
- **Error handling** with sanitized error messages
- **CORS configuration** for web clients

### Production Deployment
```bash
# Production backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL and reverse proxy (recommended)
# Use nginx + SSL certificates
```

### Environment Variables
```bash
# Production settings
DEBUG=false
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=["yourdomain.com"]

# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0

# AI Configuration
GOOGLE_CLOUD_PROJECT=production-project-id
```

## 📊 Monitoring & Analytics

### Built-in Monitoring
- **Health checks**: `/api/v1/health` endpoint
- **Service status**: Real-time service monitoring
- **Usage statistics**: Token consumption and cost tracking
- **Performance metrics**: Response times and cache hit rates

### Logging
- **Structured logging** with timestamps and levels
- **Request tracking** with unique IDs
- **Error reporting** with full stack traces
- **Performance monitoring** with timing information

## 🛠️ Development

### Project Structure
```
PyQT6_Gemini_App_v2/
├── backend/                 # FastAPI backend service
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Configuration & dependencies
│   │   ├── models/         # Pydantic models
│   │   └── services/       # Business logic
│   └── requirements.txt
├── src/                    # Desktop application
│   ├── ui/                 # PyQt6 UI components
│   ├── services/           # API client & workers
│   ├── backend_assistant.py
│   ├── assistant_adapter.py
│   └── main_enhanced.py
├── config/                 # Configuration files
├── docs/                   # Documentation
└── start_full_system.py    # System launcher
```

### Adding New Features
1. **Backend**: Add API endpoints in `backend/app/api/`
2. **Desktop**: Extend UI components in `src/ui/`
3. **Integration**: Update `AssistantAdapter` for unified interface

### Testing
```bash
# Backend tests
cd backend
pytest

# Desktop tests (if implemented)
cd src
python -m pytest tests/
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** your changes
4. **Add tests** for new functionality
5. **Submit** a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- **API Documentation**: http://localhost:8000/docs
- **Knowledge Base**: Upload documents via the UI
- **Health Status**: http://localhost:8000/api/v1/health
- **WebSocket Test**: Connect to ws://localhost:8000/ws/test-session

## 🆘 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check dependencies
pip install -r backend/requirements.txt

# Check configuration
cat backend/.env

# Check logs
tail -f logs/lostmind_ai_*.log
```

#### Desktop Client Connection Issues
1. **Verify backend is running**: Visit http://localhost:8000/health
2. **Check firewall settings**: Ensure port 8000 is accessible
3. **Switch to direct mode**: Use fallback direct API mode

#### Knowledge Base Issues
1. **Check vector database**: Ensure ChromaDB is properly initialized
2. **Verify file formats**: Supported formats listed in upload dialog
3. **Check embedding model**: Sentence-transformers installation

### Performance Optimization
- **Redis caching**: Install and configure Redis for better performance
- **Vector database**: Use persistent storage for ChromaDB
- **Concurrent processing**: Adjust worker counts for your hardware

---

## 🎉 What's Next?

Check out the [ENHANCEMENT_ROADMAP.md](ENHANCEMENT_ROADMAP.md) for upcoming features and improvements!

**Happy chatting with LostMindAI! 🚀🤖**