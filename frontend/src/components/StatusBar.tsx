import type { ConnectionStatus } from '../types/chat'

interface StatusBarProps {
  clientId: string
  status: ConnectionStatus
  reconnectCount: number
  onlineCount: number
}

export default function StatusBar({ clientId, status, reconnectCount, onlineCount }: StatusBarProps) {
  return (
    <div>
      <h1>ChatApp</h1>
      <div>
        <span>{clientId} — {status}</span>
        {status === 'reconnecting' && <span> (attempt {reconnectCount}/5)</span>}
        {status === 'connected' && <span> — {onlineCount} online</span>}
      </div>
    </div>
  )
}