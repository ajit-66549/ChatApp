import { useState, useCallback } from 'react'
import type { HistoryMessage } from '../types/chat'

const API_URL = 'http://localhost:8000'

export function useHistory() {
  const [history, setHistory] = useState<HistoryMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)

  const LIMIT = 20

  const fetchLobbyHistory = useCallback(async (reset: boolean = false) => {
    setLoading(true)
    const currentOffset = reset ? 0 : offset

    try {
      const res = await fetch(
        `${API_URL}/history/lobby?limit=${LIMIT}&offset=${currentOffset}`
      )
      const data = await res.json()

      // Concept: reverse because DB returns newest first
      // but we want to display oldest at top
      const reversed = [...data.messages].reverse()

      if (reset) {
        setHistory(reversed)
      } else {
        // Prepend older messages at the top
        setHistory((prev) => [...reversed, ...prev])
      }

      setHasMore(data.has_more)
      setOffset(currentOffset + LIMIT)
    } catch (e) {
      console.error('Failed to fetch lobby history', e)
    } finally {
      setLoading(false)
    }
  }, [offset])

  const fetchRoomHistory = useCallback(async (pin: string, reset: boolean = false) => {
    setLoading(true)
    const currentOffset = reset ? 0 : offset

    try {
      const res = await fetch(
        `${API_URL}/history/room/${pin}?limit=${LIMIT}&offset=${currentOffset}`
      )

      if (!res.ok) {
        console.error('Room not found')
        return
      }

      const data = await res.json()
      const reversed = [...data.messages].reverse()

      if (reset) {
        setHistory(reversed)
      } else {
        setHistory((prev) => [...reversed, ...prev])
      }

      setHasMore(data.has_more)
      setOffset(currentOffset + LIMIT)
    } catch (e) {
      console.error('Failed to fetch room history', e)
    } finally {
      setLoading(false)
    }
  }, [offset])

  const clearHistory = useCallback(() => {
    setHistory([])
    setOffset(0)
    setHasMore(false)
  }, [])

  return {
    history,
    loading,
    hasMore,
    fetchLobbyHistory,
    fetchRoomHistory,
    clearHistory
  }
}