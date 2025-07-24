export const VALID_PRESETS = [
  'GENERAL_BOT',
  'NERVY_BOT',
  'AVOI_BOT',
  'ENTHU_BOT',
  'ISO_BOT',
] as const
export type ValidPreset = (typeof VALID_PRESETS)[number]

/** Request parameters for /chat */
export interface ChatRequest {
  msg: string | null
  session_id: string
  user_id: string
  // Refer to agents/chat.py for presets
  preset: ValidPreset
}

/** Message structure for chat history */
export interface ConversationMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
  timestamp?: string // ISO timestamp string
}
export interface SessionInfo {
  id: string
  preset: string
  created_at: string
}
