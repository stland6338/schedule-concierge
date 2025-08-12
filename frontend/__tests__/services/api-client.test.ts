/**
 * API Client Tests - TDD Red Phase
 * Following t_wada's TDD methodology: Write failing tests first
 */

import { APIClient } from '@/services/api-client'
import { Task, Event, CreateTaskRequest, CreateEventRequest } from '@/types/api'

// Mock fetch globally
const mockFetch = jest.fn()
global.fetch = mockFetch

describe('APIClient', () => {
  let client: APIClient
  
  beforeEach(() => {
    client = new APIClient('http://localhost:8000')
    mockFetch.mockClear()
  })

  describe('Tasks API', () => {
    it('should create a task successfully', async () => {
      // RED: This test will fail because APIClient doesn't exist yet
      const mockTask: Task = {
        id: 'task-123',
        title: 'Test Task',
        priority: 1,
        status: 'Draft',
        createdAt: '2025-08-12T10:00:00Z',
        updatedAt: '2025-08-12T10:00:00Z'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTask
      })

      const request: CreateTaskRequest = {
        title: 'Test Task',
        priority: 1
      }

      const result = await client.createTask(request)
      
      expect(result).toEqual(mockTask)
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      })
    })

    it('should get slot suggestions for a task', async () => {
      // RED: This test will fail because getSuggestions doesn't exist yet
      const mockResponse = {
        taskId: 'task-123',
        slots: [
          {
            startAt: '2025-08-13T09:00:00Z',
            endAt: '2025-08-13T10:30:00Z',
            score: 1.85
          }
        ]
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await client.getSuggestions('task-123', 5)
      
      expect(result).toEqual(mockResponse)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/slots/suggest?taskId=task-123&limit=5'
      )
    })
  })

  describe('Events API', () => {
    it('should create an event successfully', async () => {
      // RED: This test will fail because createEvent doesn't exist yet
      const mockEvent: Event = {
        id: 'event-456',
        title: 'Team Meeting',
        startAt: '2025-08-13T14:00:00Z',
        endAt: '2025-08-13T15:00:00Z',
        type: 'MEETING',
        createdAt: '2025-08-12T10:30:00Z'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEvent
      })

      const request: CreateEventRequest = {
        title: 'Team Meeting',
        startAt: '2025-08-13T14:00:00Z',
        endAt: '2025-08-13T15:00:00Z',
        type: 'MEETING'
      }

      const result = await client.createEvent(request)
      
      expect(result).toEqual(mockEvent)
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      })
    })

    it('should handle focus protection errors', async () => {
      // RED: This test will fail because error handling doesn't exist yet
      const mockError = {
        detail: {
          code: 'FOCUS_PROTECTED',
          message: 'FOCUS time is protected. Cannot create event during focus blocks'
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => mockError
      })

      const request: CreateEventRequest = {
        title: 'Conflicting Meeting',
        startAt: '2025-08-13T09:30:00Z',
        endAt: '2025-08-13T10:00:00Z',
        type: 'MEETING'
      }

      await expect(client.createEvent(request)).rejects.toThrow('FOCUS_PROTECTED')
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      // RED: This test will fail because error handling doesn't exist yet
      mockFetch.mockRejectedValueOnce(new Error('Network Error'))

      await expect(client.createTask({ title: 'Test' })).rejects.toThrow('Network Error')
    })

    it('should handle API errors with proper error codes', async () => {
      // RED: This test will fail because API error handling doesn't exist yet
      const mockError = {
        detail: {
          code: 'VALIDATION_ERROR',
          message: 'Title is required',
          traceId: 'trace-123'
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => mockError
      })

      await expect(client.createTask({ title: '' })).rejects.toThrow('VALIDATION_ERROR')
    })
  })
})