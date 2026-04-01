import { useState, useEffect, useRef } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import type { ChatMessage } from './types/chat'

const CLIENT_ID = `user_${Math.random().toString(36).slice(2, 7)}`

export default function App() {
  const { message, status, sendMessage } = useWebSocket(CLIENT_ID)
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  // if ui updates, scroll down
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [message])

  // handle the send button
  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    sendMessage(trimmed)
    setInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSend()
  }

    return (
    <div>

      {/* Header */}
      <div>
        <h1>
          ChatApp
        </h1>
        <div>
          <div/>
          <span>
            {CLIENT_ID} — {status}
          </span>
        </div>
      </div>

      {/* Message List */}
      <div>
        {message.length === 0 && (
          <p>
            No messages yet. Say something!
          </p>
        )}

        {message.map((msg: ChatMessage, i) => (
          <div key={i}>
            {msg.type === 'system' ? (
              <span>
                {msg.text}
              </span>
            ) : (
              <>
                <span>
                  {msg.client_id === CLIENT_ID ? 'you' : msg.client_id}: {msg.text}
                </span>
              </>
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
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
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
  