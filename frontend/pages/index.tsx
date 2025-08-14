/**
 * Schedule Concierge Main Page
 * Integrating all TDD-built components
 */

import React, { useState } from 'react'
import { TaskManager } from '../components/TaskManager'
import { SlotRecommendation } from '../components/SlotRecommendation'
import { EventManager } from '../components/EventManager'
import { GoogleCalendarIntegration } from '../components/GoogleCalendarIntegration'
import { CalendarManager } from '../components/CalendarManager'
import { Task, SlotSuggestion } from '../types/api'

export default function Home() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [selectedSlot, setSelectedSlot] = useState<SlotSuggestion | null>(null)
  const [activeTab, setActiveTab] = useState<'tasks' | 'slots' | 'events' | 'integrations'>('tasks')

  const handleSlotSelect = (slot: SlotSuggestion) => {
    setSelectedSlot(slot)
    setActiveTab('events')
  }

  const tabStyle = (tab: string) => ({
    padding: '10px 20px',
    margin: '0 5px',
    backgroundColor: activeTab === tab ? '#007bff' : '#f8f9fa',
    color: activeTab === tab ? 'white' : 'black',
    border: '1px solid #dee2e6',
    cursor: 'pointer',
    borderRadius: '4px 4px 0 0'
  })

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px' }}>
      <header style={{ marginBottom: '30px', textAlign: 'center' }}>
        <h1 style={{ color: '#333' }}>Schedule Concierge</h1>
        <p style={{ color: '#666' }}>スマートなタスクとスケジュール管理</p>
      </header>

      {/* Tab Navigation */}
      <nav style={{ marginBottom: '20px' }}>
        <button 
          style={tabStyle('tasks')}
          onClick={() => setActiveTab('tasks')}
        >
          タスク管理
        </button>
        <button 
          style={tabStyle('slots')}
          onClick={() => setActiveTab('slots')}
          disabled={!selectedTask}
        >
          スロット推奨
        </button>
        <button 
          style={tabStyle('events')}
          onClick={() => setActiveTab('events')}
        >
          イベント作成
        </button>
        <button 
          style={tabStyle('integrations')}
          onClick={() => setActiveTab('integrations')}
        >
          外部連携
        </button>
      </nav>

      {/* Main Content */}
      <main style={{ 
        border: '1px solid #dee2e6', 
        padding: '20px', 
        borderRadius: '0 4px 4px 4px',
        backgroundColor: 'white'
      }}>
        {activeTab === 'tasks' && (
          <div>
            <TaskManager />
            {selectedTask && (
              <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#e7f3ff', border: '1px solid #b3d9ff' }}>
                <p><strong>選択されたタスク:</strong> {selectedTask.title}</p>
                <button 
                  onClick={() => setActiveTab('slots')}
                  style={{ backgroundColor: '#28a745', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '4px' }}
                >
                  このタスクの推奨スロットを表示
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'slots' && selectedTask && (
          <SlotRecommendation 
            task={selectedTask} 
            onSlotSelect={handleSlotSelect}
          />
        )}

        {activeTab === 'events' && (
          <EventManager 
            selectedSlot={selectedSlot || undefined}
            suggestedTitle={selectedTask?.title}
          />
        )}

        {activeTab === 'integrations' && (
          <>
            <GoogleCalendarIntegration />
            <CalendarManager />
          </>
        )}
      </main>

      <footer style={{ marginTop: '40px', textAlign: 'center', color: '#666', fontSize: '14px' }}>
        <p>🤖 Generated with TDD following t_wada's methodology</p>
      </footer>
    </div>
  )
}