import { useState, useRef, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import type { ChatMessage } from './types/chat'

const CLIENT_ID = `user_${Math.random().toString(36).slice(2, 7)}`

export default function App() {
  const { messages, status, reconnectCount, onlineCount, sendMessage, sendEvent } = useWebSocket(CLIENT_ID)
  const [input, setInput] = useState('')
  const [pinInput, setPinInput] = useState('')
  const [currentRoom, setCurrentRoom] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Update room state from incoming events
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last) return
    if (last.type === 'room_created' || last.type === 'room_joined') {
      setCurrentRoom(last.room_pin ?? null)
    }
    if (last.type === 'room_left') {
      setCurrentRoom(null)
    }
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setInput('')
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

      {/* Messages */}
      <div>
        {messages.length === 0 && <p>No messages yet.</p>}
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