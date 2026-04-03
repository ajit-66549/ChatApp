export type MessageType = 'message' | 'system' | 'error' | 'pong' | 'room_created' | 'room_joined' | 'room_left'

export interface ChatMessage {
  type: MessageType
  text?: string
  client_id?: string
  room_pin?: string
  online_count?: number
  error?: string
}

export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'