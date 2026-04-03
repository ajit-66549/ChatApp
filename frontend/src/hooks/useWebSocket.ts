import { useEffect, useRef, useState, useCallback } from 'react'
import type { ChatMessage, ConnectionStatus } from '../types/chat'

const WS_URL = 'ws://localhost:8000/ws'
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_ATTEMPTS = 5

export function useWebSocket(clientId: string) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isManuallyClosed = useRef(false)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [reconnectCount, setReconnectCount] = useState(0)
  const [onlineCount, setOnlineCount] = useState(0)

  const connect = useCallback(() => {
    isManuallyClosed.current = false
    const socket = new WebSocket(`${WS_URL}/${clientId}`)
    ws.current = socket

    socket.onopen = () => {
      setStatus('connected')
      reconnectAttempts.current = 0
      setReconnectCount(0)
    }

    socket.onmessage = (event: MessageEvent) => {
      const data: ChatMessage = JSON.parse(event.data)
      if (data.online_count !== undefined) setOnlineCount(data.online_count)
      if (data.type === 'pong') return
      setMessages((prev) => [...prev, data])
    }

    socket.onclose = (event: CloseEvent) => {
      if (isManuallyClosed.current) return
      if (event.code === 4001 || event.code === 4002) {
        setStatus('disconnected')
        return
      }
      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        setStatus('reconnecting')
        reconnectAttempts.current += 1
        setReconnectCount(reconnectAttempts.current)
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
      } else {
        setStatus('disconnected')
      }
    }

    socket.onerror = () => socket.close()
  }, [clientId])

  useEffect(() => {
    connect()
    return () => {
      isManuallyClosed.current = true
      reconnectTimer.current && clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((text: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'message', text }))
    }
  }, [])

  const sendPing = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'ping' }))
    }
  }, [])

  const sendEvent = useCallback((payload: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload))
    }
  }, [])

  return { messages, status, reconnectCount, onlineCount, sendMessage, sendPing, sendEvent }
}