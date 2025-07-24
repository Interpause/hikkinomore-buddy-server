/** Request parameters for /chat */
export interface ChatRequest {
  msg: string | null
  session_id: string
  user_id: string
  // Refer to agents/chat.py for presets
  preset: 'GENERAL_BOT' | 'NERVY_BOT' | 'AVOI_BOT' | 'ENTHU_BOT' | 'ISO_BOT'
}

/** Message structure for chat history */
export interface ConversationMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
  timestamp?: string // ISO timestamp string
}
