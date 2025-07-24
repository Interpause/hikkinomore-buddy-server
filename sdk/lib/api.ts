import type { ChatRequest, ConversationMessage } from './types'

export class Api {
  url: string
  timeout: number

  /** Initializes the API client with the base URL and request timeout
   *
   * @param {string} url - The base URL of the API server
   * @param {number} timeout - Timeout in milliseconds for requests
   */
  constructor(url: string, timeout: number) {
    this.url = url
    this.timeout = timeout
  }

  /** Async generator that streams chat responses from /chat endpoint
   *
   * @param {ChatRequest} req - The chat request parameters
   * @yields The latest response as a string (not the string delta)
   *
   * @example
   * ```ts
   * const request = {
   *   msg: "Hello, how are you?",
   *   session_id: "abc123",
   *   user_id: "user456",
   *   preset: "GENERAL_BOT"
   * };
   *
   * for await (const update of streamChatResponse(request)) {
   *   console.log(update); // "Start of messa..."
   * }
   * ```
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
   * Utility function to await the final response from the /chat endpoint
   *
   * @param {ChatRequest} req - The chat request parameters
   * @returns {Promise<string>} Promise that resolves to the complete response text
   *
   * @example
   * ```ts
   * const request = {
   *   msg: "Hello, how are you?",
   *   session_id: "abc123",
   *   user_id: "user456",
   *   preset: "GENERAL_BOT"
   * };
   *
   * const fullResponse = await getChatResponse(request);
   * console.log(fullResponse);
   * ```
   */
  async getChatResponse(req: ChatRequest): Promise<string> {
    let fullResp = ''
    for await (const update of this.streamChatResponse(req)) fullResp = update
    return fullResp
  }

  /**
   * Retrieves chat history for a given session
   *
   * @param {string} sessionId - The session ID to retrieve history for
   * @returns {Promise<ConversationMessage[]>} Promise that resolves to the conversation history
   *
   * @example
   * ```ts
   * const history = await getChatHistory("abc123");
   * console.log(history); // Array of ConversationMessage objects
   * ```
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
