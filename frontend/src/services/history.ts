import type { TripFormData, TripHistoryItem, TripPlan } from '@/types'

const TRIP_HISTORY_KEY = 'tripPlanHistory'
const ACTIVE_HISTORY_ID_KEY = 'activeTripHistoryId'

function readHistory(): TripHistoryItem[] {
  const raw = localStorage.getItem(TRIP_HISTORY_KEY)
  if (!raw) return []

  try {
    const parsed = JSON.parse(raw) as TripHistoryItem[]
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

function writeHistory(items: TripHistoryItem[]) {
  localStorage.setItem(TRIP_HISTORY_KEY, JSON.stringify(items))
}

export function getTripHistoryList(): TripHistoryItem[] {
  return readHistory().sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
}

export function getTripHistoryById(id: string): TripHistoryItem | undefined {
  return readHistory().find((item) => item.id === id)
}

export function saveTripToHistory(plan: TripPlan, request?: TripFormData): TripHistoryItem {
  const now = new Date().toISOString()
  const items = readHistory()

  const newItem: TripHistoryItem = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: now,
    updatedAt: now,
    city: plan.city,
    start_date: plan.start_date,
    end_date: plan.end_date,
    travel_days: plan.days.length,
    preferences: request?.preferences || [],
    transportation: request?.transportation || '',
    accommodation: request?.accommodation || '',
    budget_per_person: request?.budget_per_person,
    travel_pace: request?.travel_pace,
    companions: request?.companions,
    dietary_restrictions: request?.dietary_restrictions,
    data: plan
  }

  items.unshift(newItem)
  writeHistory(items.slice(0, 50))
  setActiveHistoryId(newItem.id)
  return newItem
}

export function updateTripHistory(id: string, plan: TripPlan) {
  const items = readHistory()
  const index = items.findIndex((item) => item.id === id)
  if (index === -1) return

  items[index] = {
    ...items[index],
    updatedAt: new Date().toISOString(),
    city: plan.city,
    start_date: plan.start_date,
    end_date: plan.end_date,
    travel_days: plan.days.length,
    data: plan
  }

  writeHistory(items)
}

export function deleteTripHistory(id: string) {
  const items = readHistory().filter((item) => item.id !== id)
  writeHistory(items)

  if (getActiveHistoryId() === id) {
    sessionStorage.removeItem(ACTIVE_HISTORY_ID_KEY)
  }
}

export function clearTripHistory() {
  localStorage.removeItem(TRIP_HISTORY_KEY)
  sessionStorage.removeItem(ACTIVE_HISTORY_ID_KEY)
}

export function setActiveHistoryId(id: string) {
  sessionStorage.setItem(ACTIVE_HISTORY_ID_KEY, id)
}

export function getActiveHistoryId(): string | null {
  return sessionStorage.getItem(ACTIVE_HISTORY_ID_KEY)
}
