/**
 * TaskManager Component Tests - TDD Red Phase
 * Following t_wada's methodology: Test the behavior, not implementation
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TaskManager } from '../../components/TaskManager'
import { APIClient } from '../../services/api-client'
import { Task } from '../../types/api'

// Mock APIClient
jest.mock('../../services/api-client')
const MockedAPIClient = APIClient as jest.MockedClass<typeof APIClient>

describe('TaskManager', () => {
  let mockAPIClient: jest.Mocked<APIClient>
  const user = userEvent.setup()

  beforeEach(() => {
    mockAPIClient = new MockedAPIClient() as jest.Mocked<APIClient>
    MockedAPIClient.mockImplementation(() => mockAPIClient)
  })

  describe('Task Creation', () => {
    it('should render task creation form', () => {
      // RED: This test will fail because TaskManager doesn't exist
      render(<TaskManager />)
      
      expect(screen.getByLabelText(/タスク名/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/優先度/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/見積時間/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/期限/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/エネルギータグ/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /タスクを作成/i })).toBeInTheDocument()
    })

    it('should create task when form is submitted', async () => {
      // RED: This will fail because component and methods don't exist
      const mockTask: Task = {
        id: 'task-123',
        title: 'プレゼン資料作成',
        priority: 1,
        estimatedMinutes: 90,
        status: 'Draft',
        createdAt: '2025-08-12T10:00:00Z',
        updatedAt: '2025-08-12T10:00:00Z'
      }
      
      mockAPIClient.createTask.mockResolvedValueOnce(mockTask)
      
      render(<TaskManager />)
      
      // Fill form
      await user.type(screen.getByLabelText(/タスク名/i), 'プレゼン資料作成')
      await user.selectOptions(screen.getByLabelText(/優先度/i), '1')
      await user.type(screen.getByLabelText(/見積時間/i), '90')
      
      // Submit form
      await user.click(screen.getByRole('button', { name: /タスクを作成/i }))
      
      await waitFor(() => {
        expect(mockAPIClient.createTask).toHaveBeenCalledWith({
          title: 'プレゼン資料作成',
          priority: 1,
          estimatedMinutes: 90
        })
      })
      
      // Should show success message
      expect(screen.getByText(/タスクが作成されました/i)).toBeInTheDocument()
    })

    it('should validate required fields', async () => {
      // RED: This will fail because validation doesn't exist
      render(<TaskManager />)
      
      // Try to submit empty form
      await user.click(screen.getByRole('button', { name: /タスクを作成/i }))
      
      expect(screen.getByText(/タスク名は必須です/i)).toBeInTheDocument()
      expect(mockAPIClient.createTask).not.toHaveBeenCalled()
    })

    it('should handle API errors gracefully', async () => {
      // RED: This will fail because error handling doesn't exist
      mockAPIClient.createTask.mockRejectedValueOnce(new Error('VALIDATION_ERROR'))
      
      render(<TaskManager />)
      
      await user.type(screen.getByLabelText(/タスク名/i), 'Test Task')
      await user.click(screen.getByRole('button', { name: /タスクを作成/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/エラーが発生しました/i)).toBeInTheDocument()
      })
    })
  })

  describe('Task List Display', () => {
    it('should display list of tasks', () => {
      // RED: This will fail because task list doesn't exist
      const mockTasks: Task[] = [
        {
          id: 'task-1',
          title: 'タスク1',
          priority: 1,
          status: 'Draft',
          createdAt: '2025-08-12T10:00:00Z',
          updatedAt: '2025-08-12T10:00:00Z'
        },
        {
          id: 'task-2',
          title: 'タスク2',
          priority: 2,
          status: 'InProgress',
          estimatedMinutes: 60,
          createdAt: '2025-08-12T10:00:00Z',
          updatedAt: '2025-08-12T10:00:00Z'
        }
      ]
      
      render(<TaskManager initialTasks={mockTasks} />)
      
      expect(screen.getByText('タスク1')).toBeInTheDocument()
      expect(screen.getByText('タスク2')).toBeInTheDocument()
      expect(screen.getByText('優先度: 1')).toBeInTheDocument()
      expect(screen.getByText('60分')).toBeInTheDocument()
    })

    it('should show empty state when no tasks', () => {
      // RED: This will fail because empty state doesn't exist
      render(<TaskManager initialTasks={[]} />)
      
      expect(screen.getByText(/タスクがありません/i)).toBeInTheDocument()
    })
  })

  describe('Task Status Management', () => {
    it('should allow changing task status', async () => {
      // RED: This will fail because status change doesn't exist
      const mockTask: Task = {
        id: 'task-1',
        title: 'テストタスク',
        priority: 1,
        status: 'Draft',
        createdAt: '2025-08-12T10:00:00Z',
        updatedAt: '2025-08-12T10:00:00Z'
      }
      
      render(<TaskManager initialTasks={[mockTask]} />)
      
      // Click status change button
      const statusButton = screen.getByRole('button', { name: /進行中にする/i })
      await user.click(statusButton)
      
      // Should show updated status
      expect(screen.getByText(/進行中/i)).toBeInTheDocument()
    })
  })
})