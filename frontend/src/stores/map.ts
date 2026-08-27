import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as mapApi from '@/api/mapAPI'
import type { MapEdge, MapNode } from '@/api/mapAPI'
import { useTimelineStore } from '@/stores/timeline'
import { buildMapFromTimeline, locationBelongsToNode, placeToId } from '@/utils/mapFromTimeline'

/** Whether the map graph came from the backend API or timeline fallback. */
export type MapDataSource = 'api' | 'timeline'

/**
 * Map store – loads session place graph and selected-place event links.
 * Falls back to timeline location_entities when the map API is unavailable.
 */
export const useMapStore = defineStore('map', () => {
  const nodes = ref<MapNode[]>([])
  const edges = ref<MapEdge[]>([])
  const sessionId = ref('default')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const dataSource = ref<MapDataSource>('timeline')
  const selectedPlaceId = ref<string | null>(null)
  const selectedEventIds = ref<string[]>([])

  const nodeCount = computed(() => nodes.value.length)
  const edgeCount = computed(() => edges.value.length)

  const selectedNode = computed(() =>
    nodes.value.find((node) => node.id === selectedPlaceId.value) ?? null,
  )

  /**
   * Load map data for a session. Uses backend API when available, otherwise timeline events.
   */
  async function fetchMap(forSessionId = 'default') {
    loading.value = true
    error.value = null
    sessionId.value = forSessionId

    try {
      const response = await mapApi.getMap(forSessionId)
      nodes.value = response.nodes ?? []
      edges.value = response.edges ?? []
      dataSource.value = 'api'
    } catch (apiError) {
      const timelineStore = useTimelineStore()
      if (timelineStore.events.length === 0 && !timelineStore.loading) {
        await timelineStore.fetchEvents(forSessionId)
      }

      const fallback = buildMapFromTimeline(timelineStore.events, forSessionId)
      nodes.value = fallback.nodes
      edges.value = fallback.edges
      dataSource.value = 'timeline'

      if (fallback.nodes.length === 0) {
        const message =
          apiError instanceof Error ? apiError.message : 'Map API unavailable'
        error.value =
          message.includes('404') || message.includes('HTTP 404')
            ? null
            : `Map API unavailable — showing timeline places when available. (${message})`
      }
    } finally {
      loading.value = false
    }
  }

  /** Select a place node and load linked timeline events. */
  async function selectPlace(placeId: string | null) {
    selectedPlaceId.value = placeId
    selectedEventIds.value = []

    if (!placeId) return

    const node = nodes.value.find((item) => item.id === placeId)
    if (!node) return

    if (dataSource.value === 'api') {
      try {
        const response = await mapApi.getPlaceEvents(sessionId.value, placeId)
        selectedEventIds.value = response.event_ids ?? []
        return
      } catch {
        // Fall through to timeline-based lookup.
      }
    }

    const timelineStore = useTimelineStore()
    selectedEventIds.value = timelineStore.events
      .filter((event) =>
        event.location_entities.some((location) => locationBelongsToNode(location, node)),
      )
      .map((event) => event.id)
  }

  /** Resolve a place query string to a node id, if it matches a label. */
  function resolvePlaceQuery(placeQuery: string | null | undefined): string | null {
    if (!placeQuery?.trim()) return null
    const query = placeQuery.trim()
    const byId = nodes.value.find((node) => node.id === query)
    if (byId) return byId.id
    const byLabel = nodes.value.find((node) => locationBelongsToNode(query, node))
    return byLabel?.id ?? placeToId(query)
  }

  function clearSelection() {
    selectedPlaceId.value = null
    selectedEventIds.value = []
  }

  return {
    nodes,
    edges,
    sessionId,
    loading,
    error,
    dataSource,
    selectedPlaceId,
    selectedEventIds,
    nodeCount,
    edgeCount,
    selectedNode,
    fetchMap,
    selectPlace,
    resolvePlaceQuery,
    clearSelection,
  }
})
