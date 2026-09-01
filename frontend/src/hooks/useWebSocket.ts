import { useEffect, useRef, useState, useCallback } from 'react'
import type { ChatMessage, ConnectionStatus } from '../types/chat'

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = import.meta.env.VITE_WS_URL ?? `${WS_PROTOCOL}//${window.location.host}/ws`
const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_ATTEMPTS = 5

export function useWebSocket(token: string) {
  const ws = useRef<WebSocket | null>(null)
  const connectRef = useRef<() => void>(() => {})
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isManuallyClosed = useRef(false)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [reconnectCount, setReconnectCount] = useState(0)
  const [onlineCount, setOnlineCount] = useState(0)

  const connect = useCallback(() => {
    if (!token) {
      return
    }
    isManuallyClosed.current = false

    // Pass token as query param for WebSocket authentication
    const socket = new WebSocket(`${WS_URL}?token=${token}`)
    ws.current = socket

    socket.onopen = () => {
      setConnectionStatus('connected')
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

      // 4003 = auth failed — don't retry
      if (event.code === 4003) {
        setConnectionStatus('disconnected')
        return
      }

      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        setConnectionStatus('reconnecting')
        reconnectAttempts.current += 1
        setReconnectCount(reconnectAttempts.current)
        reconnectTimer.current = setTimeout(() => connectRef.current(), RECONNECT_DELAY_MS)
      } else {
        setConnectionStatus('disconnected')
      }
    }

    socket.onerror = () => socket.close()
  }, [token])

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  useEffect(() => {
    connect()
    return () => {
      isManuallyClosed.current = true
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
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

  const status: ConnectionStatus = token ? connectionStatus : 'disconnected'

  return { messages, status, reconnectCount, onlineCount, sendMessage, sendPing, sendEvent }
}
