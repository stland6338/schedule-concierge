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