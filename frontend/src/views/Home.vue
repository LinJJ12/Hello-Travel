<template>
  <main class="home-page">
    <section class="hero-section">
      <div class="hero-media" aria-hidden="true">
        <div class="route-map">
          <div class="route-line"></div>
          <span class="map-pin pin-a">北京</span>
          <span class="map-pin pin-b">西安</span>
          <span class="map-pin pin-c">成都</span>
          <div class="live-card">
            <span class="live-dot"></span>
            多智能体正在协同规划
          </div>
        </div>
      </div>

      <div class="hero-copy">
        <p class="eyebrow">AI Travel Agent Workspace</p>
        <h1>从一句想法到可执行行程</h1>
        <p class="hero-subtitle">
          Hello-Travel Agent 将目的地、交通、住宿、景点、天气和预算整合成一份可落地的旅行计划，让旅行灵感快速变成清晰路线。
        </p>
        <div class="hero-actions">
          <a-button type="primary" size="large" class="hero-button" @click="scrollToPlanner">
            开始规划
          </a-button>
          <a-button size="large" class="ghost-button" @click="goHistory">
            查看历史
          </a-button>
        </div>
      </div>

      <div class="hero-metrics">
        <div v-for="metric in heroMetrics" :key="metric.label" class="metric-item">
          <strong>{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
        </div>
      </div>
    </section>

    <section class="intelligence-strip" aria-label="智能体能力">
      <div v-for="agent in agentModules" :key="agent.title" class="agent-chip">
        <component :is="agent.icon" />
        <div>
          <strong>{{ agent.title }}</strong>
          <span>{{ agent.description }}</span>
        </div>
      </div>
    </section>

    <section id="planner" class="planner-layout">
      <div class="planner-main">
        <a-card class="planner-card" :bordered="false">
          <template #title>
            <div class="card-title">
              <span>旅行需求采集</span>
              <small>越具体，生成的路线越像真正能出发的计划</small>
            </div>
          </template>

          <a-form :model="formData" layout="vertical" @finish="handleSubmit">
            <div class="form-section">
              <div class="section-heading">
                <span class="section-index">01</span>
                <div>
                  <h2>目的地与日期</h2>
                  <p>支持单城市、多城市串联和自由文本补充。</p>
                </div>
              </div>

              <a-row :gutter="[16, 8]">
                <a-col :xs="24" :lg="10">
                  <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地城市' }]">
                    <template #label>
                      <span class="form-label">目的地城市</span>
                    </template>
                    <a-input
                      v-model:value="formData.city"
                      placeholder="例如：北京、成都、厦门"
                      size="large"
                    />
                  </a-form-item>
                </a-col>

                <a-col :xs="24" :sm="12" :lg="7">
                  <a-form-item name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
                    <template #label>
                      <span class="form-label">开始日期</span>
                    </template>
                    <a-date-picker
                      v-model:value="formData.start_date"
                      class="field-full"
                      size="large"
                      placeholder="选择日期"
                    />
                  </a-form-item>
                </a-col>

                <a-col :xs="24" :sm="12" :lg="7">
                  <a-form-item name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
                    <template #label>
                      <span class="form-label">结束日期</span>
                    </template>
                    <a-date-picker
                      v-model:value="formData.end_date"
                      class="field-full"
                      size="large"
                      placeholder="选择日期"
                    />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-form-item name="destinations_text">
                <template #label>
                  <span class="form-label">多城市路线</span>
                </template>
                <a-textarea
                  v-model:value="formData.destinations_text"
                  :rows="2"
                  placeholder="可选，例如：杭州、苏州、上海。留空则使用目的地城市。"
                />
              </a-form-item>
            </div>

            <div class="form-section">
              <div class="section-heading">
                <span class="section-index">02</span>
                <div>
                  <h2>偏好与约束</h2>
                  <p>让规划器同时考虑路线效率、预算上限和同行体验。</p>
                </div>
              </div>

              <a-row :gutter="[16, 8]">
                <a-col :xs="24" :lg="12">
                  <a-form-item name="transportation">
                    <template #label>
                      <span class="form-label">交通方式</span>
                    </template>
                    <a-segmented v-model:value="formData.transportation" :options="transportationOptions" />
                  </a-form-item>
                </a-col>

                <a-col :xs="24" :lg="12">
                  <a-form-item name="accommodation">
                    <template #label>
                      <span class="form-label">住宿偏好</span>
                    </template>
                    <a-select v-model:value="formData.accommodation" size="large" class="field-full">
                      <a-select-option value="经济型酒店">经济型酒店</a-select-option>
                      <a-select-option value="舒适型酒店">舒适型酒店</a-select-option>
                      <a-select-option value="豪华酒店">豪华酒店</a-select-option>
                      <a-select-option value="民宿">民宿</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>

              <a-form-item name="preferences">
                <template #label>
                  <span class="form-label">旅行偏好</span>
                </template>
                <a-checkbox-group v-model:value="formData.preferences" class="preference-grid">
                  <a-checkbox
                    v-for="item in preferenceOptions"
                    :key="item.value"
                    :value="item.value"
                    class="preference-option"
                  >
                    <span class="preference-title">{{ item.label }}</span>
                    <span class="preference-desc">{{ item.description }}</span>
                  </a-checkbox>
                </a-checkbox-group>
              </a-form-item>

              <a-row :gutter="[16, 8]">
                <a-col :xs="24" :lg="8">
                  <a-form-item name="budget_per_person">
                    <template #label>
                      <span class="form-label">人均预算</span>
                    </template>
                    <a-input-number
                      v-model:value="formData.budget_per_person"
                      class="field-full"
                      size="large"
                      :min="0"
                      :step="100"
                      placeholder="例如：3000"
                      addon-after="元"
                    />
                  </a-form-item>
                </a-col>

                <a-col :xs="24" :lg="8">
                  <a-form-item name="travel_pace">
                    <template #label>
                      <span class="form-label">旅行节奏</span>
                    </template>
                    <a-segmented v-model:value="formData.travel_pace" :options="paceOptions" />
                  </a-form-item>
                </a-col>

                <a-col :xs="24" :lg="8">
                  <a-form-item name="companions">
                    <template #label>
                      <span class="form-label">同行人群</span>
                    </template>
                    <a-select v-model:value="formData.companions" size="large" class="field-full">
                      <a-select-option value="独自/不限">独自/不限</a-select-option>
                      <a-select-option value="情侣">情侣</a-select-option>
                      <a-select-option value="朋友">朋友</a-select-option>
                      <a-select-option value="亲子家庭">亲子家庭</a-select-option>
                      <a-select-option value="老人同行">老人同行</a-select-option>
                      <a-select-option value="商务出行">商务出行</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>
            </div>

            <div class="form-section compact">
              <div class="section-heading">
                <span class="section-index">03</span>
                <div>
                  <h2>细节补充</h2>
                  <p>把不能妥协的要求写在这里。</p>
                </div>
              </div>

              <a-form-item name="dietary_restrictions">
                <template #label>
                  <span class="form-label">饮食禁忌或偏好</span>
                </template>
                <a-input
                  v-model:value="formData.dietary_restrictions"
                  size="large"
                  placeholder="例如：不吃海鲜、清真、素食、少辣"
                />
              </a-form-item>

              <a-form-item name="free_text_input">
                <a-textarea
                  v-model:value="formData.free_text_input"
                  placeholder="例如：想看日落，预算控制在 3000 元以内，尽量不要安排太赶。"
                  :rows="4"
                  size="large"
                />
              </a-form-item>
            </div>

            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              size="large"
              block
              class="submit-button"
            >
              {{ loading ? '正在生成行程' : '生成旅行计划' }}
            </a-button>
          </a-form>
        </a-card>
      </div>

      <aside class="planner-sidebar">
        <a-card class="summary-card glass-card" :bordered="false">
          <div class="summary-header">
            <p class="eyebrow">Plan Brief</p>
            <h2>当前规划摘要</h2>
          </div>

          <div class="summary-list">
            <div v-for="item in summaryItems" :key="item.label" class="summary-item">
              <span class="summary-label">{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>

          <div class="selected-tags">
            <a-tag v-for="item in formData.preferences" :key="item" color="green">
              {{ item }}
            </a-tag>
            <span v-if="formData.preferences.length === 0" class="empty-tags">尚未选择旅行偏好</span>
          </div>
        </a-card>

        <a-card class="status-card glass-card" :bordered="false">
          <div class="status-top">
            <div>
              <p class="eyebrow">Generation</p>
              <h2>{{ loading ? '正在规划中' : '准备就绪' }}</h2>
            </div>
            <span class="status-dot" :class="{ active: loading }"></span>
          </div>

          <a-progress
            :percent="loading ? loadingProgress : 0"
            :show-info="false"
            :stroke-color="{ '0%': '#0f766e', '100%': '#2563eb' }"
            :trail-color="'#dbe3ea'"
          />

          <p class="status-text">
            {{ loading ? loadingStatus : '提交后会轮询后端异步任务，生成期间可观察实时阶段。' }}
          </p>
        </a-card>

        <a-card class="route-card glass-card" :bordered="false">
          <div class="card-title small">
            <span>路线与预算预览</span>
            <small>基于当前输入即时更新</small>
          </div>

          <div class="mini-route">
            <div v-for="(city, index) in previewCities" :key="`${city}-${index}`" class="route-stop">
              <span>{{ index + 1 }}</span>
              <strong>{{ city }}</strong>
            </div>
          </div>

          <div class="budget-meter">
            <div>
              <span>预算清晰度</span>
              <strong>{{ budgetClarity }}%</strong>
            </div>
            <a-progress :percent="budgetClarity" :show-info="false" stroke-color="#f97316" />
          </div>
        </a-card>
      </aside>
    </section>

    <section class="comparison-section">
      <div class="section-title">
        <p class="eyebrow">Decision Board</p>
        <h2>像产品级旅行 Agent 一样组织信息</h2>
      </div>

      <div class="comparison-grid">
        <article v-for="card in decisionCards" :key="card.title" class="decision-card">
          <component :is="card.icon" />
          <h3>{{ card.title }}</h3>
          <p>{{ card.description }}</p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  AimOutlined,
  ApartmentOutlined,
  CalendarOutlined,
  CloudOutlined,
  DeploymentUnitOutlined,
  DollarOutlined,
  EnvironmentOutlined,
  ThunderboltOutlined
} from '@ant-design/icons-vue'
import { generateTripPlan } from '@/services/api'
import { saveTripToHistory } from '@/services/history'
import type { TripFormData } from '@/types'
import type { Dayjs } from 'dayjs'

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const transportationOptions = ['公共交通', '自驾', '步行', '混合']
const paceOptions = ['轻松', '适中', '紧凑']

const heroMetrics = [
  { value: 'POI', label: '景点检索' },
  { value: 'Route', label: '路线编排' },
  { value: 'Weather', label: '天气融合' },
  { value: 'Budget', label: '预算估算' }
]

const agentModules = [
  { title: '目的地研究员', description: '检索城市、景点与路线线索', icon: EnvironmentOutlined },
  { title: '行程编排师', description: '按天拆解节奏和交通', icon: CalendarOutlined },
  { title: '预算审计员', description: '汇总门票、住宿、餐饮和出行', icon: DollarOutlined },
  { title: '天气观察员', description: '把天气变化纳入安排', icon: CloudOutlined }
]

const decisionCards = [
  { title: '多方案取舍', description: '把轻松、均衡、紧凑三种节奏转化为不同的路线密度。', icon: DeploymentUnitOutlined },
  { title: '地图优先', description: '规划结果围绕 POI 坐标、路线顺序和每日动线呈现。', icon: AimOutlined },
  { title: '真实约束', description: '预算、饮食、同行人群和住宿偏好会进入同一份提示上下文。', icon: ApartmentOutlined },
  { title: '智能体协作感', description: '让用户在生成前就能理解系统会怎样分工规划。', icon: ThunderboltOutlined }
]

const preferenceOptions = [
  { value: '历史文化', label: '历史文化', description: '博物馆、古迹、城市故事' },
  { value: '自然风光', label: '自然风光', description: '山海湖泊、公园与户外' },
  { value: '美食', label: '美食', description: '本地小吃、餐厅与夜市' },
  { value: '购物', label: '购物', description: '商圈、市集与伴手礼' },
  { value: '艺术', label: '艺术', description: '展览、建筑与演出' },
  { value: '休闲', label: '休闲', description: '慢节奏、咖啡与散步' }
]

type TripFormState = Omit<TripFormData, 'start_date' | 'end_date'> & {
  start_date: Dayjs | null
  end_date: Dayjs | null
  destinations_text: string
}

const formData = reactive<TripFormState>({
  city: '',
  destinations: [],
  destinations_text: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '舒适型酒店',
  preferences: [],
  budget_per_person: undefined,
  travel_pace: '适中',
  companions: '独自/不限',
  dietary_restrictions: '',
  free_text_input: ''
})

const dateSummary = computed(() => {
  if (!formData.start_date || !formData.end_date) return '待选择'
  return `${formData.start_date.format('YYYY-MM-DD')} 至 ${formData.end_date.format('YYYY-MM-DD')}`
})

const parsedDestinations = computed(() => {
  const source = formData.destinations_text || formData.city
  return source
    .split(/[,\n，、]/)
    .map(item => item.trim())
    .filter(Boolean)
})

const destinationSummary = computed(() => {
  const destinations = parsedDestinations.value
  if (destinations.length === 0) return '待填写'
  return destinations.join(' → ')
})

const previewCities = computed(() => {
  const cities = parsedDestinations.value
  return cities.length > 0 ? cities.slice(0, 4) : ['目的地', '景点', '住宿', '返程']
})

const budgetClarity = computed(() => {
  let score = 28
  if (formData.budget_per_person) score += 30
  if (formData.accommodation) score += 12
  if (formData.transportation) score += 12
  if (formData.preferences.length > 0) score += 10
  if (formData.free_text_input || formData.dietary_restrictions) score += 8
  return Math.min(score, 100)
})

const summaryItems = computed(() => [
  { label: '目的地', value: destinationSummary.value },
  { label: '日期', value: dateSummary.value },
  { label: '天数', value: `${formData.travel_days} 天` },
  { label: '交通', value: formData.transportation },
  { label: '住宿', value: formData.accommodation },
  { label: '预算', value: formData.budget_per_person ? `${formData.budget_per_person} 元/人` : '未指定' },
  { label: '节奏', value: formData.travel_pace || '未指定' },
  { label: '同行', value: formData.companions || '未指定' }
])

watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (!start || !end) return

  const days = end.diff(start, 'day') + 1
  if (days > 0 && days <= 30) {
    formData.travel_days = days
  } else if (days > 30) {
    message.warning('旅行天数不能超过 30 天')
    formData.end_date = null
  } else {
    message.warning('结束日期不能早于开始日期')
    formData.end_date = null
  }
})

const scrollToPlanner = () => {
  document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const goHistory = () => {
  router.push('/history')
}

const handleSubmit = async () => {
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择完整日期')
    return
  }

  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = '正在整理旅行需求...'

  const progressInterval = window.setInterval(() => {
    if (loadingProgress.value >= 88) return

    loadingProgress.value += 4
    if (loadingProgress.value <= 30) {
      loadingStatus.value = '正在搜索城市景点与位置...'
    } else if (loadingProgress.value <= 50) {
      loadingStatus.value = '正在匹配天气、交通和住宿...'
    } else if (loadingProgress.value <= 70) {
      loadingStatus.value = '正在安排每日节奏与餐饮...'
    } else {
      loadingStatus.value = '正在生成最终行程...'
    }
  }, 500)

  try {
    const requestData: TripFormData = {
      city: parsedDestinations.value[0] || formData.city,
      destinations: parsedDestinations.value,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      budget_per_person: formData.budget_per_person,
      travel_pace: formData.travel_pace,
      companions: formData.companions,
      dietary_restrictions: formData.dietary_restrictions,
      free_text_input: formData.free_text_input
    }

    const response = await generateTripPlan(requestData, (progress) => {
      if (typeof progress.progress === 'number') {
        loadingProgress.value = Math.max(loadingProgress.value, Math.min(progress.progress, 95))
      }
      loadingStatus.value = progress.message || progress.stage || loadingStatus.value
    })

    window.clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '行程生成完成'

    if (response.success && response.data) {
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
      saveTripToHistory(response.data, requestData)
      message.success('旅行计划生成成功')

      window.setTimeout(() => {
        router.push('/result')
      }, 500)
    } else {
      message.error(response.message || '生成失败')
    }
  } catch (error: any) {
    window.clearInterval(progressInterval)
    message.error(error.message || '生成旅行计划失败，请稍后重试')
  } finally {
    window.setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.home-page {
  width: min(1480px, 100%);
  margin: 0 auto;
  padding: 28px clamp(16px, 4vw, 44px) 64px;
}

.hero-section {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: clamp(24px, 4vw, 48px);
  min-height: 430px;
  padding: clamp(26px, 4vw, 44px);
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  overflow: hidden;
}

.hero-copy {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 760px;
}

.eyebrow {
  margin: 0 0 10px;
  color: inherit;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
  opacity: 0.7;
}

.hero-copy h1 {
  margin: 0;
  color: #111827;
  font-size: clamp(36px, 5vw, 64px);
  font-weight: 850;
  line-height: 1.02;
  letter-spacing: 0;
}

.hero-subtitle {
  max-width: 700px;
  margin: 22px 0 0;
  color: #475569;
  font-size: 18px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 32px;
}

.hero-button,
.ghost-button {
  min-width: 128px;
  height: 46px;
  border-radius: 8px;
  font-weight: 800;
}

.hero-button {
  background: #0f766e;
  border-color: #0f766e;
  box-shadow: none;
}

.hero-button:hover {
  background: #0d9488;
  border-color: #0d9488;
}

.ghost-button {
  border-color: #dbe3ea;
  background: #ffffff;
  color: #334155;
}

.ghost-button:hover {
  border-color: #0f766e;
  background: #eefaf7;
  color: #0f766e;
}

.hero-media {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
}

.route-map {
  position: relative;
  width: 100%;
  min-height: 360px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.72), rgba(15, 23, 42, 0.18) 58%, rgba(249, 115, 22, 0.14)),
    url('https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=85');
  background-position: center;
  background-size: cover;
  overflow: hidden;
}

.route-map::after {
  position: absolute;
  inset: 0;
  content: '';
  background:
    linear-gradient(180deg, transparent 0%, rgba(15, 23, 42, 0.2) 100%),
    radial-gradient(circle at 22% 20%, rgba(255, 255, 255, 0.2), transparent 26%);
}

.route-line {
  position: absolute;
  z-index: 1;
  inset: 64px 52px;
  border: 3px solid rgba(255, 255, 255, 0.78);
  border-left: 0;
  border-bottom: 0;
  border-radius: 8px;
  transform: skew(-12deg);
}

.map-pin {
  position: absolute;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  background: #ffffff;
  color: #0f172a;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.22);
}

.pin-a {
  top: 56px;
  left: 46px;
}

.pin-b {
  top: 172px;
  right: 64px;
}

.pin-c {
  bottom: 60px;
  left: 35%;
}

.live-card {
  position: absolute;
  z-index: 2;
  right: 22px;
  bottom: 22px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  border: 1px solid #dbe3ea;
  font-size: 13px;
  font-weight: 700;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.16);
}

.hero-metrics {
  position: static;
  grid-column: 1 / -1;
  z-index: 2;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  max-width: none;
  margin-top: 8px;
}

.metric-item {
  padding: 14px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #f8fafc;
}

.metric-item strong,
.metric-item span {
  display: block;
}

.metric-item strong {
  color: #111827;
  font-size: 18px;
}

.metric-item span {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.intelligence-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.agent-chip {
  display: flex;
  gap: 12px;
  min-height: 86px;
  padding: 18px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
}

.agent-chip :deep(svg) {
  flex: 0 0 auto;
  color: #0f766e;
  font-size: 22px;
}

.agent-chip strong,
.agent-chip span {
  display: block;
}

.agent-chip strong {
  color: #111827;
  font-size: 15px;
}

.agent-chip span {
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.planner-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 20px;
  margin-top: 22px;
  align-items: start;
}

.planner-card,
.glass-card,
.decision-card {
  border-radius: 8px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
}

.planner-card :deep(.ant-card-head) {
  border-bottom: 1px solid #e5e7eb;
}

.planner-card :deep(.ant-card-body) {
  padding: clamp(20px, 3vw, 32px);
}

.card-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title span {
  color: #111827;
  font-size: 20px;
  font-weight: 800;
}

.card-title small {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

.card-title.small span {
  font-size: 18px;
}

.form-section {
  padding-bottom: 26px;
  margin-bottom: 26px;
  border-bottom: 1px solid #e5e7eb;
}

.form-section.compact {
  margin-bottom: 20px;
}

.section-heading {
  display: flex;
  gap: 14px;
  margin-bottom: 18px;
}

.section-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 30px;
  border-radius: 7px;
  background: #e8f5f3;
  color: #0f766e;
  font-size: 13px;
  font-weight: 850;
}

.section-heading h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
  line-height: 1.25;
}

.section-heading p {
  margin: 6px 0 0;
  color: #64748b;
  line-height: 1.6;
}

.form-label {
  color: #334155;
  font-weight: 700;
}

.field-full {
  width: 100%;
}

.preference-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.preference-option {
  position: relative;
  display: flex;
  min-height: 86px;
  margin: 0;
  padding: 14px 14px 14px 38px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #ffffff;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.preference-option:hover {
  border-color: #0f766e;
  background: #f8fbfb;
}

.preference-option :deep(.ant-checkbox) {
  position: absolute;
  top: 16px;
  left: 14px;
}

.preference-option :deep(span:last-child) {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preference-option:has(.ant-checkbox-checked) {
  border-color: #0f766e;
  background: #eefaf7;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.08);
}

.preference-title {
  color: #111827;
  font-weight: 800;
}

.preference-desc {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.submit-button {
  height: 54px;
  border-radius: 8px;
  background: #0f766e;
  border-color: #0f766e;
  font-size: 16px;
  font-weight: 850;
}

.submit-button:hover {
  background: #0d9488;
  border-color: #0d9488;
}

.planner-sidebar {
  position: sticky;
  top: 84px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.glass-card {
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
}

.summary-header h2,
.status-top h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.summary-header .eyebrow,
.status-top .eyebrow {
  color: #0f766e;
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}

.summary-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #edf2f7;
}

.summary-item strong {
  max-width: 220px;
  color: #111827;
  text-align: right;
  word-break: break-word;
}

.summary-label {
  color: #64748b;
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.empty-tags {
  color: #94a3b8;
  font-size: 13px;
}

.status-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.status-dot {
  width: 10px;
  height: 10px;
  margin-top: 8px;
  border-radius: 50%;
  background: #cbd5e1;
}

.status-dot.active {
  background: #0f766e;
  box-shadow: 0 0 0 6px rgba(15, 118, 110, 0.14);
}

.status-text {
  min-height: 44px;
  margin: 14px 0 0;
  color: #64748b;
  line-height: 1.6;
}

.mini-route {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
}

.route-stop {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.route-stop span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #0f766e;
  color: #ffffff;
  font-size: 12px;
  font-weight: 850;
}

.route-stop strong {
  color: #111827;
}

.budget-meter {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.budget-meter div {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #64748b;
}

.budget-meter strong {
  color: #f97316;
}

.comparison-section {
  margin-top: 24px;
  padding: 30px 0 0;
}

.section-title h2 {
  margin: 0;
  color: #111827;
  font-size: clamp(24px, 3vw, 34px);
}

.section-title .eyebrow {
  color: #0f766e;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.decision-card {
  padding: 20px;
  border: 1px solid #dbe3ea;
  background: #ffffff;
}

.decision-card :deep(svg) {
  color: #f97316;
  font-size: 24px;
}

.decision-card h3 {
  margin: 14px 0 8px;
  color: #111827;
  font-size: 17px;
}

.decision-card p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

:deep(.ant-input),
:deep(.ant-picker),
:deep(.ant-select-selector),
:deep(.ant-input-affix-wrapper),
:deep(.ant-segmented) {
  border-radius: 8px;
}

:deep(.ant-segmented) {
  width: 100%;
  padding: 4px;
  background: #f1f5f9;
}

:deep(.ant-segmented-group) {
  width: 100%;
}

:deep(.ant-segmented-item) {
  flex: 1;
  min-height: 34px;
  border-radius: 6px;
  line-height: 34px;
}

:deep(.ant-segmented-item-selected) {
  color: #0f766e;
  font-weight: 800;
}

@media (max-width: 1180px) {
  .hero-section,
  .planner-layout {
    grid-template-columns: 1fr;
  }

  .hero-metrics {
    position: static;
    grid-column: 1 / -1;
    max-width: none;
  }

  .planner-sidebar {
    position: static;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .intelligence-strip,
  .comparison-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .home-page {
    padding-top: 16px;
  }

  .hero-section {
    min-height: auto;
  }

  .hero-media {
    display: none;
  }

  .hero-metrics,
  .intelligence-strip,
  .planner-sidebar,
  .preference-grid,
  .comparison-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .hero-copy h1 {
    font-size: 34px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .section-heading {
    flex-direction: column;
  }

  .preference-option {
    min-height: auto;
  }
}
</style>
