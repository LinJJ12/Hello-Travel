import type { TripFormData, TripHistoryItem, TripPlan } from '@/types'
import { MAX_HISTORY_ITEMS } from '@/config'
import logger from '@/utils/logger'

const TRIP_HISTORY_KEY = 'tripPlanHistory'
const ACTIVE_HISTORY_ID_KEY = 'activeTripHistoryId'

function readHistory(): TripHistoryItem[] {
  try {
    const raw = localStorage.getItem(TRIP_HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as TripHistoryItem[]
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    logger.warn('读取历史记录失败，已忽略损坏数据:', error)
    return []
  }
}

/**
 * 写入历史记录。
 *
 * 原实现没有 try/catch，遇到 QuotaExceededError（存储配额用尽）会直接抛错，
 * 导致保存/编辑操作中断。这里改为捕获并降级：先尝试裁剪到一半重试。
 */
function writeHistory(items: TripHistoryItem[]): boolean {
  try {
    localStorage.setItem(TRIP_HISTORY_KEY, JSON.stringify(items))
    return true
  } catch (error) {
    logger.warn('写入历史记录失败，尝试裁剪后重试:', error)
  }

  const trimmed = items.slice(0, Math.max(1, Math.floor(items.length / 2)))
  try {
    localStorage.setItem(TRIP_HISTORY_KEY, JSON.stringify(trimmed))
    return true
  } catch (error) {
    logger.error('历史记录写入最终失败（存储配额可能已满）:', error)
    return false
  }
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
  writeHistory(items.slice(0, MAX_HISTORY_ITEMS))
  setActiveHistoryId(newItem.id)
  return newItem
}

export function updateTripHistory(id: string, plan: TripPlan): void {
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

export function deleteTripHistory(id: string): void {
  const items = readHistory().filter((item) => item.id !== id)
  writeHistory(items)

  if (getActiveHistoryId() === id) {
    sessionStorage.removeItem(ACTIVE_HISTORY_ID_KEY)
  }
}

export function clearTripHistory(): void {
  localStorage.removeItem(TRIP_HISTORY_KEY)
  sessionStorage.removeItem(ACTIVE_HISTORY_ID_KEY)
}

export function setActiveHistoryId(id: string): void {
  sessionStorage.setItem(ACTIVE_HISTORY_ID_KEY, id)
}

export function getActiveHistoryId(): string | null {
  return sessionStorage.getItem(ACTIVE_HISTORY_ID_KEY)
}
