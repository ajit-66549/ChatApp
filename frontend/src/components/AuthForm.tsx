import { useState } from 'react'
import { loginUser, signupUser } from '../api/auth'

interface AuthFormProps {
  onLogin: (token: string, username: string) => void
}

export default function AuthForm({ onLogin }: AuthFormProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    setError('')
    setLoading(true)
    try {
      if (mode === 'signup') {
        await signupUser(form.username, form.password)
        setMode('login')
        setError('Signup successful! Please login.')
      } else {
        const data = await loginUser(form.username, form.password)
        onLogin(data.access_token, data.username)
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>ChatApp</h1>
      <input
        type="text"
        placeholder="Username"
        value={form.username}
        onChange={(e) => setForm({ ...form, username: e.target.value })}
      />
      <input
        type="password"
        placeholder="Password"
        value={form.password}
        onChange={(e) => setForm({ ...form, password: e.target.value })}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Signup'}
      </button>
      <button onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}>
        Switch to {mode === 'login' ? 'Signup' : 'Login'}
      </button>
      {error && <p>{error}</p>}
    </div>
  )
}