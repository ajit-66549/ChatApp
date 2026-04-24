const API_URL = 'http://localhost:8000'

export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  username: string
}

export async function loginUser(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail ?? 'Login failed')
  return data
}

export async function signupUser(username: string, password: string): Promise<void> {
  const res = await fetch(`${API_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail ?? 'Signup failed')
}