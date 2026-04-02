export type MessageType = 'message' | 'system' | 'error' | 'pong'

export interface ChatMessage {
  type: MessageType
  text?: string
  client_id?: string
  online_count?: number
}

export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'