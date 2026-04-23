import { useState, useCallback } from 'react'
import type { HistoryMessage } from '../types/chat'

const API_URL = 'http://localhost:8000'
const LIMIT = 20

export function useHistory(token: string) {
  const [history, setHistory] = useState<HistoryMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [loaded, setLoaded] = useState(false)

  const headers = { Authorization: `Bearer ${token}` }

  const fetchLobbyHistory = useCallback(async (reset: boolean = false) => {
    setLoading(true)
    const currentOffset = reset ? 0 : offset
    try {
      const res = await fetch(
        `${API_URL}/history/lobby?limit=${LIMIT}&offset=${currentOffset}`,
        { headers }
      )
      const data = await res.json()
      const reversed = [...data.messages].reverse()
      if (reset) {
        setHistory(reversed)
        setOffset(LIMIT)
      } else {
        setHistory((prev) => [...reversed, ...prev])
        setOffset(currentOffset + LIMIT)
      }
      setHasMore(data.has_more)
      setLoaded(true)
    } catch (e) {
      console.error('Failed to fetch lobby history', e)
    } finally {
      setLoading(false)
    }
  }, [offset, token])

  const fetchRoomHistory = useCallback(async (pin: string, reset: boolean = false) => {
    setLoading(true)
    const currentOffset = reset ? 0 : offset
    try {
      const res = await fetch(
        `${API_URL}/history/room/${pin}?limit=${LIMIT}&offset=${currentOffset}`,
        { headers }
      )
      if (!res.ok) return
      const data = await res.json()
      const reversed = [...data.messages].reverse()
      if (reset) {
        setHistory(reversed)
        setOffset(LIMIT)
      } else {
        setHistory((prev) => [...reversed, ...prev])
        setOffset(currentOffset + LIMIT)
      }
      setHasMore(data.has_more)
      setLoaded(true)
    } catch (e) {
      console.error('Failed to fetch room history', e)
    } finally {
      setLoading(false)
    }
  }, [offset, token])

  const clearHistory = useCallback(() => {
    setHistory([])
    setOffset(0)
    setHasMore(false)
    setLoaded(false)
  }, [])

  return { history, loading, hasMore, loaded, fetchLobbyHistory, fetchRoomHistory, clearHistory }
}