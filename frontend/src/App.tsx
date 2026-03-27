import { useEffect, useState } from 'react'

type HealthStatus = 'Checking...' | 'Backend connected' | 'Backend unreachable' | 'Error'

export default function App() {
  const [status, setStatus] = useState<HealthStatus>('Checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data: { status: string }) => {
        setStatus(data.status === 'ok' ? 'Backend connected' : 'Error')
      })
      .catch(() => setStatus('Backend unreachable'))
  }, [])

  return (
    <div>
      <h1> ChatApp </h1>
      <div> {status} </div>
    </div>
  )
}