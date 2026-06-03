import axios from 'axios'
import type {
  ExplorePlace,
  KnowledgeGraphResponse,
  POIInfo,
  TripFormData,
  TripPlan,
  TripPlanProgress,
  TripPlanResponse
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

/**
 * 生成旅行计划
 */
export async function generateTripPlan(
  formData: TripFormData,
  onProgress?: (progress: TripPlanProgress) => void
): Promise<TripPlanResponse> {
  try {
    // 使用异步作业接口：先提交任务，后轮询结果，避免长请求被浏览器中断
    const submitResp = await apiClient.post('/api/trip/plan_async', formData, { timeout: 30000 })
    const jobId = submitResp.data?.job_id
    if (!jobId) throw new Error('未获得 job_id')
    onProgress?.({
      status: 'pending',
      stage: submitResp.data?.stage || '已提交',
      progress: submitResp.data?.progress || 10,
      message: submitResp.data?.message || '任务已提交，正在排队处理'
    })

    const maxAttempts = 300 // 最多轮询 300 次 ~ 10 分钟 (300*2000ms)
    const interval = 2000

    for (let i = 0; i < maxAttempts; i++) {
      try {
        const pollResp = await apiClient.get(`/api/trip/plan_result/${jobId}`, { timeout: 30000 })
        const data = pollResp.data
        if (data && data.status === 'pending') {
          onProgress?.({
            status: 'pending',
            stage: data.stage,
            progress: data.progress,
            message: data.message
          })
        } else {
          // 成功或失败（若失败会以 HTTP 500 返回）
          return data as TripPlanResponse
        }
      } catch (pollErr: any) {
        // 如果 404/500 等，可直接抛出
        console.error('轮询错误:', pollErr)
        throw new Error(pollErr.response?.data?.detail || pollErr.message || '轮询任务失败')
      }

      // 等待
      await new Promise((res) => setTimeout(res, interval))
    }

    throw new Error('等待任务超时')

  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

export async function getKnowledgeGraph(plan: TripPlan): Promise<KnowledgeGraphResponse> {
  const response = await apiClient.post('/api/assistant/knowledge-graph', plan)
  return response.data as KnowledgeGraphResponse
}

export async function askTripAssistant(question: string, tripPlan: TripPlan): Promise<string> {
  const response = await apiClient.post('/api/assistant/chat', {
    question,
    trip_plan: tripPlan
  })
  return response.data?.answer || ''
}

export const EXPLORE_THEMES = [
  {
    key: 'nature',
    label: '自然风光',
    keywords: ['景区', '公园', '山', '湖']
  },
  {
    key: 'food',
    label: '美食推荐',
    keywords: ['美食', '小吃', '餐厅', '老字号']
  },
  {
    key: 'culture',
    label: '历史文化',
    keywords: ['博物馆', '古迹', '历史文化', '寺庙']
  },
  {
    key: 'leisure',
    label: '艺术休闲',
    keywords: ['艺术馆', '展览', '咖啡', '街区']
  },
  {
    key: 'shopping',
    label: '购物休闲',
    keywords: ['商圈', '市集', '购物中心']
  }
] as const

export type ExploreThemeKey = typeof EXPLORE_THEMES[number]['key'] | 'all' | 'none'

export async function searchPOI(keyword: string, city: string, citylimit = true): Promise<POIInfo[]> {
  const response = await apiClient.get('/api/map/poi', {
    params: {
      keywords: keyword,
      city,
      citylimit
    }
  })
  return response.data?.data || []
}

export async function searchPOIByTheme(city: string, themeKey: ExploreThemeKey): Promise<ExplorePlace[]> {
  if (themeKey === 'none') return []

  const themes = themeKey === 'all'
    ? EXPLORE_THEMES
    : EXPLORE_THEMES.filter(theme => theme.key === themeKey)

  const results = await Promise.allSettled(
    themes.flatMap(theme => {
      return theme.keywords.map(async keyword => {
        const pois = await searchPOI(keyword, city)
        return pois.map(poi => ({
          ...poi,
          theme: theme.key,
          themeLabel: theme.label,
          keyword
        }))
      })
    })
  )

  const deduped = new Map<string, ExplorePlace>()
  results.forEach(result => {
    if (result.status !== 'fulfilled') return
    result.value.forEach(place => {
      const key = place.id || `${place.name}-${place.address || ''}`
      if (!deduped.has(key)) {
        deduped.set(key, place)
      }
    })
  })

  return Array.from(deduped.values())
}

export default apiClient
