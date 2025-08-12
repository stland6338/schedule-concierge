/**
 * SlotRecommendation Component - GREEN phase implementation
 * Following t_wada's TDD: Minimal implementation to pass tests
 */

import React, { useState } from 'react'
import { APIClient } from '../services/api-client'
import { Task, SlotSuggestion, SlotSuggestionResponse } from '../types/api'

interface SlotRecommendationProps {
  task: Task
  limit?: number
  onSlotSelect?: (slot: SlotSuggestion) => void
}

export const SlotRecommendation: React.FC<SlotRecommendationProps> = ({ 
  task, 
  limit = 5, 
  onSlotSelect 
}) => {
  const [suggestions, setSuggestions] = useState<SlotSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasFetched, setHasFetched] = useState(false)

  const apiClient = new APIClient(process.env.API_BASE_URL || 'http://localhost:8000')

  const formatTime = (isoString: string): string => {
    const date = new Date(isoString)
    return date.toISOString().slice(0, 16).replace('T', ' ')
  }

  const formatTimeRange = (startAt: string, endAt: string): string => {
    const start = formatTime(startAt)
    const end = formatTime(endAt).slice(11) // Take only time part for end
    return `${start} - ${end}`
  }

  const handleGetSuggestions = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response: SlotSuggestionResponse = await apiClient.getSuggestions(task.id, limit)
      setSuggestions(response.slots)
      setHasFetched(true)
    } catch (err) {
      setError('推奨スロットの取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  const handleSlotSelect = (slot: SlotSuggestion) => {
    if (onSlotSelect) {
      onSlotSelect(slot)
    }
  }

  return (
    <div>
      <h3>スロット推奨</h3>
      
      {/* Task Information */}
      <div style={{ border: '1px solid #ccc', padding: '10px', marginBottom: '10px' }}>
        <h4>{task.title}</h4>
        {task.estimatedMinutes && <p>見積時間: {task.estimatedMinutes}分</p>}
        <p>優先度: {task.priority}</p>
      </div>
      
      {/* Get Suggestions Button */}
      <button 
        onClick={handleGetSuggestions} 
        disabled={loading}
      >
        推奨スロットを取得
      </button>
      
      {/* Loading State */}
      {loading && <p>読み込み中...</p>}
      
      {/* Error State */}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      
      {/* Suggestions Display */}
      {hasFetched && !loading && !error && (
        <div>
          <h4>推奨スロット</h4>
          {suggestions.length === 0 ? (
            <p>利用可能なスロットがありません</p>
          ) : (
            <div>
              {suggestions.map((slot, index) => (
                <div 
                  key={index}
                  style={{ 
                    border: '1px solid #ddd', 
                    margin: '10px 0', 
                    padding: '10px',
                    backgroundColor: '#f9f9f9'
                  }}
                >
                  <p><strong>{formatTimeRange(slot.startAt, slot.endAt)}</strong></p>
                  <p>スコア: {slot.score}</p>
                  {onSlotSelect && (
                    <button onClick={() => handleSlotSelect(slot)}>
                      このスロットを選択
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}