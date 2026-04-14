import { useState, useRef, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useHistory } from './hooks/useHistory'
import type { ChatMessage, HistoryMessage } from './types/chat'

const CLIENT_ID = `user_${Math.random().toString(36).slice(2, 7)}`

export default function App() {
  const { messages, status, reconnectCount, onlineCount, sendMessage, sendEvent } = useWebSocket(CLIENT_ID)
  const { history, loading, hasMore, loaded, fetchLobbyHistory, fetchRoomHistory, clearHistory } = useHistory()

  const [input, setInput] = useState('')
  const [pinInput, setPinInput] = useState('')
  const [currentRoom, setCurrentRoom] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto scroll on new live message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Track room state from WebSocket events
  // SRP: this effect only handles room state changes
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last) return

    if (last.type === 'room_created' || last.type === 'room_joined') {
      const pin = last.room_pin ?? null
      setCurrentRoom(pin)
      clearHistory()  // clear old history when switching context
    }

    if (last.type === 'room_left') {
      setCurrentRoom(null)
      clearHistory()
    }
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setInput('')
  }

  // SRP: reload button handler has one job — fetch history for current context
  const handleReload = () => {
    if (currentRoom) {
      fetchRoomHistory(currentRoom, true)
    } else {
      fetchLobbyHistory(true)
    }
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

        {/* OCP: Reload button is independent — adding auto-load later won't require changing this */}
        <button onClick={handleReload} disabled={loading || status !== 'connected'}>
          {loading ? 'Loading...' : '↺ Reload History'}
        </button>
      </div>

      {/* Message area */}
      <div>
        {/* Load more — only shown after history is loaded */}
        {loaded && hasMore && (
          <button onClick={handleLoadMore} disabled={loading}>
            {loading ? 'Loading...' : 'Load older messages'}
          </button>
        )}

        {/* History messages — only shown after reload button clicked */}
        {loaded && history.map((msg: HistoryMessage) => (
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
        {loaded && history.length > 0 && (
          <div>── live ──</div>
        )}

        {/* Live messages */}
        {messages.map((msg: ChatMessage, i) => (
          <div key={i}>
            {msg.type === 'room_created' && (
              <div>
                <strong>Room created!</strong> PIN: <strong>{msg.room_pin}</strong> — share with others
              </div>
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