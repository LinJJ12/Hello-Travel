<template>
  <main class="result-page">
    <a-empty v-if="!tripPlan" class="empty-state" description="暂无旅行计划数据，请先创建行程">
      <template #image>
        <EnvironmentOutlined class="empty-icon" />
      </template>
      <a-button type="primary" size="large" @click="goBack">返回首页创建行程</a-button>
    </a-empty>

    <template v-else>
      <section class="result-hero">
        <div class="hero-visual">
          <img :src="coverImage" :alt="tripPlan.city" @error="handleImageError" />
        </div>

        <div class="hero-content">
          <div class="hero-topline">
            <a-button class="soft-button" @click="goBack">
              <ArrowLeftOutlined />
              返回规划
            </a-button>

            <div class="action-bar">
              <a-button v-if="!editMode" class="soft-button" @click="toggleEditMode">
                <EditOutlined />
                编辑
              </a-button>
              <a-button v-if="editMode" type="primary" class="save-button" @click="saveChanges">
                <SaveOutlined />
                保存
              </a-button>
              <a-button v-if="editMode" class="soft-button" @click="cancelEdit">
                <CloseOutlined />
                取消
              </a-button>
              <a-button class="soft-button" @click="copyShareLink">
                <ShareAltOutlined />
                分享
              </a-button>
              <a-button class="soft-button" @click="goHistory">
                <HistoryOutlined />
                历史
              </a-button>
              <a-button class="soft-button" @click="goExplore">
                <CompassOutlined />
                互动地图
              </a-button>
              <a-dropdown v-if="!editMode">
                <template #overlay>
                  <a-menu>
                    <a-menu-item key="image" @click="exportAsImage">
                      <FileImageOutlined />
                      导出图片
                    </a-menu-item>
                    <a-menu-item key="pdf" @click="exportAsPDF">
                      <FilePdfOutlined />
                      导出 PDF
                    </a-menu-item>
                    <a-menu-item key="markdown" @click="exportAsMarkdown">
                      <FileTextOutlined />
                      导出 Markdown
                    </a-menu-item>
                  </a-menu>
                </template>
                <a-button class="soft-button">
                  <DownloadOutlined />
                  导出
                  <DownOutlined />
                </a-button>
              </a-dropdown>
            </div>
          </div>

          <p class="eyebrow">Generated Travel Plan</p>
          <h1>{{ tripPlan.city }}旅行计划</h1>
          <p class="hero-dates">{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</p>
          <p class="hero-suggestion">{{ tripPlan.overall_suggestions }}</p>

          <div class="metric-grid">
            <div v-for="metric in metrics" :key="metric.label" class="metric-card">
              <component :is="metric.icon" />
              <strong>{{ metric.value }}</strong>
              <span>{{ metric.label }}</span>
            </div>
          </div>
        </div>
      </section>

      <section id="trip-export-area" class="workspace">
        <aside class="insight-rail">
          <a-card class="rail-card" :bordered="false">
            <p class="eyebrow dark">Route Snapshot</p>
            <h2>路线快照</h2>
            <div class="route-list">
              <button
                v-for="day in tripPlan.days"
                :key="day.day_index"
                type="button"
                class="route-day"
                @click="focusDay(day.day_index)"
              >
                <span>Day {{ day.day_index + 1 }}</span>
                <strong>{{ day.date }}</strong>
                <small>{{ day.attractions.map(item => item.name).join(' / ') }}</small>
              </button>
            </div>
          </a-card>

          <a-card v-if="tripPlan.budget" class="rail-card budget-rail" :bordered="false">
            <p class="eyebrow dark">Budget</p>
            <h2>预算概览</h2>
            <strong class="budget-total-value">¥{{ tripPlan.budget.total }}</strong>
            <div class="budget-mini-list">
              <div v-for="item in budgetItems" :key="item.label">
                <div class="budget-line-head">
                  <span>{{ item.label }}</span>
                  <strong>¥{{ item.value }}</strong>
                </div>
                <a-progress
                  :percent="item.percent"
                  :show-info="false"
                  :stroke-color="item.color"
                  trail-color="#e5e7eb"
                />
                <small>{{ item.percent }}% · {{ item.note }}</small>
              </div>
            </div>
          </a-card>
        </aside>

        <section class="main-panel">
          <a-tabs v-model:activeKey="activeTab" class="result-tabs" @change="handleTabChange">
            <a-tab-pane key="overview">
              <template #tab>
                <span><AppstoreOutlined /> 总览</span>
              </template>

              <div class="overview-layout">
                <a-card class="content-card" :bordered="false">
                  <div class="section-heading">
                    <span>Overview</span>
                    <h2>行程结构</h2>
                  </div>
                  <div class="day-board">
                    <article v-for="day in tripPlan.days" :key="day.day_index" class="day-summary-card">
                      <div class="day-summary-head">
                        <span>第 {{ day.day_index + 1 }} 天</span>
                        <strong>{{ day.date }}</strong>
                      </div>
                      <p>{{ day.description }}</p>
                      <div class="summary-pills">
                        <span><CarOutlined /> {{ day.transportation }}</span>
                        <span><HomeOutlined /> {{ day.accommodation }}</span>
                      </div>
                      <button type="button" @click="focusDay(day.day_index)">查看当天细节</button>
                    </article>
                  </div>
                </a-card>

                <a-card class="content-card assistant-card" :bordered="false">
                  <div class="section-heading">
                    <span>Assistant Notes</span>
                    <h2>执行建议</h2>
                  </div>
                  <p>{{ tripPlan.overall_suggestions }}</p>
                  <div class="assistant-grid">
                    <div>
                      <strong>{{ totalMeals }}</strong>
                      <span>餐饮节点</span>
                    </div>
                    <div>
                      <strong>{{ hotelCount }}</strong>
                      <span>住宿推荐</span>
                    </div>
                    <div>
                      <strong>{{ weatherCount }}</strong>
                      <span>天气天数</span>
                    </div>
                  </div>
                </a-card>
              </div>
            </a-tab-pane>

            <a-tab-pane key="days">
              <template #tab>
                <span><OrderedListOutlined /> 每日行程</span>
              </template>

              <a-card id="result-days-section" class="content-card" :bordered="false">
                <a-collapse v-model:activeKey="activeDays" accordion ghost>
                  <a-collapse-panel
                    v-for="day in tripPlan.days"
                    :key="day.day_index"
                    :id="`day-${day.day_index}`"
                  >
                    <template #header>
                      <div class="collapse-day-header">
                        <span>第 {{ day.day_index + 1 }} 天</span>
                        <strong>{{ day.date }}</strong>
                        <small>{{ day.attractions.length }} 个景点</small>
                      </div>
                    </template>

                    <div class="day-detail">
                      <div class="day-context">
                        <p>{{ day.description }}</p>
                        <div class="summary-pills">
                          <span><CarOutlined /> {{ day.transportation }}</span>
                          <span><HomeOutlined /> {{ day.accommodation }}</span>
                        </div>
                      </div>

                      <div class="route-timeline">
                        <article
                          v-for="(item, index) in day.attractions"
                          :key="`${day.day_index}-${item.name}-${index}`"
                          class="route-stop"
                          :class="{ draggable: editMode }"
                          :draggable="editMode"
                          @dragstart="handleDragStart(day.day_index, index)"
                          @dragover.prevent
                          @drop="handleDrop(day.day_index, index)"
                        >
                          <div class="route-stop-marker">
                            <span>{{ index + 1 }}</span>
                          </div>

                          <div class="route-stop-thumb">
                            <img :src="getAttractionImage(item.name, index)" :alt="item.name" @error="handleImageError" />
                          </div>

                          <div class="route-stop-main">
                            <div v-if="editMode" class="edit-fields">
                              <a-input v-model:value="item.name" placeholder="景点名称" />
                              <a-input v-model:value="item.address" placeholder="地址" />
                              <a-input-number
                                v-model:value="item.visit_duration"
                                :min="10"
                                :max="480"
                                class="field-full"
                                addon-after="分钟"
                              />
                              <a-textarea v-model:value="item.description" :rows="3" placeholder="描述" />
                              <div class="edit-actions">
                                <a-button size="small" :disabled="index === 0" @click="moveAttraction(day.day_index, index, 'up')">
                                  <ArrowUpOutlined />
                                </a-button>
                                <a-button
                                  size="small"
                                  :disabled="index === day.attractions.length - 1"
                                  @click="moveAttraction(day.day_index, index, 'down')"
                                >
                                  <ArrowDownOutlined />
                                </a-button>
                                <a-button size="small" danger @click="deleteAttraction(day.day_index, index)">
                                  <DeleteOutlined />
                                </a-button>
                              </div>
                            </div>

                            <template v-else>
                              <div class="route-stop-head">
                                <div>
                                  <h3>{{ item.name }}</h3>
                                  <p>{{ item.description }}</p>
                                </div>
                                <a-button size="small" @click="focusAttraction(day.day_index, index)">
                                  <AimOutlined />
                                  定位
                                </a-button>
                              </div>
                              <div class="route-stop-meta">
                                <span><EnvironmentOutlined /> {{ item.address || '暂无地址' }}</span>
                                <span><ClockCircleOutlined /> {{ item.visit_duration || 0 }} 分钟</span>
                                <span v-if="item.rating"><StarOutlined /> {{ item.rating }}</span>
                                <span v-if="item.ticket_price"><DollarOutlined /> ¥{{ item.ticket_price }}</span>
                              </div>
                            </template>
                          </div>
                        </article>
                      </div>

                      <div class="day-support-strip">
                        <details v-if="day.hotel" class="support-item">
                          <summary>
                            <HomeOutlined />
                            <div>
                              <span>住宿推荐</span>
                              <strong>{{ day.hotel.name }}</strong>
                              <small>{{ day.hotel.address || '暂无地址' }}</small>
                            </div>
                          </summary>
                          <div class="support-detail hotel-detail-list">
                            <div class="hotel-detail-item">
                              <span>地址</span>
                              <strong>{{ day.hotel.address || '暂无地址' }}</strong>
                            </div>
                            <div class="hotel-detail-item">
                              <span>住宿服务</span>
                              <strong>{{ day.hotel.type || '住宿' }}</strong>
                            </div>
                            <div class="hotel-detail-item">
                              <span>价格区间</span>
                              <strong>{{ day.hotel.price_range || '价格待确认' }}</strong>
                            </div>
                            <div class="hotel-detail-item">
                              <span>评分距离</span>
                              <strong>{{ [day.hotel.rating, day.hotel.distance].filter(Boolean).join(' · ') || '暂无补充信息' }}</strong>
                            </div>
                          </div>
                        </details>

                        <details v-if="day.meals.length" class="support-item">
                          <summary>
                            <CoffeeOutlined />
                            <div>
                              <span>餐饮安排</span>
                              <strong>{{ day.meals.length }} 个餐饮节点</strong>
                              <small>{{ day.meals.map(meal => meal.name).join(' / ') }}</small>
                            </div>
                          </summary>
                          <div class="support-detail meal-detail-list">
                            <div v-for="meal in day.meals" :key="`${meal.type}-${meal.name}`" class="meal-detail-item">
                              <div>
                                <span>{{ getMealLabel(meal.type) }}</span>
                                <strong>{{ meal.name }}</strong>
                              </div>
                              <p v-if="meal.description">{{ meal.description }}</p>
                              <small v-if="meal.address">{{ meal.address }}</small>
                            </div>
                          </div>
                        </details>
                      </div>
                    </div>
                  </a-collapse-panel>
                </a-collapse>
              </a-card>
            </a-tab-pane>

            <a-tab-pane key="map">
              <template #tab>
                <span><EnvironmentOutlined /> 地图动线</span>
              </template>

              <div class="map-layout">
                <a-card class="content-card map-card" :bordered="false">
                  <div class="section-heading map-heading">
                    <div>
                      <span>Route Map</span>
                      <h2>景点地图</h2>
                    </div>
                    <a-button class="soft-button dark" @click="refreshMap">
                      <ReloadOutlined />
                      刷新地图
                    </a-button>
                  </div>
                  <div id="amap-container" class="amap-container"></div>
                </a-card>

                <a-card class="content-card route-index-card" :bordered="false">
                  <div class="section-heading">
                    <span>Stops</span>
                    <h2>站点索引</h2>
                  </div>
                  <div class="stop-index">
                    <button
                      v-for="stop in routeStops"
                      :key="`${stop.dayIndex}-${stop.attrIndex}-${stop.name}`"
                      type="button"
                      @click="focusAttraction(stop.dayIndex, stop.attrIndex)"
                    >
                      <span>D{{ stop.dayIndex + 1 }}-{{ stop.attrIndex + 1 }}</span>
                      <strong>{{ stop.name }}</strong>
                      <small>{{ stop.address }}</small>
                    </button>
                  </div>
                </a-card>
              </div>
            </a-tab-pane>

            <a-tab-pane key="local">
              <template #tab>
                <span><CompassOutlined /> 当地探索</span>
              </template>

              <div class="local-guide">
                <a-card class="content-card local-hero-card" :bordered="false">
                  <div class="section-heading">
                    <span>Local Guide</span>
                    <h2>用互动地图了解{{ tripPlan.city }}</h2>
                  </div>
                  <p>
                    当地探索已经升级为独立互动地图，会实时检索自然风光、美食、历史文化、艺术休闲和购物休闲，不再受当前行程偏好限制。
                  </p>

                  <a-button type="primary" size="large" @click="goExplore">
                    <CompassOutlined />
                    打开{{ tripPlan.city }}互动地图
                  </a-button>
                </a-card>
              </div>
            </a-tab-pane>

            <a-tab-pane key="budget">
              <template #tab>
                <span><CloudOutlined /> 天气建议</span>
              </template>

              <div class="weather-panel-grid">
                <a-card v-if="tripPlan.weather_info?.length" class="content-card weather-main-card" :bordered="false">
                  <div class="section-heading">
                    <span>Weather</span>
                    <h2>天气窗口与出行建议</h2>
                  </div>
                  <div class="weather-grid">
                    <article v-for="item in tripPlan.weather_info" :key="item.date" class="weather-card">
                      <div class="weather-card-head">
                        <span><CloudOutlined /></span>
                        <strong>{{ item.date }}</strong>
                      </div>
                      <div class="weather-temp-row">
                        <div>
                          <span>白天</span>
                          <strong>{{ item.day_temp }}°C</strong>
                          <small>{{ item.day_weather }}</small>
                        </div>
                        <div>
                          <span>夜间</span>
                          <strong>{{ item.night_temp }}°C</strong>
                          <small>{{ item.night_weather }}</small>
                        </div>
                      </div>
                      <p>{{ item.wind_direction }} {{ item.wind_power }}</p>
                      <div class="weather-advice">
                        <strong>当天建议</strong>
                        <span>{{ getWeatherAdvice(item).join('；') }}</span>
                      </div>
                    </article>
                  </div>
                </a-card>

                <a-card v-else class="content-card" :bordered="false">
                  <a-empty description="暂无天气数据，行程内容仍可正常查看" />
                </a-card>

                <a-card class="content-card weather-note-card" :bordered="false">
                  <div class="section-heading">
                    <span>Tips</span>
                    <h2>出行提醒</h2>
                  </div>
                  <div class="weather-tips">
                    <div v-for="tip in weatherTips" :key="tip.title">
                      <strong>{{ tip.title }}</strong>
                      <span>{{ tip.content }}</span>
                    </div>
                  </div>
                </a-card>
              </div>
            </a-tab-pane>
          </a-tabs>
        </section>
      </section>

      <a-back-top :visibility-height="320">
        <div class="back-top-button">
          <ArrowUpOutlined />
        </div>
      </a-back-top>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  AimOutlined,
  AppstoreOutlined,
  ArrowDownOutlined,
  ArrowLeftOutlined,
  ArrowUpOutlined,
  CalendarOutlined,
  CarOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  CloudOutlined,
  CompassOutlined,
  CoffeeOutlined,
  DeleteOutlined,
  DollarOutlined,
  DownOutlined,
  DownloadOutlined,
  EditOutlined,
  EnvironmentOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  HistoryOutlined,
  HomeOutlined,
  OrderedListOutlined,
  ReloadOutlined,
  SaveOutlined,
  ShareAltOutlined,
  StarOutlined
} from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { Attraction, TripPlan, WeatherInfo } from '@/types'
import {
  getActiveHistoryId,
  getTripHistoryById,
  saveTripToHistory,
  setActiveHistoryId,
  updateTripHistory
} from '@/services/history'

const router = useRouter()
const route = useRoute()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeTab = ref('overview')
const activeDays = ref<number[]>([0])
const activeHistoryId = ref<string | null>(null)
const draggedAttraction = ref<{ dayIndex: number; attrIndex: number } | null>(null)

let map: any = null
let mapApi: any = null
let mapMarkers: Record<string, any> = {}

const totalAttractions = computed(() => {
  return tripPlan.value?.days.reduce((sum, day) => sum + day.attractions.length, 0) || 0
})

const totalMeals = computed(() => {
  return tripPlan.value?.days.reduce((sum, day) => sum + day.meals.length, 0) || 0
})

const hotelCount = computed(() => {
  return tripPlan.value?.days.filter(day => Boolean(day.hotel)).length || 0
})

const weatherCount = computed(() => tripPlan.value?.weather_info?.length || 0)

const totalDurationHours = computed(() => {
  const minutes = tripPlan.value?.days.reduce((sum, day) => {
    return sum + day.attractions.reduce((daySum, attraction) => daySum + (attraction.visit_duration || 0), 0)
  }, 0) || 0
  return (minutes / 60).toFixed(1)
})

const coverImage = computed(() => {
  const first = tripPlan.value?.days[0]?.attractions[0]
  if (!first) return getFallbackImage('旅行计划', 0)
  return getAttractionImage(first.name, 0)
})

const metrics = computed(() => [
  { label: '旅行天数', value: `${tripPlan.value?.days.length || 0} 天`, icon: CalendarOutlined },
  { label: '景点站点', value: `${totalAttractions.value} 个`, icon: EnvironmentOutlined },
  { label: '游览时长', value: `${totalDurationHours.value} h`, icon: ClockCircleOutlined },
  { label: '总预算', value: tripPlan.value?.budget ? `¥${tripPlan.value.budget.total}` : '待估算', icon: DollarOutlined }
])

const budgetItems = computed(() => {
  const budget = tripPlan.value?.budget
  if (!budget) return []
  const total = budget.total || 1
  return [
    {
      label: '景点门票',
      value: budget.total_attractions,
      icon: AimOutlined,
      percent: Math.round((budget.total_attractions / total) * 100),
      color: '#0f766e',
      note: '门票与景区相关支出'
    },
    {
      label: '酒店住宿',
      value: budget.total_hotels,
      icon: HomeOutlined,
      percent: Math.round((budget.total_hotels / total) * 100),
      color: '#f97316',
      note: '住宿房费预估'
    },
    {
      label: '餐饮费用',
      value: budget.total_meals,
      icon: CoffeeOutlined,
      percent: Math.round((budget.total_meals / total) * 100),
      color: '#2563eb',
      note: '正餐、小吃与饮品'
    },
    {
      label: '交通费用',
      value: budget.total_transportation,
      icon: CarOutlined,
      percent: Math.round((budget.total_transportation / total) * 100),
      color: '#7c3aed',
      note: '城市交通与换乘'
    }
  ]
})

const weatherTips = computed(() => {
  const weather = tripPlan.value?.weather_info || []
  if (!weather.length) {
    return [
      { title: '暂无天气', content: '当前行程没有天气数据，建议出发前再次确认当地天气。' }
    ]
  }

  const uniqueAdvice = Array.from(new Set(weather.flatMap(item => getWeatherAdvice(item)))).slice(0, 4)
  const titles = ['装备', '节奏', '温度', '户外']
  return uniqueAdvice.map((content, index) => ({
    title: titles[index] || '提醒',
    content
  }))
})

const routeStops = computed(() => {
  if (!tripPlan.value) return []
  return tripPlan.value.days.flatMap((day, dayIndex) => {
    return day.attractions.map((attraction, attrIndex) => ({
      ...attraction,
      dayIndex,
      attrIndex
    }))
  })
})

onMounted(async () => {
  const queryId = typeof route.query.historyId === 'string' ? route.query.historyId : null
  const sessionId = getActiveHistoryId()
  activeHistoryId.value = queryId || sessionId

  if (activeHistoryId.value) {
    setActiveHistoryId(activeHistoryId.value)
    const historyItem = getTripHistoryById(activeHistoryId.value)
    if (historyItem) {
      tripPlan.value = historyItem.data
      sessionStorage.setItem('tripPlan', JSON.stringify(historyItem.data))
    }
  }

  if (!tripPlan.value) {
    const data = sessionStorage.getItem('tripPlan')
    if (data) {
      tripPlan.value = JSON.parse(data)
    }
  }

  if (tripPlan.value) {
    await loadAttractionPhotos()
    await nextTick()
    initMap()
  }
})

const goBack = () => {
  router.push('/')
}

const goHistory = () => {
  router.push('/history')
}

const goExplore = () => {
  router.push({ path: '/explore', query: { city: tripPlan.value?.city || '', theme: 'none' } })
}

const handleTabChange = async (key: string) => {
  activeTab.value = key
  if (key === 'map') {
    await nextTick()
    refreshMap()
  }
}

const focusDay = async (dayIndex: number) => {
  activeTab.value = 'days'
  activeDays.value = [dayIndex]
  await nextTick()
  const target = document.getElementById('result-days-section')
  if (!target) return

  const top = target.getBoundingClientRect().top + window.scrollY - 88
  window.scrollTo({ top: Math.max(top, 0), behavior: 'auto' })
}

const focusAttraction = async (dayIndex: number, attrIndex: number, switchTab = true) => {
  const attraction = tripPlan.value?.days[dayIndex]?.attractions[attrIndex]
  if (!attraction?.location) return

  if (switchTab) {
    activeTab.value = 'map'
    await nextTick()
    if (!map) initMap()
  }

  if (!map) return
  const position = [attraction.location.longitude, attraction.location.latitude]
  map.setZoomAndCenter(15, position)
  const marker = mapMarkers[`${dayIndex}-${attrIndex}`]
  if (marker && mapApi) {
    const infoWindow = new mapApi.InfoWindow({
      content: `
        <div style="padding: 12px; max-width: 260px;">
          <h4 style="margin: 0 0 8px 0;">${attraction.name}</h4>
          <p style="margin: 4px 0;">${attraction.address || ''}</p>
          <p style="margin: 4px 0; color: #0f766e;">第${dayIndex + 1}天 · 第${attrIndex + 1}站</p>
        </div>
      `,
      offset: new mapApi.Pixel(0, -30),
      autoMove: false
    })
    infoWindow.open(map, marker.getPosition())
    window.setTimeout(() => {
      map?.setCenter(position)
    }, 80)
  }
}

const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  activeTab.value = 'days'
  message.info('已进入编辑模式')
}

const saveChanges = () => {
  editMode.value = false
  if (tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
    if (activeHistoryId.value) {
      updateTripHistory(activeHistoryId.value, tripPlan.value)
    } else {
      const created = saveTripToHistory(tripPlan.value)
      activeHistoryId.value = created.id
      setActiveHistoryId(created.id)
    }
  }
  message.success('修改已保存')
  refreshMap()
}

const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  }
  editMode.value = false
  message.info('已取消编辑')
  refreshMap()
}

const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return
  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning('每天至少需要保留一个景点')
    return
  }
  day.attractions.splice(attrIndex, 1)
  message.success('景点已删除')
  refreshMap()
}

const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return
  const attractions = tripPlan.value.days[dayIndex].attractions
  if (direction === 'up' && attrIndex > 0) {
    ;[attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    ;[attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
  refreshMap()
}

const handleDragStart = (dayIndex: number, attrIndex: number) => {
  draggedAttraction.value = { dayIndex, attrIndex }
}

const handleDrop = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value || !draggedAttraction.value) return
  const source = draggedAttraction.value
  if (source.dayIndex !== dayIndex || source.attrIndex === attrIndex) {
    draggedAttraction.value = null
    return
  }
  const attractions = tripPlan.value.days[dayIndex].attractions
  const [moved] = attractions.splice(source.attrIndex, 1)
  attractions.splice(attrIndex, 0, moved)
  draggedAttraction.value = null
  refreshMap()
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

const getWeatherAdvice = (item: WeatherInfo) => {
  const weatherText = `${item.day_weather || ''}${item.night_weather || ''}`
  const windText = `${item.wind_direction || ''}${item.wind_power || ''}`
  const tempGap = Math.abs((item.day_temp || 0) - (item.night_temp || 0))
  const advice: string[] = []

  if (/雨|阵雨|雷|雪|雾/.test(weatherText)) {
    advice.push('准备雨具，鞋子尽量选择防滑耐走款')
  }
  if ((item.day_temp || 0) >= 30) {
    advice.push('白天温度较高，户外景点优先安排在上午或傍晚')
  }
  if ((item.night_temp || 0) <= 10 || tempGap >= 10) {
    advice.push('昼夜温差明显，随身带一件薄外套')
  }
  if (/风|级/.test(windText) && !/0|1/.test(String(item.wind_power))) {
    advice.push('风力偏强，减少高处或开阔地长时间停留')
  }
  if (!advice.length) {
    advice.push('天气条件较平稳，按原计划安排户外和步行路线即可')
  }

  return advice
}

const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return
  const promises: Promise<void>[] = []
  tripPlan.value.days.forEach(day => {
    day.attractions.forEach(attraction => {
      if (attraction.image_url) {
        attractionPhotos.value[attraction.name] = attraction.image_url
        return
      }
      const promise = fetch(`http://localhost:8000/api/poi/photo?name=${encodeURIComponent(attraction.name)}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data.photo_url) {
            attractionPhotos.value[attraction.name] = data.data.photo_url
          }
        })
        .catch(() => undefined)
      promises.push(promise)
    })
  })
  await Promise.all(promises)
}

const getFallbackImage = (name: string, index: number): string => {
  const colors = [
    { start: '#0f766e', end: '#2563eb' },
    { start: '#f97316', end: '#0f766e' },
    { start: '#1d4ed8', end: '#7c3aed' },
    { start: '#334155', end: '#0f766e' }
  ]
  const { start, end } = colors[index % colors.length]
  const safeName = name.replace(/[<>&"']/g, '')
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="520">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${start}"/><stop offset="100%" stop-color="${end}"/>
    </linearGradient></defs>
    <rect width="800" height="520" fill="url(#g)"/>
    <circle cx="650" cy="120" r="110" fill="rgba(255,255,255,0.16)"/>
    <text x="56" y="270" font-family="Arial, sans-serif" font-size="48" font-weight="700" fill="white">${safeName}</text>
  </svg>`
  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

const getAttractionImage = (name: string, index: number): string => {
  return attractionPhotos.value[name] || getFallbackImage(name, index)
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = getFallbackImage(img.alt || '旅行计划', 0)
}

const exportAsImage = async () => {
  try {
    message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })
    const { default: html2canvas } = await import('html2canvas')
    const element = document.querySelector('#trip-export-area') as HTMLElement
    if (!element) throw new Error('未找到内容元素')
    const canvas = await html2canvas(element, {
      backgroundColor: '#f6f8fb',
      scale: 2,
      useCORS: true,
      allowTaint: true
    })
    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.value?.city}_${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    message.success({ content: '图片导出成功', key: 'export' })
  } catch (error: any) {
    message.error({ content: `导出图片失败: ${error.message}`, key: 'export' })
  }
}

const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成 PDF...', key: 'export', duration: 0 })
    const [{ default: html2canvas }, { default: jsPDF }] = await Promise.all([
      import('html2canvas'),
      import('jspdf')
    ])
    const element = document.querySelector('#trip-export-area') as HTMLElement
    if (!element) throw new Error('未找到内容元素')
    const canvas = await html2canvas(element, {
      backgroundColor: '#f6f8fb',
      scale: 2,
      useCORS: true,
      allowTaint: true
    })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const imgWidth = 210
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    let heightLeft = imgHeight
    let position = 0
    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297
    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }
    pdf.save(`旅行计划_${tripPlan.value?.city}_${Date.now()}.pdf`)
    message.success({ content: 'PDF 导出成功', key: 'export' })
  } catch (error: any) {
    message.error({ content: `导出 PDF 失败: ${error.message}`, key: 'export' })
  }
}

const buildMarkdown = (): string => {
  if (!tripPlan.value) return ''
  const lines = [
    `# ${tripPlan.value.city}旅行计划`,
    '',
    `日期：${tripPlan.value.start_date} 至 ${tripPlan.value.end_date}`,
    '',
    `总体建议：${tripPlan.value.overall_suggestions}`,
    ''
  ]
  if (tripPlan.value.budget) {
    lines.push('## 预算', '')
    budgetItems.value.forEach(item => lines.push(`- ${item.label}：¥${item.value}`))
    lines.push(`- 预估总费用：¥${tripPlan.value.budget.total}`, '')
  }
  tripPlan.value.days.forEach(day => {
    lines.push(`## 第${day.day_index + 1}天 ${day.date}`, '', day.description, '')
    lines.push(`交通：${day.transportation}`)
    lines.push(`住宿：${day.accommodation}`, '')
    lines.push('### 景点')
    day.attractions.forEach((attraction, index) => {
      lines.push(`${index + 1}. ${attraction.name}（${attraction.visit_duration}分钟）`)
      lines.push(`   地址：${attraction.address}`)
      if (attraction.description) lines.push(`   说明：${attraction.description}`)
    })
    lines.push('')
    if (day.hotel) {
      lines.push(`### 住宿推荐：${day.hotel.name}`)
      lines.push(`地址：${day.hotel.address}`)
      lines.push(`价格：${day.hotel.price_range}`, '')
    }
    lines.push('### 餐饮')
    day.meals.forEach(meal => {
      lines.push(`- ${getMealLabel(meal.type)}：${meal.name}${meal.description ? ` - ${meal.description}` : ''}`)
    })
    lines.push('')
  })
  return lines.join('\n')
}

const downloadTextFile = (content: string, filename: string, type = 'text/markdown;charset=utf-8') => {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

const exportAsMarkdown = () => {
  if (!tripPlan.value) return
  downloadTextFile(buildMarkdown(), `旅行计划_${tripPlan.value.city}_${Date.now()}.md`)
  message.success('Markdown 导出成功')
}

const copyShareLink = async () => {
  if (!tripPlan.value) return
  let historyId = activeHistoryId.value
  if (!historyId) {
    const created = saveTripToHistory(tripPlan.value)
    historyId = created.id
    activeHistoryId.value = created.id
    setActiveHistoryId(created.id)
  }
  const url = `${window.location.origin}${router.resolve({ path: '/result', query: { historyId } }).href}`
  try {
    await navigator.clipboard.writeText(url)
    message.success('分享链接已复制')
  } catch {
    downloadTextFile(url, `旅行计划_${tripPlan.value.city}_分享链接.txt`, 'text/plain;charset=utf-8')
    message.warning('无法访问剪贴板，已导出分享链接文本')
  }
}

const refreshMap = () => {
  if (map) {
    map.destroy()
    map = null
    mapMarkers = {}
  }
  nextTick(() => initMap())
}

const initMap = async () => {
  const container = document.getElementById('amap-container')
  if (!container || !tripPlan.value) return
  try {
    const AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_WEB_JS_KEY,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })
    mapApi = AMap

    const located = routeStops.value.filter((item: Attraction) => {
      return item.location?.longitude && item.location?.latitude
    })
    const center = located.length
      ? [
          located.reduce((sum, item: any) => sum + item.location.longitude, 0) / located.length,
          located.reduce((sum, item: any) => sum + item.location.latitude, 0) / located.length
        ]
      : [116.397128, 39.916527]

    map = new AMap.Map('amap-container', {
      zoom: 12,
      center,
      viewMode: '3D',
      mapStyle: 'amap://styles/normal'
    })
    addAttractionMarkers(AMap)
  } catch (error) {
    console.error('地图加载失败:', error)
    message.error('地图加载失败')
  }
}

const addAttractionMarkers = (AMap: any) => {
  if (!tripPlan.value || !map) return
  const markers: any[] = []
  mapMarkers = {}

  routeStops.value.forEach((attraction: any, index: number) => {
    if (!attraction.location?.longitude || !attraction.location?.latitude) return
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      label: {
        content: `<div style="background:#0f766e;color:white;padding:5px 9px;border-radius:8px;font-size:12px;font-weight:700;">${index + 1}</div>`,
        offset: new AMap.Pixel(0, -30)
      }
    })
    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding:12px;max-width:280px;">
          <h4 style="margin:0 0 8px 0;">${attraction.name}</h4>
          <p style="margin:4px 0;"><strong>地址:</strong> ${attraction.address || ''}</p>
          <p style="margin:4px 0;"><strong>游览:</strong> ${attraction.visit_duration || 0}分钟</p>
          <p style="margin:4px 0;color:#0f766e;"><strong>第${attraction.dayIndex + 1}天 · 第${attraction.attrIndex + 1}站</strong></p>
        </div>
      `,
      offset: new AMap.Pixel(0, -30),
      autoMove: false
    })
    marker.on('click', () => infoWindow.open(map, marker.getPosition()))
    mapMarkers[`${attraction.dayIndex}-${attraction.attrIndex}`] = marker
    markers.push(marker)
  })

  if (markers.length > 0) {
    map.add(markers)
    map.setFitView(markers)
  }
  drawRoutes(AMap)
}

const drawRoutes = (AMap: any) => {
  if (!tripPlan.value || !map) return
  tripPlan.value.days.forEach(day => {
    const path = day.attractions
      .filter(item => item.location?.longitude && item.location?.latitude)
      .map(item => [item.location.longitude, item.location.latitude])
    if (path.length < 2) return
    const polyline = new AMap.Polyline({
      path,
      strokeColor: '#f97316',
      strokeWeight: 5,
      strokeOpacity: 0.82,
      strokeStyle: 'solid',
      showDir: true
    })
    map.add(polyline)
  })
}

</script>

<style scoped>
.result-page {
  width: min(1480px, 100%);
  margin: 0 auto;
  padding: 28px clamp(16px, 4vw, 44px) 64px;
}

.empty-state {
  min-height: 520px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.empty-icon {
  color: #0f766e;
  font-size: 72px;
}

.result-hero {
  position: relative;
  min-height: 390px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
}

.hero-visual {
  position: absolute;
  inset: 0;
}

.hero-visual::after {
  position: absolute;
  inset: 0;
  content: '';
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.96) 0%, rgba(255, 255, 255, 0.9) 48%, rgba(255, 255, 255, 0.58) 100%),
    linear-gradient(0deg, rgba(255, 255, 255, 0.82), transparent 56%);
}

.hero-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-content {
  position: relative;
  z-index: 1;
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(24px, 4vw, 46px);
  color: #111827;
}

.hero-topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.soft-button,
.save-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  border-radius: 8px;
  font-weight: 700;
}

.soft-button {
  border-color: #dbe3ea;
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
  backdrop-filter: blur(8px);
}

.soft-button:hover,
.soft-button.dark:hover {
  border-color: #0f766e;
  background: #eefaf7;
  color: #0f766e;
}

.soft-button.dark {
  border-color: #dbe3ea;
  background: #ffffff;
  color: #0f172a;
}

.save-button {
  background: #0f766e;
  border-color: #0f766e;
}

.eyebrow {
  margin: auto 0 10px;
  color: inherit;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
  opacity: 0.72;
}

.eyebrow.dark {
  margin: 0 0 8px;
  color: #0f766e;
}

.hero-content h1 {
  max-width: 820px;
  margin: 0;
  color: #111827;
  font-size: clamp(34px, 5vw, 58px);
  font-weight: 850;
  line-height: 1.02;
  letter-spacing: 0;
}

.hero-dates {
  margin: 12px 0 0;
  color: #475569;
  font-size: 18px;
}

.hero-suggestion {
  max-width: 780px;
  margin: 22px 0 0;
  color: #475569;
  font-size: 17px;
  line-height: 1.8;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  max-width: 900px;
  margin-top: 32px;
}

.metric-card {
  min-height: 96px;
  padding: 16px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
}

.metric-card :deep(svg) {
  color: #f97316;
  font-size: 20px;
}

.metric-card strong,
.metric-card span {
  display: block;
}

.metric-card strong {
  margin-top: 10px;
  color: #111827;
  font-size: 22px;
}

.metric-card span {
  margin-top: 3px;
  color: #64748b;
}

.workspace {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 20px;
  margin-top: 22px;
  align-items: start;
}

.insight-rail {
  position: sticky;
  top: 84px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rail-card,
.content-card {
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.rail-card h2,
.section-heading h2 {
  margin: 0;
  color: #111827;
}

.route-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
}

.route-day {
  display: block;
  width: 100%;
  padding: 13px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}

.route-day:hover {
  border-color: #0f766e;
  background: #eefaf7;
}

.route-day span,
.route-day strong,
.route-day small {
  display: block;
}

.route-day span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
}

.route-day strong {
  margin-top: 4px;
  color: #111827;
}

.route-day small {
  margin-top: 6px;
  color: #64748b;
  line-height: 1.5;
}

.budget-total-value {
  display: block;
  margin: 12px 0;
  color: #f97316;
  font-size: 36px;
  line-height: 1;
}

.budget-mini-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 18px;
}

.budget-mini-list > div {
  color: #64748b;
}

.budget-line-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.budget-line-head strong {
  color: #111827;
}

.budget-mini-list small {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.main-panel {
  min-width: 0;
}

.result-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
  padding: 6px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
}

.result-tabs :deep(.ant-tabs-tab) {
  margin: 0;
  padding: 10px 16px;
  border-radius: 7px;
  font-weight: 750;
}

.result-tabs :deep(.ant-tabs-tab + .ant-tabs-tab) {
  margin-left: 4px;
}

.result-tabs :deep(.ant-tabs-tab-active) {
  background: #0f766e;
}

.result-tabs :deep(.ant-tabs-tab-active .ant-tabs-tab-btn) {
  color: #ffffff;
}

.result-tabs :deep(.ant-tabs-ink-bar) {
  display: none;
}

.overview-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.9fr);
  gap: 16px;
}

.weather-panel-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}

.content-card :deep(.ant-card-body) {
  padding: clamp(18px, 3vw, 28px);
}

.section-heading {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 18px;
}

.section-heading span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
  text-transform: uppercase;
}

.day-board,
.route-timeline,
.weather-grid {
  display: grid;
  gap: 14px;
}

.day-board {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.day-summary-card,
.info-panel,
.weather-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.day-summary-card {
  padding: 18px;
}

.day-summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.day-summary-head span {
  color: #0f766e;
  font-weight: 850;
}

.day-summary-head strong {
  color: #111827;
}

.day-summary-card p,
.assistant-card p,
.day-context p {
  color: #64748b;
  line-height: 1.7;
}

.day-summary-card button {
  width: 100%;
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #f8fafc;
  color: #0f766e;
  font-weight: 800;
  cursor: pointer;
}

.summary-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-pills span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #edf2f7;
  color: #334155;
  font-size: 12px;
  font-weight: 750;
}

.assistant-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 18px;
}

.assistant-grid div {
  padding: 14px;
  border-radius: 8px;
  background: #f8fafc;
}

.assistant-grid strong,
.assistant-grid span {
  display: block;
}

.assistant-grid strong {
  color: #0f766e;
  font-size: 24px;
}

.assistant-grid span {
  color: #64748b;
  font-size: 12px;
}

.collapse-day-header {
  display: grid;
  grid-template-columns: 90px 1fr auto;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.collapse-day-header span {
  color: #0f766e;
  font-weight: 850;
}

.collapse-day-header strong {
  color: #111827;
}

.collapse-day-header small {
  color: #64748b;
}

.day-detail {
  padding: 4px 0 18px;
}

.day-context {
  padding: 16px;
  border-radius: 8px;
  background: #f8fafc;
}

.route-timeline {
  position: relative;
  margin-top: 18px;
}

.route-timeline::before {
  position: absolute;
  top: 18px;
  bottom: 18px;
  left: 19px;
  width: 2px;
  content: '';
  background: #dbe3ea;
}

.route-stop {
  position: relative;
  display: grid;
  grid-template-columns: 40px 88px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.route-stop.draggable {
  cursor: grab;
}

.route-stop-marker {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
}

.route-stop-marker span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 999px;
  background: #0f766e;
  color: #ffffff;
  font-weight: 850;
}

.route-stop-thumb {
  width: 88px;
  height: 72px;
  overflow: hidden;
  border-radius: 8px;
  background: #e2e8f0;
}

.route-stop-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.route-stop-main {
  min-width: 0;
}

.route-stop-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.route-stop-head h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.route-stop-head p {
  max-width: 760px;
  margin: 8px 0 0;
  color: #64748b;
  line-height: 1.7;
}

.route-stop-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.route-stop-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  padding: 6px 9px;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  font-weight: 650;
}

.route-stop-meta span:first-child {
  max-width: min(100%, 520px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.route-stop-meta :deep(svg) {
  flex: 0 0 auto;
  color: #0f766e;
}

.edit-fields {
  display: grid;
  gap: 10px;
}

.field-full {
  width: 100%;
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.day-support-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
  margin-top: 18px;
}

.support-item {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.support-item summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 82px;
  padding: 16px;
  cursor: pointer;
  list-style: none;
}

.support-item summary::-webkit-details-marker {
  display: none;
}

.support-item summary::after {
  content: '收起';
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
}

.support-item:not([open]) summary::after {
  content: '展开';
}

.support-item summary > :deep(svg) {
  color: #0f766e;
  font-size: 20px;
}

.support-item span,
.support-item strong,
.support-item small {
  display: block;
}

.support-item span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 850;
}

.support-item strong {
  color: #111827;
  line-height: 1.5;
}

.support-item summary small {
  margin-top: 5px;
  overflow: hidden;
  color: #64748b;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.support-detail {
  flex: 1;
  margin: 0 16px 16px 48px;
  padding: 14px;
  border-radius: 8px;
  background: #ffffff;
}

.support-detail p,
.support-detail small {
  color: #64748b;
  line-height: 1.5;
}

.support-detail p,
.support-detail small {
  margin: 0;
}

.hotel-detail-list,
.meal-detail-list {
  display: grid;
  gap: 10px;
  min-height: 312px;
}

.hotel-detail-item,
.meal-detail-item {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.hotel-detail-item strong,
.meal-detail-item strong,
.meal-detail-item p,
.meal-detail-item small {
  display: block;
}

.hotel-detail-item span,
.meal-detail-item span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 850;
}

.hotel-detail-item strong {
  color: #334155;
}

.meal-detail-item strong {
  margin-top: 3px;
}

.meal-detail-item p {
  margin-top: 0;
}

.meal-detail-item small {
  margin-top: 5px;
}

.map-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
}

.map-heading {
  flex-direction: row;
  justify-content: space-between;
  align-items: flex-start;
}

.amap-container {
  width: 100%;
  height: 620px;
  border-radius: 8px;
  background: #e2e8f0;
  overflow: hidden;
}

.stop-index {
  display: grid;
  gap: 10px;
  max-height: 620px;
  overflow: auto;
  padding-right: 4px;
}

.stop-index button {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.stop-index button:hover {
  border-color: #0f766e;
  background: #eefaf7;
}

.stop-index span {
  color: #f97316;
  font-size: 12px;
  font-weight: 850;
}

.stop-index strong {
  color: #111827;
}

.stop-index small {
  color: #64748b;
  line-height: 1.5;
}

.weather-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.weather-card {
  display: grid;
  gap: 16px;
  padding: 18px;
  background: #ffffff;
}

.weather-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.weather-card-head span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #e8f5f3;
  color: #0f766e;
}

.weather-card-head strong {
  color: #111827;
  font-size: 15px;
}

.weather-temp-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.weather-temp-row div {
  min-width: 0;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.weather-temp-row span,
.weather-temp-row small {
  display: block;
  color: #64748b;
}

.weather-temp-row span {
  font-size: 12px;
  font-weight: 800;
}

.weather-temp-row strong {
  display: block;
  margin: 5px 0 2px;
  color: #0f766e;
  font-size: 22px;
}

.weather-card p {
  margin: 0;
  color: #334155;
  font-size: 13px;
}

.weather-advice {
  padding: 12px;
  border-radius: 8px;
  background: #eefaf7;
}

.weather-advice strong,
.weather-advice span {
  display: block;
}

.weather-advice strong {
  color: #0f766e;
  font-size: 12px;
}

.weather-advice span {
  margin-top: 5px;
  color: #334155;
  line-height: 1.6;
}

.weather-note-card {
  position: sticky;
  top: 84px;
}

.weather-tips {
  display: grid;
  gap: 12px;
}

.weather-tips div {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.weather-tips strong,
.weather-tips span {
  display: block;
}

.weather-tips strong {
  color: #111827;
}

.weather-tips span {
  margin-top: 6px;
  color: #64748b;
  line-height: 1.7;
}

.local-guide {
  display: grid;
  gap: 16px;
}

.local-hero-card {
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.08), rgba(249, 115, 22, 0.08)),
    #ffffff;
}

.local-hero-card p {
  max-width: 900px;
  margin: 0;
  color: #64748b;
  line-height: 1.8;
}

.back-top-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 118, 110, 0.32);
}

:deep(.ant-collapse-item) {
  margin-bottom: 12px;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  background: #ffffff;
}

:deep(.ant-collapse-header) {
  padding: 16px 18px !important;
}

:deep(.ant-collapse-content-box) {
  padding: 0 18px 18px !important;
}

@media (max-width: 1180px) {
  .workspace,
  .overview-layout,
  .weather-panel-grid,
  .map-layout {
    grid-template-columns: 1fr;
  }

  .weather-note-card {
    position: static;
  }

  .insight-rail {
    position: static;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .result-page {
    padding-top: 16px;
  }

  .hero-topline {
    flex-direction: column;
  }

  .action-bar {
    justify-content: flex-start;
  }

  .day-board,
  .route-timeline,
  .day-support-strip,
  .insight-rail,
  .weather-temp-row,
  .weather-grid {
    grid-template-columns: 1fr;
  }

  .route-stop {
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .route-stop-thumb {
    display: none;
  }

  .route-stop-head {
    flex-direction: column;
  }

  .support-detail {
    margin-left: 16px;
  }

  .hotel-detail-item,
  .meal-detail-item {
    grid-template-columns: 1fr;
  }

  .amap-container,
  .stop-index {
    height: 460px;
    max-height: 460px;
  }
}

@media (max-width: 560px) {
  .result-hero {
    min-height: 560px;
  }

  .hero-content h1 {
    font-size: 34px;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .collapse-day-header {
    grid-template-columns: 1fr;
  }
}
</style>
