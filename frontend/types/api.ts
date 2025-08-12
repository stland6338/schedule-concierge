// API Type definitions based on backend spec
export interface Task {
  id: string
  title: string
  priority: number
  estimatedMinutes?: number
  dueAt?: string
  energyTag?: 'morning' | 'afternoon' | 'deep'
  status: 'Draft' | 'Scheduled' | 'InProgress' | 'Done' | 'Overdue'
  createdAt: string
  updatedAt: string
}

export interface Event {
  id: string
  title: string
  startAt: string
  endAt: string
  type: 'GENERAL' | 'MEETING' | 'FOCUS' | 'BUFFER'
  description?: string
  createdAt: string
}

export interface SlotSuggestion {
  startAt: string
  endAt: string
  score: number
}

export interface SlotSuggestionResponse {
  taskId: string
  slots: SlotSuggestion[]
}

export interface APIError {
  detail: {
    code: string
    message: string
    traceId?: string
  }
}

export interface CreateTaskRequest {
  title: string
  priority?: number
  estimatedMinutes?: number
  dueAt?: string
  energyTag?: 'morning' | 'afternoon' | 'deep'
}

export interface CreateEventRequest {
  title: string
  startAt: string
  endAt: string
  type?: 'GENERAL' | 'MEETING' | 'FOCUS' | 'BUFFER'
  description?: string
  overrideFocusProtection?: boolean
}