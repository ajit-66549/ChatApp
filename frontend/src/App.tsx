import { useState, useRef, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useHistory } from './hooks/useHistory'
import type { ChatMessage, HistoryMessage } from './types/chat'

const CLIENT_ID = `user_${Math.random().toString(36).slice(2, 7)}`

export default function App() {
  const { messages, status, reconnectCount, onlineCount, sendMessage, sendEvent } = useWebSocket(CLIENT_ID)
  const { history, loading, hasMore, fetchLobbyHistory, fetchRoomHistory, clearHistory } = useHistory()

  const [input, setInput] = useState('')
  const [pinInput, setPinInput] = useState('')
  const [currentRoom, setCurrentRoom] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Load lobby history on first connect
  useEffect(() => {
    if (status === 'connected' && !currentRoom) {
      fetchLobbyHistory(true)
    }
  }, [status])

  // Auto scroll to bottom on new live message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Track room state from incoming WebSocket events
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last) return

    if (last.type === 'room_created' || last.type === 'room_joined') {
      const pin = last.room_pin ?? null
      setCurrentRoom(pin)
      if (pin) {
        clearHistory()
        fetchRoomHistory(pin, true)
      }
    }

    if (last.type === 'room_left') {
      setCurrentRoom(null)
      clearHistory()
      fetchLobbyHistory(true)
    }
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setInput('')
  }

  const handleLoadMore = () => {
    if (currentRoom) {
      fetchRoomHistory(currentRoom)
    } else {
      fetchLobbyHistory()
    }
  }

  return (
    <div>
      <h1>ChatApp — {CLIENT_ID}</h1>
      <p>
        Status: {status}
        {reconnectCount > 0 && ` (reconnecting ${reconnectCount}/5)`}
        {' | '}
        {currentRoom ? `Room: ${currentRoom} (${onlineCount} online)` : 'Lobby'}
      </p>

      {/* Room controls */}
      <div>
        {!currentRoom && (
          <>
            <button onClick={() => sendEvent({ type: 'create_room' })} disabled={status !== 'connected'}>
              Create Room
            </button>
            <input
              type="text"
              placeholder="Enter PIN"
              value={pinInput}
              onChange={(e) => setPinInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  sendEvent({ type: 'join_room', pin: pinInput.trim() })
                  setPinInput('')
                }
              }}
            />
            <button
              onClick={() => { sendEvent({ type: 'join_room', pin: pinInput.trim() }); setPinInput('') }}
              disabled={status !== 'connected'}
            >
              Join Room
            </button>
          </>
        )}
        {currentRoom && (
          <button onClick={() => sendEvent({ type: 'leave_room' })} disabled={status !== 'connected'}>
            Leave Room
          </button>
        )}
      </div>

      {/* Message area */}
      <div>

        {/* Load more button */}
        {hasMore && (
          <button onClick={handleLoadMore} disabled={loading}>
            {loading ? 'Loading...' : 'Load older messages'}
          </button>
        )}

        {/* History messages from DB */}
        {history.map((msg: HistoryMessage) => (
          <div key={msg.id}>
            <small>{new Date(msg.created_at).toLocaleTimeString()}</small>
            {' '}
            <strong>{msg.user_id === CLIENT_ID ? 'you' : msg.user_id}:</strong>
            {' '}
            {msg.text}
            <small> [history]</small>
          </div>
        ))}

        {/* Divider between history and live */}
        {history.length > 0 && messages.filter(m => m.type === 'message').length > 0 && (
          <div>── live ──</div>
        )}

        {/* Live messages from WebSocket */}
        {messages.map((msg: ChatMessage, i) => (
          <div key={i}>
            {msg.type === 'room_created' && (
              <strong>Room created! PIN: {msg.room_pin} — share with others</strong>
            )}
            {msg.type === 'room_joined' && (
              <em>Joined room {msg.room_pin} ({msg.online_count} online)</em>
            )}
            {msg.type === 'room_left' && (
              <em>You left the room. Back in lobby.</em>
            )}
            {msg.type === 'system' && (
              <em>{msg.text}{msg.online_count !== undefined ? ` (${msg.online_count} online)` : ''}</em>
            )}
            {msg.type === 'error' && (
              <span>Error: {msg.error}</span>
            )}
            {msg.type === 'message' && (
              <span>
                <strong>{msg.client_id === CLIENT_ID ? 'you' : msg.client_id}:</strong>{' '}
                {msg.text}
                {msg.room_pin && <small> [room]</small>}
              </span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={currentRoom ? 'Message room...' : 'Message lobby...'}
          disabled={status !== 'connected'}
        />
        <button onClick={handleSend} disabled={status !== 'connected'}>
          Send
        </button>
      </div>
    </div>
  )
}