import type { ChatRequest, ConversationMessage } from './types'

/**
 * Low-level HTTP API client for the Hikkinomore Buddy chat service.
 *
 * This class provides direct access to the chat API endpoints with minimal abstraction.
 * For most use cases, consider using the {@link ChatManager} and {@link Chat} classes instead,
 * which provide a higher-level interface with session management and caching.
 *
 * @example
 * ```typescript
 * const api = new Api('http://localhost:3000', 30000);
 *
 * const request: ChatRequest = {
 *   msg: "Hello, world!",
 *   session_id: "session_123",
 *   user_id: "user_456",
 *   preset: "GENERAL_BOT"
 * };
 *
 * // Stream the response
 * for await (const update of api.streamChatResponse(request)) {
 *   console.log(update);
 * }
 * ```
 *
 * @public
 */
export class Api {
  /** The base URL of the API server. */
  url: string

  /** Request timeout in milliseconds. */
  timeout: number

  /**
   * Initializes the API client with the base URL and request timeout.
   *
   * @param url - The base URL of the API server (e.g., 'http://localhost:3000')
   * @param timeout - Timeout in milliseconds for requests. Defaults to 30000 (30 seconds)
   *
   * @example
   * ```typescript
   * const api = new Api('http://localhost:3000', 15000); // 15 second timeout
   * ```
   */
  constructor(url: string, timeout: number) {
    this.url = url
    this.timeout = timeout
  }

  /**
   * Streams chat responses from the `/chat` endpoint in real-time.
   *
   * This method returns an async generator that yields progressive updates of the bot's response.
   * Each yielded value contains the complete response text up to that point, not just the delta.
   *
   * The request is automatically aborted if it exceeds the configured timeout duration.
   *
   * @param req - The chat request parameters
   * @yields The latest complete response text as each chunk is received
   * @throws {Error} When the request times out or encounters an HTTP error
   *
   * @example
   * ```typescript
   * const request: ChatRequest = {
   *   msg: "Tell me a story",
   *   session_id: "story_session",
   *   user_id: "user123",
   *   preset: "ENTHU_BOT"
   * };
   *
   * for await (const update of api.streamChatResponse(request)) {
   *   console.log("Current response:", update);
   *   // Output might be:
   *   // "Once upon a time..."
   *   // "Once upon a time, there was a brave knight..."
   *   // "Once upon a time, there was a brave knight who loved adventures!"
   * }
   * ```
   *
   * @public
   */
  async *streamChatResponse(
    req: ChatRequest,
  ): AsyncGenerator<string, void, unknown> {
    const timeout = this.timeout // In case timeout is changed after instantiation
    const abort = new AbortController()
    const handle = setTimeout(() => abort.abort(), timeout)

    try {
      const resp = await fetch(`${this.url}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(req),
        signal: abort.signal,
      })

      if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`)
      if (!resp.body) throw new Error('Response body is null')

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()

      try {
        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          const update = decoder.decode(value, { stream: true })
          if (update) yield update
        }
      } finally {
        reader.releaseLock()
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        throw new Error(`Request timed out after ${timeout}ms`)
      }
      throw err
    } finally {
      clearTimeout(handle)
    }
  }

  /**
   * Sends a chat request and waits for the complete response.
   *
   * This is a convenience method that internally uses {@link streamChatResponse}
   * but waits for the entire response to be received before returning it.
   *
   * Use this method when you need the full response at once rather than processing
   * it in real-time. For better user experience with longer responses, consider
   * using {@link streamChatResponse} instead.
   *
   * @param req - The chat request parameters
   * @returns Promise that resolves to the complete response text
   * @throws {Error} When the request times out or encounters an HTTP error
   *
   * @example
   * ```typescript
   * const request: ChatRequest = {
   *   msg: "What is 2 + 2?",
   *   session_id: "math_session",
   *   user_id: "student1",
   *   preset: "GENERAL_BOT"
   * };
   *
   * const fullResponse = await api.getChatResponse(request);
   * console.log("Complete answer:", fullResponse);
   * // Output: "2 + 2 equals 4."
   * ```
   *
   * @public
   */
  async getChatResponse(req: ChatRequest): Promise<string> {
    let fullResp = ''
    for await (const update of this.streamChatResponse(req)) fullResp = update
    return fullResp
  }

  /**
   * Retrieves the conversation history for a specific chat session.
   *
   * This method fetches all messages (system, user, and assistant) that have been
   * exchanged within the specified session, ordered chronologically.
   *
   * @param sessionId - The unique identifier of the session to retrieve history for
   * @returns Promise that resolves to an array of conversation messages
   * @throws {Error} When the session is not found, request times out, or encounters an HTTP error
   *
   * @example
   * ```typescript
   * const history = await api.getChatHistory("session_123");
   *
   * history.forEach(message => {
   *   console.log(`${message.role}: ${message.content}`);
   *   if (message.timestamp) {
   *     console.log(`  (sent at ${message.timestamp})`);
   *   }
   * });
   *
   * // Output might be:
   * // user: Hello, how are you?
   * //   (sent at 2025-07-24T10:30:00.000Z)
   * // assistant: I'm doing great, thank you for asking!
   * //   (sent at 2025-07-24T10:30:02.000Z)
   * ```
   *
   * @public
   */
  async getChatHistory(sessionId: string): Promise<ConversationMessage[]> {
    const timeout = this.timeout
    const abort = new AbortController()
    const handle = setTimeout(() => abort.abort(), timeout)

    try {
      const resp = await fetch(`${this.url}/chat/${sessionId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: abort.signal,
      })

      if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`)

      const history: ConversationMessage[] = await resp.json()
      return history
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        throw new Error(`Request timed out after ${timeout}ms`)
      }
      throw err
    } finally {
      clearTimeout(handle)
    }
  }
}
