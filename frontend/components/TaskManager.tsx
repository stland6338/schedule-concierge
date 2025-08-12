/**
 * TaskManager Component - GREEN phase implementation
 * Following t_wada's TDD: Minimal implementation to pass tests
 */

import React, { useState, FormEvent } from 'react'
import { APIClient } from '../services/api-client'
import { Task, CreateTaskRequest } from '../types/api'

interface TaskManagerProps {
  initialTasks?: Task[]
}

export const TaskManager: React.FC<TaskManagerProps> = ({ initialTasks = [] }) => {
  const [tasks, setTasks] = useState<Task[]>(initialTasks)
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState(3)
  const [estimatedMinutes, setEstimatedMinutes] = useState<number | ''>('')
  const [dueAt, setDueAt] = useState('')
  const [energyTag, setEnergyTag] = useState<'morning' | 'afternoon' | 'deep' | ''>('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [validationError, setValidationError] = useState('')

  const apiClient = new APIClient(process.env.API_BASE_URL || 'http://localhost:8000')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    
    // Validation
    if (!title.trim()) {
      setValidationError('タスク名は必須です')
      return
    }
    
    setValidationError('')
    setError('')
    setSuccess('')

    try {
      const request: CreateTaskRequest = {
        title: title.trim(),
        priority,
        ...(estimatedMinutes && { estimatedMinutes: Number(estimatedMinutes) }),
        ...(dueAt && { dueAt }),
        ...(energyTag && { energyTag })
      }

      const newTask = await apiClient.createTask(request)
      setTasks(prev => [...prev, newTask])
      setSuccess('タスクが作成されました')
      
      // Reset form
      setTitle('')
      setPriority(3)
      setEstimatedMinutes('')
      setDueAt('')
      setEnergyTag('')
    } catch (err) {
      setError('エラーが発生しました')
    }
  }

  const handleStatusChange = (taskId: string, newStatus: Task['status']) => {
    setTasks(prev => 
      prev.map(task => 
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    )
  }

  return (
    <div>
      <h2>タスク管理</h2>
      
      {/* Task Creation Form */}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="title">タスク名</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        
        <div>
          <label htmlFor="priority">優先度</label>
          <select
            id="priority"
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value))}
          >
            <option value={1}>1 (最高)</option>
            <option value={2}>2 (高)</option>
            <option value={3}>3 (通常)</option>
            <option value={4}>4 (低)</option>
            <option value={5}>5 (最低)</option>
          </select>
        </div>
        
        <div>
          <label htmlFor="estimatedMinutes">見積時間（分）</label>
          <input
            id="estimatedMinutes"
            type="number"
            value={estimatedMinutes}
            onChange={(e) => setEstimatedMinutes(e.target.value ? Number(e.target.value) : '')}
          />
        </div>
        
        <div>
          <label htmlFor="dueAt">期限</label>
          <input
            id="dueAt"
            type="datetime-local"
            value={dueAt}
            onChange={(e) => setDueAt(e.target.value)}
          />
        </div>
        
        <div>
          <label htmlFor="energyTag">エネルギータグ</label>
          <select
            id="energyTag"
            value={energyTag}
            onChange={(e) => setEnergyTag(e.target.value as any)}
          >
            <option value="">選択してください</option>
            <option value="morning">朝型</option>
            <option value="afternoon">午後型</option>
            <option value="deep">深い集中</option>
          </select>
        </div>
        
        <button type="submit">タスクを作成</button>
      </form>
      
      {validationError && <div style={{ color: 'red' }}>{validationError}</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {success && <div style={{ color: 'green' }}>{success}</div>}
      
      {/* Task List */}
      <div>
        <h3>タスク一覧</h3>
        {tasks.length === 0 ? (
          <p>タスクがありません</p>
        ) : (
          <div>
            {tasks.map(task => (
              <div key={task.id} style={{ border: '1px solid #ccc', margin: '10px 0', padding: '10px' }}>
                <h4>{task.title}</h4>
                <p>優先度: {task.priority}</p>
                {task.estimatedMinutes && <p>{task.estimatedMinutes}分</p>}
                <p>ステータス: {task.status === 'InProgress' ? '進行中' : task.status}</p>
                
                {task.status === 'Draft' && (
                  <button 
                    onClick={() => handleStatusChange(task.id, 'InProgress')}
                  >
                    進行中にする
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}