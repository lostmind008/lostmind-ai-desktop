# LostMindAI Web Client

Modern web interface for the LostMindAI desktop application, built with Next.js 14 and TypeScript.

## Features

- **Real-time Chat Interface**: WebSocket-powered conversations with instant responses
- **File Upload Support**: Attach images, documents, and videos to conversations
- **Session Management**: Create, switch between, and manage multiple chat sessions
- **Thinking Process**: View AI reasoning when enabled
- **Web Search Integration**: Enable search grounding for enhanced responses
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Type-Safe**: Full TypeScript integration with backend API types

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- LostMindAI backend service running

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment (optional):
```bash
cp .env.example .env.local
# Edit .env.local with your backend URL if different from localhost:8000
```

### Development

Start the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

### Building for Production

```bash
npm run build
npm start
```

## Architecture

### Components Structure

- `src/components/Chat/`: Core chat interface components
  - `ChatInterface.tsx`: Main chat container with state management
  - `MessageList.tsx`: Scrollable message history display
  - `MessageBubble.tsx`: Individual message rendering with markdown support
  - `MessageInput.tsx`: Message composition with file upload
  - `SessionSidebar.tsx`: Session management sidebar

### Services

- `src/services/api.ts`: HTTP API client with type-safe endpoints
- `src/services/websocket.ts`: WebSocket service for real-time communication

### Type Definitions

- `src/types/api.ts`: TypeScript interfaces matching backend Pydantic models

## Configuration

The application automatically connects to:
- **Backend API**: `http://localhost:8000/api/v1`
- **WebSocket**: `ws://localhost:8000/ws`

Configure different URLs via Next.js rewrites in `next.config.js`.

## Features in Detail

### Real-time Communication
- WebSocket connection with automatic reconnection
- Typing indicators and connection status
- Optimistic UI updates for immediate feedback

### File Handling
- Drag-and-drop file upload
- Support for images, PDFs, text files, and videos
- File size validation (10MB limit)
- Visual file attachment management

### AI Features
- Toggle thinking process display
- Enable web search grounding
- Markdown rendering with syntax highlighting
- Code block syntax highlighting

### Session Management
- Create multiple chat sessions
- Session persistence across page reloads
- Delete sessions with confirmation
- Session metadata (message count, timestamps)

## Development Notes

- Uses Next.js 14 App Router
- Tailwind CSS for styling with custom LostMindAI branding
- React Hook Form for form management
- React Hot Toast for notifications
- React Markdown for message rendering
- Prism for syntax highlighting

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers with WebSocket support