import { useState, useEffect } from 'react'

export interface Message {
  role: 'user' | 'assistant'
  content: string
  charts?: unknown[]
  actions?: string[]
}

const MESSAGES_STORE: Record<string, Message[]> = {}

function loadMessages(key: string): Message[] {
  if (!MESSAGES_STORE[key]) {
    try {
      const raw = localStorage.getItem(`chat_msgs_${key}`)
      if (raw) MESSAGES_STORE[key] = JSON.parse(raw)
    } catch { /* ignore */ }
  }
  return MESSAGES_STORE[key] || []
}

function saveMessages(key: string, msgs: Message[]) {
  MESSAGES_STORE[key] = msgs
  try {
    // Keep only last 20 messages to limit storage
    const trimmed = msgs.slice(-20)
    localStorage.setItem(`chat_msgs_${key}`, JSON.stringify(trimmed))
  } catch { /* ignore */ }
}

export function usePersistentMessages(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>(() => loadMessages(sessionId))

  useEffect(() => {
    setMessages(loadMessages(sessionId))
  }, [sessionId])

  const addMessage = (msg: Message) => {
    setMessages(prev => {
      const next = [...prev, msg]
      saveMessages(sessionId, next)
      return next
    })
  }

  const updateLastAssistant = (content: string) => {
    setMessages(prev => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, content }
        saveMessages(sessionId, next)
      }
      return next
    })
  }

  const clearMessages = () => {
    setMessages([])
    saveMessages(sessionId, [])
  }

  return { messages, addMessage, updateLastAssistant, clearMessages }
}
