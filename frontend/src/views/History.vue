<template>
  <div class="history-container">
    <div class="history-header">
      <div>
        <h1 class="title">历史旅行规划</h1>
        <p class="subtitle">查看并重新打开之前生成的旅行计划</p>
      </div>
      <a-space>
        <a-button @click="goHome">返回首页</a-button>
        <a-popconfirm
          title="确认清空全部历史记录吗？"
          ok-text="确认"
          cancel-text="取消"
          @confirm="clearAll"
        >
          <a-button danger :disabled="historyList.length === 0">清空历史</a-button>
        </a-popconfirm>
      </a-space>
    </div>

    <a-empty v-if="historyList.length === 0" description="暂无历史记录" />

    <a-list v-else :data-source="historyList" :grid="{ gutter: 16, column: 2 }">
      <template #renderItem="{ item }">
        <a-list-item>
          <a-card :title="`${item.city} ${item.travel_days}天行程`" class="history-card">
            <p><strong>日期:</strong> {{ item.start_date }} 至 {{ item.end_date }}</p>
            <p><strong>偏好:</strong> {{ item.preferences?.length ? item.preferences.join(' / ') : '未设置' }}</p>
            <p><strong>交通:</strong> {{ item.transportation || '未设置' }}</p>
            <p><strong>住宿:</strong> {{ item.accommodation || '未设置' }}</p>
            <p><strong>预算:</strong> {{ item.budget_per_person ? `${item.budget_per_person}元/人` : '未设置' }}</p>
            <p><strong>节奏:</strong> {{ item.travel_pace || '未设置' }}</p>
            <p><strong>同行:</strong> {{ item.companions || '未设置' }}</p>
            <p><strong>最后更新:</strong> {{ formatTime(item.updatedAt) }}</p>

            <a-space>
              <a-button type="primary" @click="openHistory(item.id)">查看</a-button>
              <a-popconfirm
                title="确认删除这条历史记录吗？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="removeHistory(item.id)"
              >
                <a-button danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </a-card>
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import type { TripHistoryItem } from '@/types'
import {
  clearTripHistory,
  deleteTripHistory,
  getTripHistoryById,
  getTripHistoryList,
  setActiveHistoryId
} from '@/services/history'

const router = useRouter()
const historyList = ref<TripHistoryItem[]>([])

const loadHistory = () => {
  historyList.value = getTripHistoryList()
}

onMounted(() => {
  loadHistory()
})

const goHome = () => {
  router.push('/')
}

const openHistory = (id: string) => {
  const item = getTripHistoryById(id)
  if (!item) {
    message.error('该历史记录不存在或已被删除')
    loadHistory()
    return
  }

  sessionStorage.setItem('tripPlan', JSON.stringify(item.data))
  setActiveHistoryId(item.id)
  router.push({ path: '/result', query: { historyId: item.id } })
}

const removeHistory = (id: string) => {
  deleteTripHistory(id)
  loadHistory()
  message.success('历史记录已删除')
}

const clearAll = () => {
  clearTripHistory()
  loadHistory()
  message.success('历史记录已清空')
}

const formatTime = (iso: string): string => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.history-container {
  max-width: 1200px;
  margin: 0 auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title {
  margin: 0;
  font-size: 30px;
}

.subtitle {
  margin: 8px 0 0;
  color: #666;
}

.history-card {
  border-radius: 10px;
}
</style>
