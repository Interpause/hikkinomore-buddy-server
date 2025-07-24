import { Api, type ChatRequest, type ConversationMessage } from '../lib'
import './style.css'

// Types for local storage
interface ChatSession {
  id: string
  title: string
  preset: string
  created_at: string
}

interface AppState {
  userId: string
  apiUrl: string
  sessions: ChatSession[]
  currentSessionId: string | null
}

class ChatApp {
  private api: Api
  private state: AppState
  private currentStreamController: AbortController | null = null

  constructor() {
    this.state = this.loadState()
    this.api = new Api(this.state.apiUrl, 30000)
    this.init()
  }

  private loadState(): AppState {
    const saved = localStorage.getItem('chatAppState')
    if (saved) {
      return JSON.parse(saved)
    }

    // Default state
    return {
      userId: this.generateId(),
      apiUrl: 'http://localhost:3000',
      sessions: [],
      currentSessionId: null,
    }
  }

  private saveState() {
    localStorage.setItem('chatAppState', JSON.stringify(this.state))
  }

  private generateId(): string {
    return Math.random().toString(36).substring(2) + Date.now().toString(36)
  }

  private async init() {
    this.renderApp()
    this.setupEventListeners()

    // Load current session if exists
    if (this.state.currentSessionId) {
      await this.loadChatHistory(this.state.currentSessionId)
    }
  }

  private renderApp() {
    document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
      <div class="chat-app">
        <header class="chat-header">
          <div class="user-controls">
            <label>User ID: 
              <input type="text" id="userId" value="${this.state.userId}" />
            </label>
            <label>API URL: 
              <input type="text" id="apiUrl" value="${this.state.apiUrl}" placeholder="http://localhost:3000" />
            </label>
          </div>
          <div class="header-buttons">
            <button id="deleteChatBtn" class="delete-chat-btn" ${!this.state.currentSessionId ? 'disabled' : ''}>Delete Chat</button>
            <button id="factoryResetBtn" class="factory-reset-btn">Factory Reset</button>
            <button id="newChatBtn" class="new-chat-btn">New Chat</button>
          </div>
        </header>
        
        <div class="chat-layout">
          <aside class="chat-sidebar">
            <h3>Chat Sessions</h3>
            <div id="sessionsList" class="sessions-list">
              ${this.renderSessionsList()}
            </div>
          </aside>
          
          <main class="chat-main">
            <div id="chatMessages" class="chat-messages">
              ${this.state.sessions.length === 0 ? '<div class="empty-state">Press "New Chat" to start a conversation</div>' : ''}
            </div>
            <div class="chat-input-container">
              <input type="text" id="messageInput" placeholder="Type your message..." />
              <button id="sendBtn">Send</button>
            </div>
          </main>
        </div>
      </div>
      
      <!-- Modal for new chat -->
      <div id="newChatModal" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Create New Chat</h3>
            <button class="modal-close" id="modalClose">&times;</button>
          </div>
          <div class="modal-body">
            <label>
              Chat Title:
              <input type="text" id="chatTitleInput" placeholder="Enter chat title..." />
            </label>
            <label>
              Bot Preset:
              <select id="presetSelect">
                <option value="GENERAL_BOT">General Bot</option>
                <option value="NERVY_BOT">Nervy Bot</option>
                <option value="AVOI_BOT">Avoidant Bot</option>
                <option value="ENTHU_BOT">Enthusiastic Bot</option>
                <option value="ISO_BOT">Isolated Bot</option>
              </select>
            </label>
          </div>
          <div class="modal-footer">
            <button id="modalCancel" class="btn-secondary">Cancel</button>
            <button id="modalCreate" class="btn-primary">Create Chat</button>
          </div>
        </div>
      </div>
      
      <!-- Toast container -->
      <div id="toastContainer" class="toast-container"></div>
    `
  }

  private renderSessionsList(): string {
    return this.state.sessions
      .map(
        (session) => `
      <div class="session-item ${session.id === this.state.currentSessionId ? 'active' : ''}" 
           data-session-id="${session.id}">
        <div class="session-title">${session.title}</div>
        <div class="session-meta">${session.preset} • ${new Date(session.created_at).toLocaleDateString()}</div>
      </div>
    `,
      )
      .join('')
  }

  private setupEventListeners() {
    // User ID input
    const userIdInput = document.getElementById('userId') as HTMLInputElement
    userIdInput.addEventListener('change', (e) => {
      this.state.userId = (e.target as HTMLInputElement).value
      this.saveState()
    })

    // API URL input
    const apiUrlInput = document.getElementById('apiUrl') as HTMLInputElement
    apiUrlInput.addEventListener('change', (e) => {
      this.state.apiUrl = (e.target as HTMLInputElement).value
      this.api = new Api(this.state.apiUrl, 30000)
      this.saveState()
    })

    // New chat button
    document.getElementById('newChatBtn')!.addEventListener('click', () => {
      this.showNewChatModal()
    })

    // Delete chat button
    document.getElementById('deleteChatBtn')!.addEventListener('click', () => {
      this.deleteCurrentChat()
    })

    // Factory reset button
    document
      .getElementById('factoryResetBtn')!
      .addEventListener('click', () => {
        this.showFactoryResetConfirmation()
      })

    // Modal events
    const modal = document.getElementById('newChatModal')!
    const modalClose = document.getElementById('modalClose')!
    const modalCancel = document.getElementById('modalCancel')!
    const modalCreate = document.getElementById('modalCreate')!

    modalClose.addEventListener('click', () => this.hideNewChatModal())
    modalCancel.addEventListener('click', () => this.hideNewChatModal())
    modalCreate.addEventListener('click', () =>
      this.createNewSessionFromModal(),
    )

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.hideNewChatModal()
    })

    // Send message
    const sendBtn = document.getElementById('sendBtn')!
    const messageInput = document.getElementById(
      'messageInput',
    ) as HTMLInputElement

    sendBtn.addEventListener('click', () => this.sendMessage())
    messageInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendMessage()
    })

    // Session selection
    document.getElementById('sessionsList')!.addEventListener('click', (e) => {
      const sessionItem = (e.target as HTMLElement).closest('.session-item')
      if (sessionItem) {
        const sessionId = sessionItem.getAttribute('data-session-id')!
        this.switchToSession(sessionId)
      }
    })
  }

  private showNewChatModal() {
    const modal = document.getElementById('newChatModal')!
    const titleInput = document.getElementById(
      'chatTitleInput',
    ) as HTMLInputElement
    const presetSelect = document.getElementById(
      'presetSelect',
    ) as HTMLSelectElement

    // Reset form
    titleInput.value = ''
    presetSelect.value = 'GENERAL_BOT'

    modal.style.display = 'flex'
    titleInput.focus()
  }

  private hideNewChatModal() {
    const modal = document.getElementById('newChatModal')!
    modal.style.display = 'none'
  }

  private async createNewSessionFromModal() {
    const titleInput = document.getElementById(
      'chatTitleInput',
    ) as HTMLInputElement
    const presetSelect = document.getElementById(
      'presetSelect',
    ) as HTMLSelectElement

    const title = titleInput.value.trim()
    if (!title) {
      this.showToast('Please enter a chat title', 'error')
      return
    }

    const session: ChatSession = {
      id: this.generateId(),
      title,
      preset: presetSelect.value,
      created_at: new Date().toISOString(),
    }

    this.state.sessions.unshift(session)
    this.state.currentSessionId = session.id
    this.saveState()

    this.hideNewChatModal()
    this.renderApp()
    this.setupEventListeners()
    await this.loadChatHistory(session.id)

    this.showToast(`Chat "${title}" created successfully`, 'success')
  }

  private showToast(
    message: string,
    type: 'success' | 'error' | 'info' = 'info',
  ) {
    const container = document.getElementById('toastContainer')!
    const toast = document.createElement('div')
    toast.className = `toast toast-${type}`
    toast.textContent = message

    container.appendChild(toast)

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10)

    // Auto remove after 3 seconds
    setTimeout(() => {
      toast.classList.remove('show')
      setTimeout(() => {
        if (container.contains(toast)) {
          container.removeChild(toast)
        }
      }, 300)
    }, 3000)
  }

  private deleteCurrentChat() {
    if (!this.state.currentSessionId) return

    const currentSession = this.state.sessions.find(
      (s) => s.id === this.state.currentSessionId,
    )
    if (!currentSession) return

    if (
      confirm(
        `Are you sure you want to delete the chat "${currentSession.title}"?`,
      )
    ) {
      // Remove the session from the list
      this.state.sessions = this.state.sessions.filter(
        (s) => s.id !== this.state.currentSessionId,
      )

      // Set current session to the first available session, or null if none
      this.state.currentSessionId =
        this.state.sessions.length > 0 ? this.state.sessions[0].id : null

      this.saveState()
      this.renderApp()
      this.setupEventListeners()

      // Load history for new current session or clear messages
      if (this.state.currentSessionId) {
        this.loadChatHistory(this.state.currentSessionId)
      } else {
        document.getElementById('chatMessages')!.innerHTML =
          '<div class="empty-state">Press "New Chat" to start a conversation</div>'
      }

      this.showToast(`Chat "${currentSession.title}" deleted`, 'success')
    }
  }

  private showFactoryResetConfirmation() {
    if (
      confirm(
        'Are you sure you want to factory reset the app? This will:\n\n• Delete all chat sessions\n• Reset API URL to default\n• Generate a new User ID\n\nThis action cannot be undone.',
      )
    ) {
      this.factoryReset()
    }
  }

  private factoryReset() {
    // Clear localStorage
    localStorage.removeItem('chatAppState')

    // Reset state to defaults
    this.state = {
      userId: this.generateId(),
      apiUrl: 'http://localhost:3000',
      sessions: [],
      currentSessionId: null,
    }

    // Recreate API client with default URL
    this.api = new Api(this.state.apiUrl, 30000)

    // Save the new state
    this.saveState()

    // Re-render the app
    this.renderApp()
    this.setupEventListeners()

    this.showToast('App has been factory reset', 'success')
  }

  private async switchToSession(sessionId: string) {
    this.state.currentSessionId = sessionId
    this.saveState()

    // Update UI
    document.querySelectorAll('.session-item').forEach((item) => {
      item.classList.toggle(
        'active',
        item.getAttribute('data-session-id') === sessionId,
      )
    })

    await this.loadChatHistory(sessionId)
  }

  private async loadChatHistory(sessionId: string) {
    try {
      const history = await this.api.getChatHistory(sessionId)
      this.renderMessages(history)
    } catch (error) {
      console.error('Failed to load chat history:', error)
      // Start with empty history for new sessions
      this.renderMessages([])
    }
  }

  private renderMessages(messages: ConversationMessage[]) {
    const container = document.getElementById('chatMessages')!
    container.innerHTML = messages
      .map((msg) => this.renderMessage(msg))
      .join('')
    container.scrollTop = container.scrollHeight
  }

  private renderMessage(message: ConversationMessage): string {
    const time =
      message.timestamp ?
        new Date(message.timestamp).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        })
      : ''
    const isUser = message.role === 'user'
    const isSystem = message.role === 'system'

    if (isSystem) {
      return `<div class="message system-message">${message.content}</div>`
    }

    return `
      <div class="message ${isUser ? 'user-message' : 'assistant-message'}">
        <div class="message-bubble">
          <div class="message-content">${message.content}</div>
          ${time ? `<div class="message-time">${time}</div>` : ''}
        </div>
      </div>
    `
  }

  private async sendMessage() {
    const input = document.getElementById('messageInput') as HTMLInputElement
    const message = input.value.trim()
    if (!message || !this.state.currentSessionId) return

    const currentSession = this.state.sessions.find(
      (s) => s.id === this.state.currentSessionId,
    )
    if (!currentSession) return

    // Clear input and add user message to UI
    input.value = ''
    this.addMessageToUI({
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    })

    // Add assistant message placeholder
    const assistantMessageId = 'assistant-' + Date.now()
    this.addMessageToUI(
      {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      },
      assistantMessageId,
    )

    try {
      // Cancel any existing stream
      if (this.currentStreamController) {
        this.currentStreamController.abort()
      }
      this.currentStreamController = new AbortController()

      const request: ChatRequest = {
        msg: message,
        session_id: this.state.currentSessionId,
        user_id: this.state.userId,
        preset: currentSession.preset as any,
      }

      let fullResponse = ''
      for await (const update of this.api.streamChatResponse(request)) {
        fullResponse = update
        this.updateMessageContent(assistantMessageId, fullResponse)
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      this.showToast(
        'Failed to send message: ' + (error as Error).message,
        'error',
      )
      this.updateMessageContent(
        assistantMessageId,
        'Error: Failed to get response',
      )
    } finally {
      this.currentStreamController = null
    }
  }

  private addMessageToUI(message: ConversationMessage, id?: string) {
    const container = document.getElementById('chatMessages')!
    const messageHtml = this.renderMessage(message)
    const div = document.createElement('div')
    div.innerHTML = messageHtml

    const messageElement = div.firstElementChild! as HTMLElement
    if (id) {
      messageElement.id = id
    }

    container.appendChild(messageElement)
    container.scrollTop = container.scrollHeight
  }

  private updateMessageContent(messageId: string, content: string) {
    const messageElement = document.getElementById(messageId)
    if (messageElement) {
      const contentElement = messageElement.querySelector('.message-content')
      if (contentElement) {
        contentElement.textContent = content
      }
    }
  }
}

// Initialize the app
new ChatApp()
