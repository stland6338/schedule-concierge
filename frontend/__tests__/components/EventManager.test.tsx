/**
 * EventManager Component Tests - TDD Red Phase
 * Following t_wada's methodology: Focus on behavior and user experience
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EventManager } from '../../components/EventManager'
import { APIClient } from '../../services/api-client'
import { Event, SlotSuggestion } from '../../types/api'

// Mock APIClient
jest.mock('../../services/api-client')
const MockedAPIClient = APIClient as jest.MockedClass<typeof APIClient>

describe('EventManager', () => {
  let mockAPIClient: jest.Mocked<APIClient>
  const user = userEvent.setup()

  beforeEach(() => {
    mockAPIClient = new MockedAPIClient() as jest.Mocked<APIClient>
    MockedAPIClient.mockImplementation(() => mockAPIClient)
  })

  describe('Event Creation Form', () => {
    it('should render event creation form', () => {
      // RED: This test will fail because EventManager doesn't exist
      render(<EventManager />)
      
      expect(screen.getByLabelText(/イベント名/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/開始時刻/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/終了時刻/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/タイプ/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/説明/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /イベントを作成/i })).toBeInTheDocument()
    })

    it('should create event when form is submitted', async () => {
      // RED: This will fail because event creation doesn't exist
      const mockEvent: Event = {
        id: 'event-123',
        title: 'チームミーティング',
        startAt: '2025-08-13T14:00:00Z',
        endAt: '2025-08-13T15:00:00Z',
        type: 'MEETING',
        createdAt: '2025-08-12T10:30:00Z'
      }
      
      mockAPIClient.createEvent.mockResolvedValueOnce(mockEvent)
      
      render(<EventManager />)
      
      // Fill form
      await user.type(screen.getByLabelText(/イベント名/i), 'チームミーティング')
      await user.type(screen.getByLabelText(/開始時刻/i), '2025-08-13T14:00')
      await user.type(screen.getByLabelText(/終了時刻/i), '2025-08-13T15:00')
      await user.selectOptions(screen.getByLabelText(/タイプ/i), 'MEETING')
      
      // Submit form
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      await waitFor(() => {
        expect(mockAPIClient.createEvent).toHaveBeenCalledWith({
          title: 'チームミーティング',
          startAt: '2025-08-13T14:00:00Z',
          endAt: '2025-08-13T15:00:00Z',
          type: 'MEETING'
        })
      })
      
      // Should show success message
      expect(screen.getByText(/イベントが作成されました/i)).toBeInTheDocument()
    })

    it('should validate required fields', async () => {
      // RED: This will fail because validation doesn't exist
      render(<EventManager />)
      
      // Try to submit empty form
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      expect(screen.getByText(/イベント名は必須です/i)).toBeInTheDocument()
      expect(screen.getByText(/開始時刻は必須です/i)).toBeInTheDocument()
      expect(screen.getByText(/終了時刻は必須です/i)).toBeInTheDocument()
      expect(mockAPIClient.createEvent).not.toHaveBeenCalled()
    })

    it('should validate that end time is after start time', async () => {
      // RED: This will fail because time validation doesn't exist
      render(<EventManager />)
      
      await user.type(screen.getByLabelText(/イベント名/i), 'Test Event')
      await user.type(screen.getByLabelText(/開始時刻/i), '2025-08-13T15:00')
      await user.type(screen.getByLabelText(/終了時刻/i), '2025-08-13T14:00') // Earlier than start
      
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      expect(screen.getByText(/終了時刻は開始時刻より後である必要があります/i)).toBeInTheDocument()
      expect(mockAPIClient.createEvent).not.toHaveBeenCalled()
    })
  })

  describe('Focus Protection Handling', () => {
    it('should handle focus protection errors with override option', async () => {
      // RED: This will fail because focus protection error handling doesn't exist
      mockAPIClient.createEvent
        .mockRejectedValueOnce(new Error('FOCUS_PROTECTED'))
        .mockResolvedValueOnce({
          id: 'event-456',
          title: '緊急対応',
          startAt: '2025-08-13T09:30:00Z',
          endAt: '2025-08-13T10:00:00Z',
          type: 'MEETING',
          createdAt: '2025-08-12T10:30:00Z'
        })
      
      render(<EventManager />)
      
      await user.type(screen.getByLabelText(/イベント名/i), '緊急対応')
      await user.type(screen.getByLabelText(/開始時刻/i), '2025-08-13T09:30')
      await user.type(screen.getByLabelText(/終了時刻/i), '2025-08-13T10:00')
      
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      // Should show focus protection error and override option
      await waitFor(() => {
        expect(screen.getByText(/フォーカス時間と重複しています/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /フォーカス保護を上書きして作成/i })).toBeInTheDocument()
      })
      
      // Click override button
      await user.click(screen.getByRole('button', { name: /フォーカス保護を上書きして作成/i }))
      
      await waitFor(() => {
        expect(mockAPIClient.createEvent).toHaveBeenLastCalledWith({
          title: '緊急対応',
          startAt: '2025-08-13T09:30:00Z',
          endAt: '2025-08-13T10:00:00Z',
          type: 'GENERAL',
          overrideFocusProtection: true
        })
      })
      
      expect(screen.getByText(/イベントが作成されました/i)).toBeInTheDocument()
    })

    it('should allow canceling focus protection override', async () => {
      // RED: This will fail because cancel option doesn't exist
      mockAPIClient.createEvent.mockRejectedValueOnce(new Error('FOCUS_PROTECTED'))
      
      render(<EventManager />)
      
      await user.type(screen.getByLabelText(/イベント名/i), 'テストイベント')
      await user.type(screen.getByLabelText(/開始時刻/i), '2025-08-13T09:30')
      await user.type(screen.getByLabelText(/終了時刻/i), '2025-08-13T10:00')
      
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /キャンセル/i })).toBeInTheDocument()
      })
      
      // Click cancel button
      await user.click(screen.getByRole('button', { name: /キャンセル/i }))
      
      // Should hide the error and buttons
      expect(screen.queryByText(/フォーカス時間と重複しています/i)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /フォーカス保護を上書きして作成/i })).not.toBeInTheDocument()
    })
  })

  describe('Slot Integration', () => {
    it('should allow creating event from selected slot', async () => {
      // RED: This will fail because slot integration doesn't exist
      const selectedSlot: SlotSuggestion = {
        startAt: '2025-08-13T09:00:00Z',
        endAt: '2025-08-13T10:30:00Z',
        score: 1.85
      }
      
      const mockEvent: Event = {
        id: 'event-789',
        title: 'プレゼン準備',
        startAt: '2025-08-13T09:00:00Z',
        endAt: '2025-08-13T10:30:00Z',
        type: 'FOCUS',
        createdAt: '2025-08-12T10:30:00Z'
      }
      
      mockAPIClient.createEvent.mockResolvedValueOnce(mockEvent)
      
      render(<EventManager selectedSlot={selectedSlot} suggestedTitle="プレゼン準備" />)
      
      // Form should be pre-filled with slot data
      expect(screen.getByDisplayValue('プレゼン準備')).toBeInTheDocument()
      expect(screen.getByDisplayValue('2025-08-13T09:00')).toBeInTheDocument()
      expect(screen.getByDisplayValue('2025-08-13T10:30')).toBeInTheDocument()
      
      // Submit form
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      await waitFor(() => {
        expect(mockAPIClient.createEvent).toHaveBeenCalledWith({
          title: 'プレゼン準備',
          startAt: '2025-08-13T09:00:00Z',
          endAt: '2025-08-13T10:30:00Z',
          type: 'GENERAL'
        })
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      // RED: This will fail because network error handling doesn't exist
      mockAPIClient.createEvent.mockRejectedValueOnce(new Error('Network Error'))
      
      render(<EventManager />)
      
      await user.type(screen.getByLabelText(/イベント名/i), 'Test Event')
      await user.type(screen.getByLabelText(/開始時刻/i), '2025-08-13T14:00')
      await user.type(screen.getByLabelText(/終了時刻/i), '2025-08-13T15:00')
      
      await user.click(screen.getByRole('button', { name: /イベントを作成/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/イベントの作成に失敗しました/i)).toBeInTheDocument()
      })
    })
  })
})