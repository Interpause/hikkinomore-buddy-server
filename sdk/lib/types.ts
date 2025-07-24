/**
 * Valid bot personality presets supported by the Hikkinomore Buddy API.
 *
 * Each preset configures the bot with a different personality and response style:
 * - `GENERAL_BOT`: General-purpose conversational bot with balanced responses
 * - `NERVY_BOT`: Nervous and anxious personality, tends to be cautious and worried
 * - `AVOI_BOT`: Avoidant and withdrawn personality, prefers minimal interaction
 * - `ENTHU_BOT`: Enthusiastic and energetic personality, very positive and excited
 * - `ISO_BOT`: Isolated and introspective personality, thoughtful and solitary
 *
 * @public
 */
export const VALID_PRESETS = [
  'GENERAL_BOT',
  'NERVY_BOT',
  'AVOI_BOT',
  'ENTHU_BOT',
  'ISO_BOT',
] as const

/**
 * Type representing valid bot personality presets.
 *
 * @see {@link VALID_PRESETS} for the list of available presets and their descriptions.
 * @public
 */
export type ValidPreset = (typeof VALID_PRESETS)[number]

/**
 * Request parameters for the chat API endpoint.
 *
 * This interface defines the structure of requests sent to the `/chat` endpoint
 * for initiating or continuing a conversation.
 *
 * @example
 * ```typescript
 * const request: ChatRequest = {
 *   msg: "Hello, how are you today?",
 *   session_id: "session_123456",
 *   user_id: "user_789",
 *   preset: "GENERAL_BOT"
 * };
 * ```
 *
 * @public
 */
export interface ChatRequest {
  /** The message content to send to the bot. Can be null for initial session setup. */
  msg: string | null

  /** Unique identifier for the chat session. Messages within the same session maintain context. */
  session_id: string

  /** Unique identifier for the user. Used for session management and personalization. */
  user_id: string

  /**
   * Bot personality preset to use for this request.
   * @see {@link ValidPreset} for available options.
   */
  preset: ValidPreset
}

/**
 * Represents a single message in a conversation.
 *
 * This interface defines the structure of messages returned by the chat history API
 * and used throughout the conversation flow.
 *
 * @example
 * ```typescript
 * const message: ConversationMessage = {
 *   role: "assistant",
 *   content: "Hello! How can I help you today?",
 *   timestamp: "2025-07-24T10:30:00.000Z"
 * };
 * ```
 *
 * @public
 */
export interface ConversationMessage {
  /**
   * The role of the message sender.
   * - `system`: Internal system messages (setup, configuration)
   * - `user`: Messages sent by the human user
   * - `assistant`: Messages sent by the AI bot
   */
  role: 'system' | 'user' | 'assistant'

  /** The text content of the message. */
  content: string

  /**
   * Optional ISO 8601 timestamp string indicating when the message was created.
   * Format: YYYY-MM-DDTHH:mm:ss.sssZ
   */
  timestamp?: string
}

/**
 * Basic information about a chat session.
 *
 * This interface provides metadata about a chat session, including its identifier,
 * current preset, and creation timestamp.
 *
 * @example
 * ```typescript
 * const sessionInfo: SessionInfo = {
 *   id: "session_123456",
 *   preset: "GENERAL_BOT",
 *   created_at: "2025-07-24T10:00:00.000Z"
 * };
 * ```
 *
 * @public
 */
export interface SessionInfo {
  /** Unique identifier for the chat session. */
  id: string

  /** The bot personality preset currently active for this session. */
  preset: string

  /** ISO 8601 timestamp string indicating when the session was created. */
  created_at: string
}
