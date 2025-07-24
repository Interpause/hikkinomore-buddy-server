import { Api } from './api'
import type {
  ChatRequest,
  ConversationMessage,
  SessionInfo,
  ValidPreset,
} from './types'
import { VALID_PRESETS } from './types'

export class Chat {
  private manager: ChatManager
  readonly sessionId: string
  private _preset: ValidPreset

  constructor(manager: ChatManager, sessionId: string, preset: ValidPreset) {
    this.manager = manager
    this.sessionId = sessionId
    this._preset = preset
  }

  /** Send a message and get the complete response */
  async chat(message: string): Promise<string> {
    const request: ChatRequest = {
      msg: message,
      session_id: this.sessionId,
      user_id: this.manager.userId,
      preset: this._preset,
    }

    return await this.manager.api.getChatResponse(request)
  }

  /** Send a message and stream the response */
  async *chatStream(message: string): AsyncGenerator<string, void, unknown> {
    const request: ChatRequest = {
      msg: message,
      session_id: this.sessionId,
      user_id: this.manager.userId,
      preset: this._preset,
    }

    for await (const update of this.manager.api.streamChatResponse(request)) {
      yield update
    }
  }

  /** Get the conversation history for this session */
  async getHistory(): Promise<ConversationMessage[]> {
    return await this.manager.api.getChatHistory(this.sessionId)
  }

  /** Get the current preset */
  get preset(): ValidPreset {
    return this._preset
  }

  /** Get basic session information */
  get sessionInfo(): SessionInfo {
    return {
      id: this.sessionId,
      preset: this._preset,
      created_at: new Date().toISOString(), // Placeholder since backend doesn't provide this yet
    }
  }

  /** Clear conversation history for this session
   * TODO: Implement backend endpoint for clearing session history
   */
  async clearHistory(): Promise<void> {
    throw new Error('clearHistory not yet implemented - backend support needed')
  }

  /** Delete a specific message from the conversation
   * TODO: Implement backend endpoint for deleting specific messages
   */
  async deleteMessage(_messageId: string): Promise<void> {
    throw new Error(
      'deleteMessage not yet implemented - backend support needed',
    )
  }

  /** Change the preset for this session
   * TODO: Implement backend endpoint for updating session preset
   */
  set preset(preset: ValidPreset) {
    // TODO: This should make an API call to update the preset in the backend
    // For now, just update locally
    this._preset = preset
    console.warn(
      'setPreset only updates locally - backend persistence not yet implemented',
    )
  }
}

export class ChatManager {
  private _userId: string
  readonly api: Api
  private chatCache: Map<string, Chat> = new Map()

  constructor(userId: string, url: string, timeout: number = 30000) {
    this._userId = userId
    this.api = new Api(url, timeout)
  }

  /** Get the current user ID */
  get userId(): string {
    return this._userId
  }

  /** Set a new user ID */
  set userId(userId: string) {
    this._userId = userId
    // Clear cache when user changes
    this.chatCache.clear()
  }

  /** Get a Chat instance. Always creates a new session if no sessionId provided.
   * If sessionId is provided, returns existing session or creates a new Chat object for it.
   *
   * WARNING: Preset is not persisted by the backend yet, so inadvertently changing the preset
   * when retrieving an existing session will change the initial prompt of that session.
   */
  getChat(sessionId?: string, preset: ValidPreset = 'GENERAL_BOT'): Chat {
    // Validate preset
    if (!VALID_PRESETS.includes(preset)) {
      throw new Error(
        `Invalid preset: ${preset}. Valid presets are: ${VALID_PRESETS.join(', ')}`,
      )
    }

    let actualSessionId: string

    if (sessionId) {
      // Use provided session ID
      actualSessionId = sessionId
    } else {
      // Always create new session when no sessionId provided
      actualSessionId = this.generateSessionId()
    }

    // Check cache first
    if (this.chatCache.has(actualSessionId)) {
      return this.chatCache.get(actualSessionId)!
    }

    // Create new Chat instance
    const chat = new Chat(this, actualSessionId, preset)
    this.chatCache.set(actualSessionId, chat)
    return chat
  }

  /** List all sessions for the current user
   * TODO: Implement backend endpoint for listing user sessions
   */
  async listSessions(): Promise<SessionInfo[]> {
    throw new Error('listSessions not yet implemented - backend support needed')
  }

  /** Delete a session
   * TODO: Implement backend endpoint for deleting sessions
   */
  async deleteSession(sessionId: string): Promise<void> {
    // Remove from cache if present
    this.chatCache.delete(sessionId)
    throw new Error(
      'deleteSession not yet implemented - backend support needed',
    )
  }

  /** Generate a unique session ID */
  private generateSessionId(): string {
    return Math.random().toString(36).substring(2) + Date.now().toString(36)
  }
}
