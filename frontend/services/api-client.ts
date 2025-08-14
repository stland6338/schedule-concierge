/**
 * API Client - GREEN phase implementation
 * Following t_wada's TDD: Minimal implementation to pass tests
 */

import { 
  Task, 
  Event, 
  CreateTaskRequest, 
  CreateEventRequest,
  SlotSuggestionResponse,
  APIError
} from '@/types/api'

export class APIClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  async createTask(request: CreateTaskRequest): Promise<Task> {
    const response = await fetch(`${this.baseURL}/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const error: APIError = await response.json()
      throw new Error(error.detail.code)
    }

    return response.json()
  }

  async createEvent(request: CreateEventRequest): Promise<Event> {
    const response = await fetch(`${this.baseURL}/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const error: APIError = await response.json()
      throw new Error(error.detail.code)
    }

    return response.json()
  }

  async getSuggestions(taskId: string, limit: number = 5): Promise<SlotSuggestionResponse> {
    const response = await fetch(
      `${this.baseURL}/slots/suggest?taskId=${taskId}&limit=${limit}`
    )

    if (!response.ok) {
      const error: APIError = await response.json()
      throw new Error(error.detail.code)
    }

    return response.json()
  }
}

// Lightweight runtime client used by some components (e.g., integrations)
const BASE = process.env.API_BASE_URL || 'http://localhost:8000'

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    try {
      const err = await res.json()
      throw new Error(err?.detail?.code || `HTTP_${res.status}`)
    } catch (e) {
      if (e instanceof Error) throw e
      throw new Error(`HTTP_${res.status}`)
    }
  }
  return res.json()
}

export const apiClient = {
  get: async <T = any>(path: string): Promise<T> => {
    const res = await fetch(`${BASE}${path}`)
    return handle<T>(res)
  },
  post: async <T = any>(path: string, body?: any): Promise<T> => {
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
    return handle<T>(res)
  },
  put: async <T = any>(path: string, body?: any): Promise<T> => {
    const res = await fetch(`${BASE}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
    return handle<T>(res)
  },
  delete: async <T = any>(path: string): Promise<T> => {
    const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
    return handle<T>(res)
  },
}