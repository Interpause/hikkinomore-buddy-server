# Hikki-no-more Buddy SDK

A TypeScript/JavaScript SDK for interacting with the Hikkinomore Buddy chat API. This SDK provides both low-level API access and high-level chat management capabilities.

## Features

- 🚀 **Simple API**: Easy-to-use high-level `ChatManager` and `Chat` classes
- 📡 **Streaming Support**: Real-time chat responses with async generators
- 🎯 **Type Safety**: Full TypeScript support with comprehensive type definitions
- 💾 **Session Management**: Built-in session handling and caching
- 🎨 **Multiple Presets**: Support for various bot personalities
- ⚡ **Timeout Handling**: Configurable request timeouts with proper error handling

## Installation

```bash
npm install @interpause/hikkinomore-buddy-sdk
```

## Quick Start

### High-Level API (Recommended)

```typescript
import { ChatManager } from '@interpause/hikkinomore-buddy-sdk'

// Initialize the chat manager
const chatManager = new ChatManager('user123', 'http://localhost:3000')

// Get a chat session
const chat = chatManager.getChat('session456', 'GENERAL_BOT')

// Send a message and get streaming response
for await (const update of chat.chatStream('Hello, how are you?')) {
  console.log(update) // Prints progressive response
}

// Or get the complete response
const response = await chat.chat('What is the weather like?')
console.log(response)

// Get conversation history
const history = await chat.getHistory()
console.log(history)
```

### Low-Level API

```typescript
import { Api } from '@interpause/hikkinomore-buddy-sdk'

// Initialize the API client
const api = new Api('http://localhost:3000', 30000)

// Send a chat request
const request = {
  msg: 'Hello, world!',
  session_id: 'session456',
  user_id: 'user123',
  preset: 'GENERAL_BOT' as const
}

// Stream the response
for await (const update of api.streamChatResponse(request)) {
  console.log(update)
}

// Get chat history
const history = await api.getChatHistory('session456')
console.log(history)
```

## API Reference

### ChatManager

The main entry point for managing chat sessions.

#### Constructor
- `new ChatManager(userId: string, url: string, timeout?: number)`

#### Methods
- `getChat(sessionId?: string, preset?: ValidPreset): Chat` - Get or create a chat session
- `listSessions(): Promise<SessionInfo[]>` - List all sessions (TODO: backend support needed)
- `deleteSession(sessionId: string): Promise<void>` - Delete a session (TODO: backend support needed)

### Chat

Represents an individual chat session.

#### Methods
- `chat(message: string): Promise<string>` - Send message and get complete response
- `chatStream(message: string): AsyncGenerator<string>` - Send message and stream response
- `getHistory(): Promise<ConversationMessage[]>` - Get conversation history
- `clearHistory(): Promise<void>` - Clear session history (TODO: backend support needed)

#### Properties
- `sessionId: string` - The session identifier
- `preset: ValidPreset` - The bot personality preset
- `sessionInfo: SessionInfo` - Basic session information

### Api

Low-level API client for direct HTTP requests.

#### Constructor
- `new Api(url: string, timeout: number)`

#### Methods
- `streamChatResponse(req: ChatRequest): AsyncGenerator<string>` - Stream chat response
- `getChatResponse(req: ChatRequest): Promise<string>` - Get complete chat response
- `getChatHistory(sessionId: string): Promise<ConversationMessage[]>` - Get chat history

## Bot Presets

The SDK supports multiple bot personalities:

- `GENERAL_BOT` - General-purpose conversational bot
- `NERVY_BOT` - Nervous and anxious personality
- `AVOI_BOT` - Avoidant and withdrawn personality  
- `ENTHU_BOT` - Enthusiastic and energetic personality
- `ISO_BOT` - Isolated and introspective personality

## Types

### ConversationMessage
```typescript
interface ConversationMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
  timestamp?: string // ISO timestamp string
}
```

### ChatRequest
```typescript
interface ChatRequest {
  msg: string | null
  session_id: string
  user_id: string
  preset: ValidPreset
}
```

### SessionInfo
```typescript
interface SessionInfo {
  id: string
  preset: string
  created_at: string
}
```

## Error Handling

The SDK provides comprehensive error handling:

```typescript
try {
  const response = await chat.chat('Hello!')
  console.log(response)
} catch (error) {
  if (error.message.includes('timed out')) {
    console.log('Request timed out')
  } else if (error.message.includes('HTTP error')) {
    console.log('Server error')
  } else {
    console.log('Unknown error:', error.message)
  }
}
```

## Development

### Building the SDK

```bash
npm run build
```

### Generating Documentation

```bash
npm run docs
```

### Running the Demo

```bash
npm run dev
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This SDK is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
