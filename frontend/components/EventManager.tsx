/**
 * EventManager Component - GREEN phase implementation
 * Following t_wada's TDD: Minimal implementation to pass tests
 */

import React, { useState, useEffect, FormEvent } from 'react'
import { APIClient } from '../services/api-client'
import { Event, CreateEventRequest, SlotSuggestion } from '../types/api'

interface EventManagerProps {
  selectedSlot?: SlotSuggestion
  suggestedTitle?: string
}

export const EventManager: React.FC<EventManagerProps> = ({ 
  selectedSlot, 
  suggestedTitle 
}) => {
  const [title, setTitle] = useState('')
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [type, setType] = useState<'GENERAL' | 'MEETING' | 'FOCUS' | 'BUFFER'>('GENERAL')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [focusConflict, setFocusConflict] = useState(false)
  const [pendingEventData, setPendingEventData] = useState<CreateEventRequest | null>(null)

  const apiClient = new APIClient(process.env.API_BASE_URL || 'http://localhost:8000')

  // Pre-fill form with selected slot data
  useEffect(() => {
    if (selectedSlot) {
      // Convert UTC to local datetime-local format
      const startTime = selectedSlot.startAt.slice(0, 16)
      const endTime = selectedSlot.endAt.slice(0, 16)
      setStartAt(startTime)
      setEndAt(endTime)
    }
    if (suggestedTitle) {
      setTitle(suggestedTitle)
    }
  }, [selectedSlot, suggestedTitle])

  const formatDateTime = (localDateTime: string): string => {
    // Add :00Z to make it proper UTC format
    return `${localDateTime}:00Z`
  }

  const validateForm = (): string[] => {
    const errors: string[] = []
    
    if (!title.trim()) {
      errors.push('イベント名は必須です')
    }
    
    if (!startAt) {
      errors.push('開始時刻は必須です')
    }
    
    if (!endAt) {
      errors.push('終了時刻は必須です')
    }
    
    if (startAt && endAt && new Date(startAt) >= new Date(endAt)) {
      errors.push('終了時刻は開始時刻より後である必要があります')
    }
    
    return errors
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    
    // Validation
    const errors = validateForm()
    if (errors.length > 0) {
      setValidationErrors(errors)
      return
    }
    
    setValidationErrors([])
    setError('')
    setSuccess('')
    setFocusConflict(false)

    const request: CreateEventRequest = {
      title: title.trim(),
      startAt: formatDateTime(startAt),
      endAt: formatDateTime(endAt),
      type,
      ...(description && { description })
    }

    try {
      const newEvent = await apiClient.createEvent(request)
      setSuccess('イベントが作成されました')
      
      // Reset form
      if (!selectedSlot) { // Don't reset if using selected slot
        setTitle('')
        setStartAt('')
        setEndAt('')
        setType('GENERAL')
        setDescription('')
      }
    } catch (err) {
      if (err instanceof Error && err.message === 'FOCUS_PROTECTED') {
        setFocusConflict(true)
        setPendingEventData(request)
      } else {
        setError('イベントの作成に失敗しました')
      }
    }
  }

  const handleOverrideFocusProtection = async () => {
    if (!pendingEventData) return
    
    const requestWithOverride: CreateEventRequest = {
      ...pendingEventData,
      overrideFocusProtection: true
    }

    try {
      const newEvent = await apiClient.createEvent(requestWithOverride)
      setSuccess('イベントが作成されました')
      setFocusConflict(false)
      setPendingEventData(null)
    } catch (err) {
      setError('イベントの作成に失敗しました')
    }
  }

  const handleCancelOverride = () => {
    setFocusConflict(false)
    setPendingEventData(null)
  }

  return (
    <div>
      <h2>イベント管理</h2>
      
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="title">イベント名</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        
        <div>
          <label htmlFor="startAt">開始時刻</label>
          <input
            id="startAt"
            type="datetime-local"
            value={startAt}
            onChange={(e) => setStartAt(e.target.value)}
          />
        </div>
        
        <div>
          <label htmlFor="endAt">終了時刻</label>
          <input
            id="endAt"
            type="datetime-local"
            value={endAt}
            onChange={(e) => setEndAt(e.target.value)}
          />
        </div>
        
        <div>
          <label htmlFor="type">タイプ</label>
          <select
            id="type"
            value={type}
            onChange={(e) => setType(e.target.value as any)}
          >
            <option value="GENERAL">一般</option>
            <option value="MEETING">会議</option>
            <option value="FOCUS">集中作業</option>
            <option value="BUFFER">バッファ</option>
          </select>
        </div>
        
        <div>
          <label htmlFor="description">説明</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>
        
        <button type="submit">イベントを作成</button>
      </form>
      
      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div style={{ color: 'red' }}>
          {validationErrors.map((error, index) => (
            <p key={index}>{error}</p>
          ))}
        </div>
      )}
      
      {/* Focus Conflict Handling */}
      {focusConflict && (
        <div style={{ backgroundColor: '#fff3cd', padding: '10px', margin: '10px 0', border: '1px solid #ffeaa7' }}>
          <p style={{ color: '#856404' }}>フォーカス時間と重複しています</p>
          <div>
            <button 
              onClick={handleOverrideFocusProtection}
              style={{ marginRight: '10px', backgroundColor: '#dc3545', color: 'white' }}
            >
              フォーカス保護を上書きして作成
            </button>
            <button 
              onClick={handleCancelOverride}
              style={{ backgroundColor: '#6c757d', color: 'white' }}
            >
              キャンセル
            </button>
          </div>
        </div>
      )}
      
      {/* Success/Error Messages */}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {success && <div style={{ color: 'green' }}>{success}</div>}
    </div>
  )
}