import { useState, useRef, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useHistory } from './hooks/useHistory'
import AuthForm from './components/AuthForm'
import type { ChatMessage, HistoryMessage, ConnectionStatus } from './types/chat'

export default function App() {
  const [token, setToken] = useState<string>(
    () => localStorage.getItem('token') ?? ''
  )
  const [username, setUsername] = useState<string>(
    () => localStorage.getItem('username') ?? ''
  )

  const { messages, status, reconnectCount, onlineCount, sendMessage, sendEvent } = useWebSocket(token)
  const { history, loading, hasMore, loaded, fetchLobbyHistory, fetchRoomHistory, clearHistory } = useHistory(token)

  const [input, setInput] = useState('')
  const [pinInput, setPinInput] = useState('')
  const [currentRoom, setCurrentRoom] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last) return
    if (last.type === 'room_created' || last.type === 'room_joined') {
      setCurrentRoom(last.room_pin ?? null)
      clearHistory()
    }
    if (last.type === 'room_left') {
      setCurrentRoom(null)
      clearHistory()
    }
  }, [messages])

  const handleLogin = (token: string, username: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    setToken(token)
    setUsername(username)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    setToken('')
    setUsername('')
    setCurrentRoom(null)
    clearHistory()
  }

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setInput('')
  }

  const handleReload = () => {
    if (currentRoom) fetchRoomHistory(currentRoom, true)
    else fetchLobbyHistory(true)
  }

  if (!token) return <AuthForm onLogin={handleLogin} />

  return (
    <div>
      <h1>ChatApp — {username}</h1>
      <p>
        Status: {status}
        {reconnectCount > 0 && ` (reconnecting ${reconnectCount}/5)`}
        {' | '}
        {currentRoom ? `Room: ${currentRoom} (${onlineCount} online)` : 'Lobby'}
      </p>

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
        <button onClick={handleReload} disabled={loading || status !== 'connected'}>
          {loading ? 'Loading...' : '↺ Reload History'}
        </button>
        <button onClick={handleLogout}>Logout</button>
      </div>

      <div>
        {loaded && hasMore && (
          <button onClick={() => currentRoom ? fetchRoomHistory(currentRoom) : fetchLobbyHistory()} disabled={loading}>
            {loading ? 'Loading...' : 'Load older messages'}
          </button>
        )}

        {loaded && history.map((msg: HistoryMessage) => (
          <div key={msg.id}>
            <small>{new Date(msg.created_at).toLocaleTimeString()}</small>
            {' '}
            <strong>{msg.user_id === username ? 'you' : msg.user_id}:</strong>
            {' '}
            {msg.text}
            <small> [history]</small>
          </div>
        ))}

        {loaded && history.length > 0 && <div>── live ──</div>}

        {messages.map((msg: ChatMessage, i) => (
          <div key={i}>
            {msg.type === 'room_created' && (
              <div><strong>Room created! PIN: {msg.room_pin}</strong> — share with others</div>
            )}
            {msg.type === 'room_joined' && (
              <em>Joined room {msg.room_pin} ({msg.online_count} online)</em>
            )}
            {msg.type === 'room_left' && <em>You left the room. Back in lobby.</em>}
            {msg.type === 'system' && (
              <em>{msg.text}{msg.online_count !== undefined ? ` (${msg.online_count} online)` : ''}</em>
            )}
            {msg.type === 'error' && <span>Error: {msg.error}</span>}
            {msg.type === 'message' && (
              <span>
                <strong>{msg.client_id === username ? 'you' : msg.client_id}:</strong>{' '}
                {msg.text}
                {msg.room_pin && <small> [room]</small>}
              </span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={currentRoom ? 'Message room...' : 'Message lobby...'}
          disabled={status !== 'connected'}
        />
        <button onClick={handleSend} disabled={status !== 'connected'}>Send</button>
      </div>
    </div>
  )
}