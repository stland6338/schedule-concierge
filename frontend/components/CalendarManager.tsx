import React, { useEffect, useState } from 'react'
import { apiClient } from '../services/api-client'
import { Calendar } from '../types/api'

export function CalendarManager() {
  const [calendars, setCalendars] = useState<Calendar[]>([])
  const [error, setError] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiClient.get<Calendar[]>('/calendars')
      setCalendars(data)
    } catch (e) {
      setError('カレンダーの取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const toggleSelected = async (cal: Calendar) => {
    try {
      const updated = await apiClient.put<Calendar>(`/calendars/${cal.id}`, { selected: !cal.selected })
      setCalendars(prev => prev.map(c => c.id === cal.id ? updated : c))
    } catch (e) {
      setError('更新に失敗しました')
    }
  }

  const setDefault = async (cal: Calendar) => {
    try {
      const updated = await apiClient.put<Calendar>(`/calendars/${cal.id}`, { isDefault: true })
      // APIは他のisDefaultを0にするので、一覧を再取得
      await load()
    } catch (e) {
      setError('既定カレンダーの設定に失敗しました')
    }
  }

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 16, marginTop: 16 }}>
      <h3>カレンダー管理</h3>
      {error && <div style={{ color: 'red', marginBottom: 8 }}>{error}</div>}
      {loading ? (
        <div>読み込み中...</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>名前</th>
              <th>既定</th>
              <th>選択</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {calendars.map(cal => (
              <tr key={cal.id}>
                <td>
                  {cal.name || '(無題)'} {cal.isPrimary && <span style={{ color: '#888' }}>(primary)</span>}
                </td>
                <td style={{ textAlign: 'center' }}>{cal.isDefault ? '✅' : ''}</td>
                <td style={{ textAlign: 'center' }}>{cal.selected ? '✅' : ''}</td>
                <td>
                  <button onClick={() => toggleSelected(cal)} style={{ marginRight: 8 }}>
                    {cal.selected ? '除外する' : '含める'}
                  </button>
                  {!cal.isDefault && (
                    <button onClick={() => setDefault(cal)}>既定にする</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default CalendarManager
