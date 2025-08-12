/**
 * SlotRecommendation Component Tests - TDD Red Phase
 * Following t_wada's methodology: Test behavior, not implementation
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SlotRecommendation } from '../../components/SlotRecommendation'
import { APIClient } from '../../services/api-client'
import { Task, SlotSuggestionResponse } from '../../types/api'

// Mock APIClient
jest.mock('../../services/api-client')
const MockedAPIClient = APIClient as jest.MockedClass<typeof APIClient>

describe('SlotRecommendation', () => {
  let mockAPIClient: jest.Mocked<APIClient>
  const user = userEvent.setup()
  
  const mockTask: Task = {
    id: 'task-123',
    title: 'プレゼン資料作成',
    priority: 1,
    estimatedMinutes: 90,
    status: 'Draft',
    createdAt: '2025-08-12T10:00:00Z',
    updatedAt: '2025-08-12T10:00:00Z'
  }

  beforeEach(() => {
    mockAPIClient = new MockedAPIClient() as jest.Mocked<APIClient>
    MockedAPIClient.mockImplementation(() => mockAPIClient)
  })

  describe('Slot Suggestions Display', () => {
    it('should render task information and get suggestions button', () => {
      render(<SlotRecommendation task={mockTask} />)
      
      expect(screen.getByText('プレゼン資料作成')).toBeInTheDocument()
      expect(screen.getByText('見積時間: 90分')).toBeInTheDocument()
      expect(screen.getByText('優先度: 1')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /推奨スロットを取得/i })).toBeInTheDocument()
    })

    it('should fetch and display slot suggestions when button clicked', async () => {
      const mockSuggestions: SlotSuggestionResponse = {
        taskId: 'task-123',
        slots: [
          {
            startAt: '2025-08-13T09:00:00Z',
            endAt: '2025-08-13T10:30:00Z',
            score: 1.85
          },
          {
            startAt: '2025-08-13T14:00:00Z',
            endAt: '2025-08-13T15:30:00Z',
            score: 1.72
          }
        ]
      }
      
      mockAPIClient.getSuggestions.mockResolvedValueOnce(mockSuggestions)
      
      render(<SlotRecommendation task={mockTask} />)
      
      const getSuggestionsButton = screen.getByRole('button', { name: /推奨スロットを取得/i })
      await user.click(getSuggestionsButton)
      
      await waitFor(() => {
        expect(mockAPIClient.getSuggestions).toHaveBeenCalledWith('task-123', 5)
      })
      
      // Should display suggestions using heading
      expect(screen.getByRole('heading', { name: /推奨スロット/i })).toBeInTheDocument()
      expect(screen.getByText(/2025-08-13 09:00/)).toBeInTheDocument()
      expect(screen.getByText(/2025-08-13 14:00/)).toBeInTheDocument()
      expect(screen.getByText(/スコア: 1.85/)).toBeInTheDocument()
      expect(screen.getByText(/スコア: 1.72/)).toBeInTheDocument()
    })

    it('should show loading state while fetching suggestions', async () => {
      mockAPIClient.getSuggestions.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      )
      
      render(<SlotRecommendation task={mockTask} />)
      
      const getSuggestionsButton = screen.getByRole('button', { name: /推奨スロットを取得/i })
      await user.click(getSuggestionsButton)
      
      expect(screen.getByText(/読み込み中.../i)).toBeInTheDocument()
      expect(getSuggestionsButton).toBeDisabled()
    })

    it('should handle API errors gracefully', async () => {
      mockAPIClient.getSuggestions.mockRejectedValueOnce(new Error('TASK_NOT_FOUND'))
      
      render(<SlotRecommendation task={mockTask} />)
      
      const getSuggestionsButton = screen.getByRole('button', { name: /推奨スロットを取得/i })
      await user.click(getSuggestionsButton)
      
      await waitFor(() => {
        expect(screen.getByText(/推奨スロットの取得に失敗しました/i)).toBeInTheDocument()
      })
    })

    it('should show empty state when no suggestions available', async () => {
      const mockEmptyResponse: SlotSuggestionResponse = {
        taskId: 'task-123',
        slots: []
      }
      
      mockAPIClient.getSuggestions.mockResolvedValueOnce(mockEmptyResponse)
      
      render(<SlotRecommendation task={mockTask} />)
      
      const getSuggestionsButton = screen.getByRole('button', { name: /推奨スロットを取得/i })
      await user.click(getSuggestionsButton)
      
      await waitFor(() => {
        expect(screen.getByText(/利用可能なスロットがありません/i)).toBeInTheDocument()
      })
    })
  })

  describe('Slot Selection', () => {
    it('should allow selecting a recommended slot', async () => {
      const mockSuggestions: SlotSuggestionResponse = {
        taskId: 'task-123',
        slots: [
          {
            startAt: '2025-08-13T09:00:00Z',
            endAt: '2025-08-13T10:30:00Z',
            score: 1.85
          }
        ]
      }
      
      mockAPIClient.getSuggestions.mockResolvedValueOnce(mockSuggestions)
      
      const onSlotSelect = jest.fn()
      render(<SlotRecommendation task={mockTask} onSlotSelect={onSlotSelect} />)
      
      // Get suggestions first
      await user.click(screen.getByRole('button', { name: /推奨スロットを取得/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/2025-08-13 09:00/)).toBeInTheDocument()
      })
      
      // Select the slot
      const selectButton = screen.getByRole('button', { name: /このスロットを選択/i })
      await user.click(selectButton)
      
      expect(onSlotSelect).toHaveBeenCalledWith({
        startAt: '2025-08-13T09:00:00Z',
        endAt: '2025-08-13T10:30:00Z',
        score: 1.85
      })
    })

    it('should allow customizing the number of suggestions', async () => {
      render(<SlotRecommendation task={mockTask} limit={10} />)
      
      const getSuggestionsButton = screen.getByRole('button', { name: /推奨スロットを取得/i })
      await user.click(getSuggestionsButton)
      
      await waitFor(() => {
        expect(mockAPIClient.getSuggestions).toHaveBeenCalledWith('task-123', 10)
      })
    })
  })

  describe('Time Display', () => {
    it('should format time correctly in local timezone', async () => {
      const mockSuggestions: SlotSuggestionResponse = {
        taskId: 'task-123',
        slots: [
          {
            startAt: '2025-08-13T00:00:00Z', // UTC midnight
            endAt: '2025-08-13T01:30:00Z',   // UTC 1:30 AM
            score: 1.5
          }
        ]
      }
      
      mockAPIClient.getSuggestions.mockResolvedValueOnce(mockSuggestions)
      
      render(<SlotRecommendation task={mockTask} />)
      
      await user.click(screen.getByRole('button', { name: /推奨スロットを取得/i }))
      
      await waitFor(() => {
        // Should show user-friendly time format
        expect(screen.getByText(/2025-08-13 00:00 - 01:30/)).toBeInTheDocument()
      })
    })
  })
})