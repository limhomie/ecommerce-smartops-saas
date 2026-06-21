import { useState, useEffect, useCallback, useRef } from 'react'
import client from '../api/client'

interface TaskState {
  taskId: string
  sessionId: string
  status: 'idle' | 'running' | 'done' | 'error'
  progress: string[]
  result: Record<string, unknown> | null
  error: string | null
}

const STORE: Record<string, TaskState> = {}
const LISTENERS: Set<() => void> = new Set()

function load(key: string): TaskState {
  if (!STORE[key]) {
    try {
      const raw = localStorage.getItem(`bg_task_${key}`)
      if (raw) STORE[key] = JSON.parse(raw)
    } catch { /* ignore */ }
  }
  return STORE[key] || { taskId: '', sessionId: '', status: 'idle', progress: [], result: null, error: null }
}

function save(key: string, state: TaskState) {
  STORE[key] = state
  try { localStorage.setItem(`bg_task_${key}`, JSON.stringify(state)) } catch { /* ignore */ }
  LISTENERS.forEach(fn => fn())
}

export function clearBackgroundTask(key: string) {
  save(key, { taskId: '', sessionId: '', status: 'idle', progress: [], result: null, error: null })
}

export function useBackgroundTask(key: string) {
  const [state, setState] = useState<TaskState>(() => load(key))
  const polling = useRef(false)

  // Listen for cross-component updates
  useEffect(() => {
    const fn = () => setState(load(key))
    LISTENERS.add(fn)
    return () => { LISTENERS.delete(fn) }
  }, [key])

  // Auto-poll on mount if there's a running task
  useEffect(() => {
    if (state.status !== 'running' || !state.taskId || polling.current) return
    polling.current = true
    let cancelled = false
    const poll = async () => {
      while (!cancelled) {
        try {
          const { data } = await client.get(`/agent/tasks/${state.taskId}`)
          if (cancelled) return
          if (data.status === 'completed') {
            save(key, { ...state, status: 'done', result: data.result || {}, progress: [] })
            return
          }
          if (data.status === 'failed') {
            save(key, { ...state, status: 'error', error: data.error || '任务失败', progress: [] })
            return
          }
        } catch { /* retry */ }
        await new Promise(r => setTimeout(r, 1500))
      }
    }
    poll()
    return () => { cancelled = true; polling.current = false }
  }, [state.status, state.taskId, key])

  const startTask = useCallback(async (task: string, sid?: string) => {
    const sessionId = sid || crypto.randomUUID()
    const newState: TaskState = {
      taskId: '', sessionId, status: 'running', progress: [], result: null, error: null,
    }
    save(key, newState)
    try {
      const { data } = await client.post('/agent/tasks', { task, session_id: sessionId })
      save(key, { ...newState, taskId: data.task_id })
    } catch (e: unknown) {
      save(key, { ...newState, status: 'error', error: e instanceof Error ? e.message : '请求失败' })
    }
  }, [key])

  const clear = useCallback(() => clearBackgroundTask(key), [key])

  return { ...state, startTask, clear }
}
