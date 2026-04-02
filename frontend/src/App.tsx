import { useState, useRef, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import type { ChatMessage } from './types/chat'
import StatusBar from './components/StatusBar'

const CLIENT_ID = `user_${Math.random().toString(36).slice(2, 7)}`

export default function App() {
  const { messages, status, reconnectCount, sendMessage } = useWebSocket(CLIENT_ID)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend()
  }

  return (
    <div>
      <StatusBar
        clientId={CLIENT_ID}
        status={status}
        reconnectCount={reconnectCount}
      />

      {(status === 'reconnecting' || status === 'disconnected') && (
        <div>
          {status === 'reconnecting'
            ? `Reconnecting... (attempt ${reconnectCount}/5)`
            : 'Could not reconnect. Please refresh the page.'}
        </div>
      )}

      <div>
        {messages.length === 0 && <p>No messages yet. Say something!</p>}
        {messages.map((msg: ChatMessage, i) => (
          <div key={i}>
            {msg.type === 'system' ? (
              <em>{msg.text}</em>
            ) : (
              <span>
                <strong>{msg.client_id === CLIENT_ID ? 'you' : msg.client_id}:</strong>{' '}
                {msg.text}
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
          onKeyDown={handleKeyDown}
          placeholder={status === 'connected' ? 'Type a message...' : 'Waiting for connection...'}
          disabled={status !== 'connected'}
        />
        <button
          onClick={handleSend}
          disabled={status !== 'connected'}
        >
          Send
        </button>
      </div>
    </div>
  )
}