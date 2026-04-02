import { useEffect, useRef, useState, useCallback } from 'react'
import type { ChatMessage, ConnectionStatus } from '../types/chat'

const WS_URL = 'ws://localhost:8000/ws'
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_ATTEMPTS = 5

export function useWebSocket(clientId: string) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const messageQueue = useRef<string[]>([])
  const isManuallyClosed = useRef(false)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [reconnectCount, setReconnectCount] = useState(0)

  const connect = useCallback(() => {
    // Prevent duplicate connections
    if (
      ws.current &&
      (ws.current.readyState === WebSocket.OPEN ||
        ws.current.readyState === WebSocket.CONNECTING)
    ) {
      return
    }

    isManuallyClosed.current = false
    setStatus('connecting')

    const socket = new WebSocket(`${WS_URL}/${clientId}`)
    ws.current = socket

    socket.onopen = () => {
      setStatus('connected')
      reconnectAttempts.current = 0
      setReconnectCount(0)

      // Flush queued messages
      while (messageQueue.current.length > 0) {
        const queued = messageQueue.current.shift()
        if (queued) {
          socket.send(queued)
        }
      }
    }

    socket.onmessage = (event: MessageEvent) => {
      const data: ChatMessage = JSON.parse(event.data)
      setMessages((prev) => [...prev, data])
    }

    socket.onclose = () => {
      // Clear current socket reference if this is the same socket
      if (ws.current === socket) {
        ws.current = null
      }

      if (isManuallyClosed.current) return

      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        setStatus('reconnecting')
        reconnectAttempts.current += 1
        setReconnectCount(reconnectAttempts.current)

        reconnectTimer.current = setTimeout(() => {
          connect()
        }, RECONNECT_DELAY_MS)
      } else {
        setStatus('disconnected')
      }
    }

    socket.onerror = () => {
      socket.close()
    }
  }, [clientId])

  useEffect(() => {
    connect()

    return () => {
      isManuallyClosed.current = true

      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }

      ws.current?.close()
      ws.current = null
    }
  }, [connect])

  const sendMessage = useCallback((text: string) => {
    const payload = JSON.stringify({ text })

    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(payload)
    } else {
      // Queue message if not connected yet
      messageQueue.current.push(payload)
    }
  }, [])

  const resetMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, status, reconnectCount, sendMessage, resetMessages }
}