export type MessageType = "message" | "system"

export interface ChatMessage {
    type: MessageType,
    client_id?: string,
    text: string
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected"