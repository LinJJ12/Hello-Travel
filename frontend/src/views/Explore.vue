<template>
  <main class="explore-page">
    <section class="explore-header">
      <div>
        <p class="eyebrow">Interactive Local Map</p>
        <h1>互动地图</h1>
        <p>直接搜索城市、地区或地点，也可以按主题查看自然风光、美食、历史文化、艺术休闲和购物休闲。</p>
      </div>

      <a-form class="search-bar" layout="inline" @finish="handleSearch">
        <a-form-item>
          <a-input
            v-model:value="cityInput"
            size="large"
            placeholder="输入城市/地区，例如：成都、杭州西湖"
            allow-clear
            @pressEnter="handleSearch"
          />
        </a-form-item>
        <a-form-item>
          <a-input
            v-model:value="keywordInput"
            size="large"
            placeholder="可选关键词，例如：茶馆"
            allow-clear
            @pressEnter="handleSearch"
          />
        </a-form-item>
        <a-button type="primary" size="large" html-type="submit" :loading="loading" @click="handleSearch">
          <SearchOutlined />
          搜索
        </a-button>
      </a-form>
    </section>

    <section class="explore-shell">
      <aside class="theme-panel">
        <button
          v-for="theme in themeOptions"
          :key="theme.key"
          type="button"
          class="theme-button"
          :class="{ active: activeTheme === theme.key }"
          @click="selectTheme(theme.key)"
        >
          <component :is="theme.icon" class="theme-icon" />
          <span class="theme-copy">
            <strong>{{ theme.label }}</strong>
            <small>{{ theme.description }}</small>
          </span>
        </button>
      </aside>

      <section class="map-panel">
        <div class="map-toolbar">
          <div>
            <strong>{{ city || '选择城市' }}</strong>
            <span>{{ loading ? '正在检索地点' : `${places.length} 个地点` }}</span>
          </div>
          <a-button @click="refreshPlaces" :disabled="!city" :loading="loading">
            <ReloadOutlined />
            刷新
          </a-button>
        </div>
        <div id="explore-amap" class="explore-map"></div>
        <div v-if="activeTheme === 'none' && !keywordInput && places.length === 0" class="map-empty">
          <strong>中国地图视野</strong>
          <span>可以直接搜索城市/地区，或选择主题查看地点标记</span>
        </div>
      </section>

      <aside class="places-panel">
        <div class="places-head">
          <div>
            <span>Places</span>
            <h2>地点列表</h2>
          </div>
          <a-tag color="green">{{ resultModeLabel }}</a-tag>
        </div>

        <a-empty
          v-if="!loading && places.length === 0"
          :description="activeTheme === 'none' ? '当前未显示地点。输入城市/地区后点击搜索即可查看结果' : '暂无地点结果，请换个主题或关键词'"
        />

        <div v-else class="places-list">
          <button
            v-for="place in places"
            :key="getPlaceKey(place)"
            type="button"
            :class="{ active: selectedPlace && getPlaceKey(selectedPlace) === getPlaceKey(place) }"
            @click="selectPlace(place)"
          >
            <strong>{{ place.name }}</strong>
            <span>{{ place.address || '暂无地址' }}</span>
            <small>{{ place.themeLabel }} · {{ place.keyword }}</small>
          </button>
        </div>

        <div v-if="selectedPlace" class="place-detail">
          <p class="eyebrow dark">Selected</p>
          <h3>{{ selectedPlace.name }}</h3>
          <p>{{ selectedPlace.address || '暂无地址' }}</p>
          <div class="detail-grid">
            <div>
              <span>类型</span>
              <strong>{{ selectedPlace.type || selectedPlace.themeLabel }}</strong>
            </div>
            <div>
              <span>来源</span>
              <strong>{{ selectedPlace.keyword }}</strong>
            </div>
          </div>
          <a-button block type="primary" @click="focusPlace(selectedPlace)">
            <AimOutlined />
            地图定位
          </a-button>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  AimOutlined,
  AppstoreOutlined,
  CoffeeOutlined,
  CompassOutlined,
  EyeInvisibleOutlined,
  PictureOutlined,
  ReadOutlined,
  ReloadOutlined,
  SearchOutlined,
  ShoppingOutlined
} from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { EXPLORE_THEMES, searchPOI, searchPOIByTheme, type ExploreThemeKey } from '@/services/api'
import type { ExplorePlace } from '@/types'

const route = useRoute()
const router = useRouter()

const city = ref('')
const cityInput = ref('')
const keywordInput = ref('')
const activeTheme = ref<ExploreThemeKey>('none')
const loading = ref(false)
const places = ref<ExplorePlace[]>([])
const selectedPlace = ref<ExplorePlace | null>(null)

let map: any = null
let mapApi: any = null
let markers: any[] = []
let searchSubmitting = false

const iconMap: Record<string, any> = {
  none: EyeInvisibleOutlined,
  all: AppstoreOutlined,
  nature: PictureOutlined,
  food: CoffeeOutlined,
  culture: ReadOutlined,
  leisure: CompassOutlined,
  shopping: ShoppingOutlined
}

const themeOptions = computed(() => [
  { key: 'none' as ExploreThemeKey, label: '都不显示', description: '隐藏所有地点标记', icon: EyeInvisibleOutlined },
  { key: 'all' as ExploreThemeKey, label: '全部主题', description: '显示全部主题地点', icon: AppstoreOutlined },
  ...EXPLORE_THEMES.map(theme => ({
    key: theme.key,
    label: theme.label,
    description: getThemeDescription(theme.key),
    icon: iconMap[theme.key] || CompassOutlined
  }))
])

const getThemeDescription = (themeKey: string) => {
  const descriptions: Record<string, string> = {
    nature: '景区、公园、山水湖泊',
    food: '餐厅、小吃、老字号',
    culture: '博物馆、古迹、寺庙',
    leisure: '艺术馆、展览、街区',
    shopping: '商圈、市集、购物中心'
  }
  return descriptions[themeKey] || '探索当地地点'
}

const activeThemeLabel = computed(() => {
  return themeOptions.value.find(theme => theme.key === activeTheme.value)?.label || '全部主题'
})

const resultModeLabel = computed(() => {
  if (places.value.some(place => place.theme === 'region')) return '地区搜索'
  if (keywordInput.value.trim()) return '关键词'
  return activeThemeLabel.value
})

onMounted(async () => {
  const queryCity = typeof route.query.city === 'string' ? route.query.city : ''
  const queryTheme = typeof route.query.theme === 'string' ? route.query.theme : ''
  city.value = queryCity
  cityInput.value = queryCity
  if (isExploreThemeKey(queryTheme)) {
    activeTheme.value = queryTheme
  }
  await nextTick()
  await initMap()
  if (city.value && activeTheme.value !== 'none') {
    await reloadPlaces()
  }
})

const isExploreThemeKey = (value: string): value is ExploreThemeKey => {
  return ['none', 'all', ...EXPLORE_THEMES.map(theme => theme.key)].includes(value)
}

const initMap = async () => {
  const container = document.getElementById('explore-amap')
  if (!container) return
  try {
    const AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_WEB_JS_KEY,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.InfoWindow']
    })
    mapApi = AMap
    map = new AMap.Map('explore-amap', {
      zoom: 4,
      center: [104.195397, 35.86166],
      viewMode: '3D'
    })
  } catch (error) {
    console.error('互动地图加载失败:', error)
    message.error('互动地图加载失败，请检查高德地图 JS Key')
  }
}

const handleSearch = async () => {
  if (searchSubmitting) return
  const nextCity = cityInput.value.trim()
  if (!nextCity) {
    message.warning('请输入城市、地区或地点')
    return
  }
  searchSubmitting = true
  city.value = nextCity
  places.value = []
  selectedPlace.value = null
  loading.value = true
  clearMarkers()
  router.replace({ path: '/explore', query: { city: city.value } })
  try {
    if (!map) {
      await nextTick()
      await initMap()
    }
    await reloadPlaces({ directSearch: true, keepLoading: true })
  } finally {
    loading.value = false
    searchSubmitting = false
  }
}

const selectTheme = async (themeKey: ExploreThemeKey) => {
  activeTheme.value = themeKey
  if (city.value) {
    router.replace({ path: '/explore', query: { city: city.value, theme: themeKey } })
  }
  if (themeKey === 'none') {
    keywordInput.value = ''
    places.value = []
    selectedPlace.value = null
    clearMarkers()
    return
  }

  if (city.value) {
    await reloadPlaces()
  } else {
    message.info('请输入城市后查看该主题地点')
  }
}

const refreshPlaces = async () => {
  await reloadPlaces({ directSearch: activeTheme.value === 'none' })
}

const reloadPlaces = async (options: { directSearch?: boolean; keepLoading?: boolean } = {}) => {
  if (!city.value) return
  const shouldDirectSearch = Boolean(options.directSearch)
  if (activeTheme.value === 'none' && !keywordInput.value.trim() && !shouldDirectSearch) {
    places.value = []
    selectedPlace.value = null
    clearMarkers()
    return
  }

  if (!options.keepLoading) loading.value = true
  selectedPlace.value = null
  try {
    if (keywordInput.value.trim() || shouldDirectSearch) {
      const keyword = keywordInput.value.trim() || city.value
      let pois = await searchPOI(keyword, city.value, !shouldDirectSearch)
      if (shouldDirectSearch && !keywordInput.value.trim() && pois.length === 0) {
        pois = await searchPOI('景点', city.value, true)
      }
      places.value = pois.map(poi => ({
        ...poi,
        theme: shouldDirectSearch && !keywordInput.value.trim() ? 'region' : 'custom',
        themeLabel: shouldDirectSearch && !keywordInput.value.trim() ? '地区搜索' : '关键词',
        keyword
      }))
    } else {
      places.value = await searchPOIByTheme(city.value, activeTheme.value)
    }
    renderMarkers()
    if (places.value[0]) {
      selectPlace(places.value[0], false)
    } else if (shouldDirectSearch) {
      message.info('暂未找到地点结果，请尝试输入更具体的地区或地点名称')
    }
  } catch (error: any) {
    console.error('地点检索失败:', error)
    places.value = []
    clearMarkers()
    message.error(error.message || '地点检索失败')
  } finally {
    if (!options.keepLoading) loading.value = false
  }
}

const clearMarkers = () => {
  if (map && markers.length > 0) {
    map.remove(markers)
  }
  markers = []
}

const renderMarkers = () => {
  if (!map || !mapApi) return
  clearMarkers()
  markers = places.value
    .filter(place => place.location?.longitude && place.location?.latitude)
    .map((place, index) => {
      const marker = new mapApi.Marker({
        position: [place.location.longitude, place.location.latitude],
        title: place.name,
        label: {
          content: `<div style="background:#0f766e;color:white;padding:5px 8px;border-radius:8px;font-size:12px;font-weight:700;">${index + 1}</div>`,
          offset: new mapApi.Pixel(0, -28)
        }
      })
      marker.on('click', () => selectPlace(place))
      return marker
    })

  if (markers.length > 0) {
    map.add(markers)
    map.setFitView(markers)
  }
}

const selectPlace = (place: ExplorePlace, openInfo = true) => {
  selectedPlace.value = place
  if (openInfo) {
    focusPlace(place)
  }
}

const focusPlace = (place: ExplorePlace) => {
  if (!map || !mapApi || !place.location) return
  const position = new mapApi.LngLat(place.location.longitude, place.location.latitude)
  map.setZoomAndCenter(15, position)
  const infoWindow = new mapApi.InfoWindow({
    content: `
      <div style="padding:12px;max-width:280px;">
        <h4 style="margin:0 0 8px 0;">${place.name}</h4>
        <p style="margin:4px 0;">${place.address || ''}</p>
        <p style="margin:4px 0;color:#0f766e;">${place.themeLabel} · ${place.keyword}</p>
      </div>
    `,
    offset: new mapApi.Pixel(0, -30),
    autoMove: false
  })
  infoWindow.open(map, position)
  window.setTimeout(() => {
    map?.setCenter(position)
  }, 80)
}

const getPlaceKey = (place: ExplorePlace) => {
  return place.id || `${place.name}-${place.address || ''}`
}
</script>

<style scoped>
.explore-page {
  width: min(1480px, 100%);
  margin: 0 auto;
  padding: 28px clamp(16px, 4vw, 44px) 56px;
}

.explore-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 26px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #ffffff;
}

.eyebrow {
  margin: 0 0 8px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
  text-transform: uppercase;
}

.eyebrow.dark {
  color: #64748b;
}

.explore-header h1 {
  margin: 0;
  color: #111827;
  font-size: clamp(32px, 4vw, 48px);
  line-height: 1.08;
}

.explore-header p:last-child {
  max-width: 640px;
  margin: 12px 0 0;
  color: #64748b;
  line-height: 1.7;
}

.search-bar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.search-bar :deep(.ant-form-item) {
  margin: 0;
}

.search-bar :deep(.ant-input) {
  width: 210px;
}

.explore-shell {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 340px;
  gap: 16px;
  margin-top: 16px;
  align-items: stretch;
}

.theme-panel,
.map-panel,
.places-panel {
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #ffffff;
}

.theme-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
}

.theme-button {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 76px;
  padding: 16px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.theme-button:hover,
.theme-button.active {
  border-color: #0f766e;
  background: #eefaf7;
}

.theme-icon {
  flex: 0 0 32px;
  color: #0f766e;
  font-size: 24px;
}

.theme-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 6px;
}

.theme-copy strong {
  display: block;
  min-width: 0;
  color: #111827;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.25;
  white-space: nowrap;
}

.theme-copy small {
  display: block;
  min-width: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal;
}

.map-panel {
  position: relative;
  overflow: hidden;
}

.map-toolbar {
  position: absolute;
  top: 14px;
  left: 14px;
  right: 14px;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(219, 227, 234, 0.9);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
}

.map-toolbar > div {
  min-width: 0;
}

.map-toolbar strong,
.map-toolbar span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-toolbar strong {
  color: #111827;
}

.map-toolbar span {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

.map-toolbar :deep(.ant-btn) {
  flex: 0 0 auto;
  width: auto;
  min-width: 92px;
  height: 40px;
  white-space: nowrap;
}

.map-toolbar :deep(.ant-btn > span) {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.explore-map {
  width: 100%;
  height: 720px;
  background: #e2e8f0;
}

.map-empty {
  position: absolute;
  left: 18px;
  bottom: 18px;
  z-index: 2;
  display: grid;
  gap: 4px;
  max-width: 280px;
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px solid #dbe3ea;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.map-empty strong {
  color: #111827;
}

.map-empty span {
  color: #64748b;
  font-size: 13px;
}

.places-panel {
  display: flex;
  flex-direction: column;
  min-height: 720px;
  padding: 16px;
}

.places-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #edf2f7;
}

.places-head span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 850;
  text-transform: uppercase;
}

.places-head h2 {
  margin: 3px 0 0;
  color: #111827;
}

.places-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  margin-top: 14px;
  overflow: auto;
  padding-right: 4px;
}

.places-list button {
  display: grid;
  gap: 5px;
  width: 100%;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.places-list button:hover,
.places-list button.active {
  border-color: #0f766e;
  background: #eefaf7;
}

.places-list strong {
  color: #111827;
}

.places-list span,
.places-list small {
  color: #64748b;
  line-height: 1.45;
}

.place-detail {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid #edf2f7;
}

.place-detail h3 {
  margin: 0;
  color: #111827;
}

.place-detail p {
  color: #64748b;
  line-height: 1.6;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 14px 0;
}

.detail-grid div {
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.detail-grid span,
.detail-grid strong {
  display: block;
}

.detail-grid span {
  color: #94a3b8;
  font-size: 12px;
}

.detail-grid strong {
  margin-top: 4px;
  color: #111827;
}

@media (max-width: 1180px) {
  .explore-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .search-bar {
    justify-content: flex-start;
  }

  .explore-shell {
    grid-template-columns: 1fr;
  }

  .theme-panel {
    display: grid;
    grid-template-columns: repeat(2, minmax(260px, 1fr));
  }

  .places-panel {
    min-height: auto;
  }
}

@media (max-width: 720px) {
  .explore-page {
    padding-top: 16px;
  }

  .search-bar,
  .search-bar :deep(.ant-form-item),
  .search-bar :deep(.ant-input) {
    width: 100%;
  }

  .theme-panel {
    grid-template-columns: 1fr;
  }

  .explore-map {
    height: 520px;
  }
}
</style>
