import { useState, useEffect, useRef, useCallback } from "react";
import type { ChatMessage, ConnectionStatus } from "../types/chat";

const WS_URL = "ws://localhost:8000/ws"

export function useWebSocket(clientId: String) {
    const ws = useRef<WebSocket | null>(null)
    const [message, setMessage] = useState<ChatMessage[]>([])
    const [status, setStatus] = useState<ConnectionStatus>("connecting")

    useEffect(() => {
        const socket = new WebSocket(`${WS_URL}/${clientId}`)
        ws.current = socket

        socket.onopen = () => {
            setStatus("connected")
        }

        socket.onmessage = (event: MessageEvent) => {
            const data: ChatMessage = JSON.parse(event.data)
            setMessage((prev) => [...prev, data])
        }

        socket.onclose = () => {
            setStatus("disconnected")
        }

        socket.onerror = (error) => {
            console.log("WebSocket error: ", error)
            setStatus("disconnected")
        }

        return () => {
            socket.close()
        }
    }, [clientId])

    const sendMessage = useCallback((text: String) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({text}))
        }
    }, [])

    return {message, status, sendMessage}
}