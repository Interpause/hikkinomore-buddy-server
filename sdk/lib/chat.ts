import { Api } from './api'
import type {
  ChatRequest,
  ConversationMessage,
  SessionInfo,
  ValidPreset,
} from './types'
import { VALID_PRESETS } from './types'

/**
 * Represents an individual chat session with a specific bot personality.
 *
 * The Chat class provides a high-level interface for interacting with a single chat session.
 * It handles session-specific configuration (like bot preset) and provides convenient methods
 * for sending messages, streaming responses, and managing conversation history.
 *
 * Chat instances are typically created and managed by a {@link ChatManager} rather than
 * instantiated directly.
 *
 * @example
 * ```typescript
 * // Usually obtained from ChatManager
 * const chatManager = new ChatManager('user123', 'http://localhost:3000');
 * const chat = chatManager.getChat('session456', 'ENTHU_BOT');
 *
 * // Send a message and get complete response
 * const response = await chat.chat('Hello!');
 * console.log(response);
 *
 * // Stream the response in real-time
 * for await (const update of chat.chatStream('Tell me a joke')) {
 *   console.log(update);
 * }
 * ```
 *
 * @public
 */
export class Chat {
  /** @internal */
  private manager: ChatManager

  /** The unique identifier for this chat session. */
  readonly sessionId: string

  /** @internal */
  private _preset: ValidPreset

  /**
   * @internal
   * Creates a new Chat instance. Use {@link ChatManager.getChat} instead of calling this directly.
   */
  constructor(manager: ChatManager, sessionId: string, preset: ValidPreset) {
    this.manager = manager
    this.sessionId = sessionId
    this._preset = preset
  }

  /**
   * Sends a message and waits for the complete response.
   *
   * This method sends a message to the bot and waits for the entire response to be generated
   * before returning it. For better user experience with longer responses, consider using
   * {@link chatStream} to display the response as it's being generated.
   *
   * @param message - The message to send to the bot
   * @returns Promise that resolves to the complete bot response
   * @throws {Error} When the request fails or times out
   *
   * @example
   * ```typescript
   * const response = await chat.chat('What is the capital of France?');
   * console.log(response); // "The capital of France is Paris."
   * ```
   *
   * @public
   */
  async chat(message: string): Promise<string> {
    const request: ChatRequest = {
      msg: message,
      session_id: this.sessionId,
      user_id: this.manager.userId,
      preset: this._preset,
    }

    return await this.manager.api.getChatResponse(request)
  }

  /**
   * Sends a message and streams the response in real-time.
   *
   * This method returns an async generator that yields progressive updates of the bot's response
   * as it's being generated. Each yielded value contains the complete response text up to that point.
   *
   * This provides a better user experience for longer responses, allowing you to display
   * the text as it's being written rather than waiting for the complete response.
   *
   * @param message - The message to send to the bot
   * @yields The latest complete response text as each chunk is received
   * @throws {Error} When the request fails or times out
   *
   * @example
   * ```typescript
   * console.log('Bot is typing...');
   * for await (const update of chat.chatStream('Write a short poem')) {
   *   // Clear previous line and show current progress
   *   process.stdout.write('\r' + update);
   * }
   * console.log(); // New line when complete
   * ```
   *
   * @public
   */
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

  /**
   * Retrieves the conversation history for this session.
   *
   * Returns all messages (system, user, and assistant) that have been exchanged
   * within this chat session, ordered chronologically.
   *
   * @returns Promise that resolves to the conversation history
   * @throws {Error} When the request fails or the session is not found
   *
   * @example
   * ```typescript
   * const history = await chat.getHistory();
   * history.forEach(msg => {
   *   console.log(`${msg.role}: ${msg.content}`);
   * });
   * ```
   *
   * @public
   */
  async getHistory(): Promise<ConversationMessage[]> {
    return await this.manager.api.getChatHistory(this.sessionId)
  }

  /**
   * Gets the current bot personality preset for this session.
   *
   * @returns The current preset identifier
   *
   * @example
   * ```typescript
   * console.log(`Current preset: ${chat.preset}`); // "ENTHU_BOT"
   * ```
   *
   * @public
   */
  get preset(): ValidPreset {
    return this._preset
  }

  /**
   * Gets basic information about this chat session.
   *
   * @returns Session metadata including ID, preset, and creation timestamp
   *
   * @example
   * ```typescript
   * const info = chat.sessionInfo;
   * console.log(`Session ${info.id} created at ${info.created_at}`);
   * ```
   *
   * @public
   */
  get sessionInfo(): SessionInfo {
    return {
      id: this.sessionId,
      preset: this._preset,
      created_at: new Date().toISOString(), // Placeholder since backend doesn't provide this yet
    }
  }

  /**
   * Clears the conversation history for this session.
   *
   * @throws {Error} Always throws - backend support not yet implemented
   * @todo Implement backend endpoint for clearing session history
   *
   * @example
   * ```typescript
   * try {
   *   await chat.clearHistory();
   * } catch (error) {
   *   console.log('Clear history not yet supported');
   * }
   * ```
   *
   * @public
   */
  async clearHistory(): Promise<void> {
    throw new Error('clearHistory not yet implemented - backend support needed')
  }

  /**
   * Deletes a specific message from the conversation.
   *
   * @param _messageId - The ID of the message to delete (currently unused)
   * @throws {Error} Always throws - backend support not yet implemented
   * @todo Implement backend endpoint for deleting specific messages
   *
   * @public
   */
  async deleteMessage(_messageId: string): Promise<void> {
    throw new Error(
      'deleteMessage not yet implemented - backend support needed',
    )
  }

  /**
   * Changes the bot personality preset for this session.
   *
   * **Warning**: This currently only updates the preset locally. Backend persistence
   * is not yet implemented, so the preset change won't survive if the session is
   * recreated or if the server restarts.
   *
   * @param preset - The new preset to use
   * @throws {Error} When an invalid preset is provided
   * @todo Implement backend endpoint for updating session preset
   *
   * @example
   * ```typescript
   * chat.preset = 'NERVY_BOT';
   * console.log('Preset changed to nervous personality');
   * ```
   *
   * @public
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

/**
 * High-level manager for chat sessions and API interactions.
 *
 * The ChatManager class provides the main entry point for using the Hikkinomore Buddy SDK.
 * It handles session creation, caching, and provides a clean interface for managing
 * multiple chat sessions for a user.
 *
 * @example
 * ```typescript
 * const chatManager = new ChatManager('user123', 'http://localhost:3000');
 *
 * // Create a new session with enthusiastic bot
 * const chat1 = chatManager.getChat(undefined, 'ENTHU_BOT');
 *
 * // Get an existing session (or create if it doesn't exist)
 * const chat2 = chatManager.getChat('session456', 'GENERAL_BOT');
 *
 * // Send messages
 * const response = await chat1.chat('Hello!');
 * console.log(response);
 * ```
 *
 * @public
 */
export class ChatManager {
  /** @internal */
  private _userId: string

  /** The underlying API client used for HTTP requests. */
  readonly api: Api

  /** @internal */
  private chatCache: Map<string, Chat> = new Map()

  /**
   * Creates a new ChatManager instance.
   *
   * @param userId - Unique identifier for the user
   * @param url - Base URL of the Hikkinomore Buddy API server
   * @param timeout - Request timeout in milliseconds (default: 30000)
   *
   * @example
   * ```typescript
   * const manager = new ChatManager('user123', 'http://localhost:3000', 15000);
   * ```
   *
   * @public
   */
  constructor(userId: string, url: string, timeout: number = 30000) {
    this._userId = userId
    this.api = new Api(url, timeout)
  }

  /**
   * Gets the current user ID.
   *
   * @returns The user identifier
   *
   * @public
   */
  get userId(): string {
    return this._userId
  }

  /**
   * Sets a new user ID and clears the session cache.
   *
   * When the user ID changes, all cached Chat instances are cleared since
   * they belong to the previous user.
   *
   * @param userId - The new user identifier
   *
   * @example
   * ```typescript
   * manager.userId = 'newUser456';
   * // All previous chat sessions are now cleared from cache
   * ```
   *
   * @public
   */
  set userId(userId: string) {
    this._userId = userId
    // Clear cache when user changes
    this.chatCache.clear()
  }

  /**
   * Gets or creates a Chat session.
   *
   * This method is the primary way to obtain Chat instances. It handles session creation,
   * caching, and preset validation.
   *
   * **Behavior:**
   * - If no `sessionId` is provided, always creates a new session with a generated ID
   * - If `sessionId` is provided, returns existing cached session or creates a new Chat object for it
   * - Sessions are cached to avoid recreating Chat objects for the same session
   *
   * **Important**: The preset is not persisted by the backend yet. If you retrieve an
   * existing session with a different preset than it was created with, the preset will
   * be changed for that session.
   *
   * @param sessionId - Optional session ID. If not provided, a new session is created
   * @param preset - Bot personality preset to use (default: 'GENERAL_BOT')
   * @returns A Chat instance for the specified or generated session
   * @throws {Error} When an invalid preset is provided
   *
   * @example
   * ```typescript
   * // Create a new session (generates a new session ID)
   * const newChat = manager.getChat();
   *
   * // Create a new session with specific preset
   * const enthusChat = manager.getChat(undefined, 'ENTHU_BOT');
   *
   * // Get an existing session
   * const existingChat = manager.getChat('session_123');
   *
   * // Get/create session with specific preset
   * const nervyChat = manager.getChat('session_456', 'NERVY_BOT');
   * ```
   *
   * @public
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

  /**
   * Lists all chat sessions for the current user.
   *
   * @returns Promise that resolves to an array of session information
   * @throws {Error} Always throws - backend support not yet implemented
   * @todo Implement backend endpoint for listing user sessions
   *
   * @example
   * ```typescript
   * try {
   *   const sessions = await manager.listSessions();
   *   sessions.forEach(session => {
   *     console.log(`Session ${session.id}: ${session.preset}`);
   *   });
   * } catch (error) {
   *   console.log('Session listing not yet supported');
   * }
   * ```
   *
   * @public
   */
  async listSessions(): Promise<SessionInfo[]> {
    throw new Error('listSessions not yet implemented - backend support needed')
  }

  /**
   * Deletes a chat session from both cache and backend.
   *
   * @param sessionId - The ID of the session to delete
   * @throws {Error} Always throws - backend support not yet implemented
   * @todo Implement backend endpoint for deleting sessions
   *
   * @example
   * ```typescript
   * try {
   *   await manager.deleteSession('session_123');
   * } catch (error) {
   *   console.log('Session deletion not yet supported');
   * }
   * ```
   *
   * @public
   */
  async deleteSession(sessionId: string): Promise<void> {
    // Remove from cache if present
    this.chatCache.delete(sessionId)
    throw new Error(
      'deleteSession not yet implemented - backend support needed',
    )
  }

  /**
   * @internal
   * Generates a unique session ID using timestamp and random characters.
   */
  private generateSessionId(): string {
    return Math.random().toString(36).substring(2) + Date.now().toString(36)
  }
}
