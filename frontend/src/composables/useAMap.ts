/**
 * 高德地图组合式函数。
 *
 * 原实现中 `initMap` / `renderMarkers` / `focusPlace` / InfoWindow HTML 在
 * Result.vue 与 Explore.vue 里几乎逐字重复，且组件卸载时从不销毁地图实例
 * （内存泄漏）。这里统一封装，并在 `onUnmounted` 自动清理。
 */

import { onUnmounted, ref, type Ref } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

import { AMAP_JS_KEY, DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM, FOCUS_MAP_ZOOM } from '@/config'
import logger from '@/utils/logger'

export interface MarkerSpec {
  lng: number
  lat: number
  title: string
  /** 标记上的小标签文案，默认使用序号 */
  label?: string
  onClick?: () => void
}

export interface UseAMapOptions {
  zoom?: number
  center?: [number, number]
  plugins?: string[]
}

export interface UseAMapReturn {
  map: Ref<any>
  mapApi: Ref<any>
  markers: Ref<any[]>
  init: () => Promise<boolean>
  clearMarkers: () => void
  renderMarkers: (specs: MarkerSpec[], fitView?: boolean) => void
  openInfoWindow: (lng: number, lat: number, html: string, zoom?: number) => void
  destroy: () => void
}

const MARKER_LABEL_STYLE =
  'background:#0f766e;color:#fff;padding:5px 8px;border-radius:8px;font-size:12px;font-weight:700;'

export function useAMap(containerId: string, options: UseAMapOptions = {}): UseAMapReturn {
  const map = ref<any>(null)
  const mapApi = ref<any>(null)
  const markers = ref<any[]>([])
  let centerTimer: number | null = null

  const init = async (): Promise<boolean> => {
    if (map.value) return true
    if (typeof document === 'undefined' || !document.getElementById(containerId)) return false
    if (!AMAP_JS_KEY) {
      logger.error('未配置高德地图 JS API Key（VITE_AMAP_WEB_JS_KEY）')
      return false
    }
    try {
      const AMap = await AMapLoader.load({
        key: AMAP_JS_KEY,
        version: '2.0',
        plugins: options.plugins ?? ['AMap.Marker', 'AMap.InfoWindow']
      })
      mapApi.value = AMap
      map.value = new AMap.Map(containerId, {
        zoom: options.zoom ?? DEFAULT_MAP_ZOOM,
        center: options.center ?? DEFAULT_MAP_CENTER,
        viewMode: '3D'
      })
      return true
    } catch (error) {
      logger.error('高德地图加载失败:', error)
      return false
    }
  }

  const clearMarkers = (): void => {
    if (map.value && markers.value.length > 0) {
      map.value.remove(markers.value)
    }
    markers.value = []
  }

  const renderMarkers = (specs: MarkerSpec[], fitView = true): void => {
    const AMap = mapApi.value
    const instance = map.value
    if (!AMap || !instance) return

    clearMarkers()
    markers.value = specs.map((spec, index) => {
      const marker = new AMap.Marker({
        position: [spec.lng, spec.lat],
        title: spec.title,
        label: {
          content: `<div style="${MARKER_LABEL_STYLE}">${spec.label ?? index + 1}</div>`,
          offset: new AMap.Pixel(0, -28)
        }
      })
      if (spec.onClick) marker.on('click', spec.onClick)
      return marker
    })

    if (markers.value.length > 0) {
      instance.add(markers.value)
      if (fitView) instance.setFitView(markers.value)
    }
  }

  const openInfoWindow = (lng: number, lat: number, html: string, zoom = FOCUS_MAP_ZOOM): void => {
    const AMap = mapApi.value
    const instance = map.value
    if (!AMap || !instance) return

    const position = new AMap.LngLat(lng, lat)
    instance.setZoomAndCenter(zoom, position)
    const infoWindow = new AMap.InfoWindow({
      content: html,
      offset: new AMap.Pixel(0, -30),
      autoMove: false
    })
    infoWindow.open(instance, position)

    if (centerTimer) window.clearTimeout(centerTimer)
    centerTimer = window.setTimeout(() => instance.setCenter(position), 80)
  }

  const destroy = (): void => {
    if (centerTimer) {
      window.clearTimeout(centerTimer)
      centerTimer = null
    }
    clearMarkers()
    map.value?.destroy?.()
    map.value = null
    mapApi.value = null
  }

  // 组件卸载时自动释放地图实例与定时器
  onUnmounted(destroy)

  return { map, mapApi, markers, init, clearMarkers, renderMarkers, openInfoWindow, destroy }
}

export default useAMap
