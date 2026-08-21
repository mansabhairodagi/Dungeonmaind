<script setup lang="ts">
/**
 * MapView – displays a schematic campaign map built from session places.
 * Loads backend map data when available, otherwise derives nodes from timeline events.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMapStore } from '@/stores/map'
import { useTimelineStore } from '@/stores/timeline'
import type { MapEdgeType } from '@/api/mapAPI'

const router = useRouter()
const route = useRoute()
const mapStore = useMapStore()
const timelineStore = useTimelineStore()

const svgRef = ref<SVGSVGElement | null>(null)
const viewBox = { width: 720, height: 420 }

const edgeLabels: Record<MapEdgeType, string> = {
  traveled: 'Traveled',
  near: 'Near',
  north_of: 'North of',
  inside: 'Inside',
  other: 'Linked',
}

const edgeColors: Record<MapEdgeType, string> = {
  traveled: '#f39c12',
  near: '#3498db',
  north_of: '#2ecc71',
  inside: '#9b59b6',
  other: '#95a5a6',
}

const nodePositions = computed(() => {
  const count = mapStore.nodes.length
  if (count === 0) return new Map<string, { x: number; y: number }>()

  const centerX = viewBox.width / 2
  const centerY = viewBox.height / 2
  const radius = Math.min(viewBox.width, viewBox.height) * 0.34
  const positions = new Map<string, { x: number; y: number }>()

  mapStore.nodes.forEach((node, index) => {
    const angle = (index / count) * Math.PI * 2 - Math.PI / 2
    positions.set(node.id, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    })
  })

  return positions
})

const highlightedPlaceId = computed(() => {
  const fromQuery = mapStore.resolvePlaceQuery(
    typeof route.query.place === 'string' ? route.query.place : null,
  )
  return mapStore.selectedPlaceId ?? fromQuery
})

const selectedEvents = computed(() => {
  const ids = new Set(mapStore.selectedEventIds)
  return timelineStore.events
    .filter((event) => ids.has(event.id))
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
})

function goBack() {
  router.push({ name: 'home' })
}

function goToTimeline() {
  router.push({ name: 'timeline' })
}

async function handleSelectPlace(placeId: string) {
  await mapStore.selectPlace(placeId)
  const node = mapStore.nodes.find((item) => item.id === placeId)
  if (node) {
    router.replace({ name: 'map', query: { place: node.label } })
  }
}

function openTimelineEvent(eventId: string) {
  router.push({ name: 'timeline', query: { event: eventId } })
}

function edgePath(fromId: string, toId: string): string {
  const from = nodePositions.value.get(fromId)
  const to = nodePositions.value.get(toId)
  if (!from || !to) return ''
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`
}

async function loadMap() {
  await mapStore.fetchMap()
  const placeId = mapStore.resolvePlaceQuery(
    typeof route.query.place === 'string' ? route.query.place : null,
  )
  if (placeId && mapStore.nodes.some((node) => node.id === placeId)) {
    await mapStore.selectPlace(placeId)
  }
}

onMounted(loadMap)

watch(
  () => route.query.place,
  async (place) => {
    if (typeof place !== 'string' || !place.trim()) {
      mapStore.clearSelection()
      return
    }
    const placeId = mapStore.resolvePlaceQuery(place)
    if (placeId && mapStore.nodes.some((node) => node.id === placeId)) {
      await mapStore.selectPlace(placeId)
    }
  },
)
</script>

<template>
  <div class="map-page">
    <div class="map-shell">
      <header class="map-header">
        <div class="title-group">
          <button class="back-btn" @click="goBack">← Back to Dashboard</button>
          <div>
            <p class="eyebrow">Campaign Journey</p>
            <h1>Geographic Map</h1>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="goToTimeline">Open Timeline</button>
          <button class="btn btn-primary" :disabled="mapStore.loading" @click="loadMap">
            {{ mapStore.loading ? 'Loading...' : 'Refresh Map' }}
          </button>
        </div>
      </header>

      <p v-if="mapStore.dataSource === 'timeline'" class="info-banner">
        Showing places from timeline events until the map API is available.
      </p>

      <div v-if="mapStore.error" class="error-banner">
        {{ mapStore.error }}
      </div>

      <div v-if="mapStore.loading" class="loading">Loading map...</div>

      <div v-else-if="mapStore.nodeCount === 0" class="empty-state">
        <p>No places on the map yet.</p>
        <p>Record and transcribe a session, generate timeline events, then refresh this map.</p>
        <button class="btn btn-primary" @click="goToTimeline">Go to Timeline</button>
      </div>

      <div v-else class="map-layout">
        <section class="map-canvas-panel">
          <div class="map-meta">
            <span>{{ mapStore.nodeCount }} places</span>
            <span>{{ mapStore.edgeCount }} links</span>
          </div>

          <svg
            ref="svgRef"
            class="map-canvas"
            :viewBox="`0 0 ${viewBox.width} ${viewBox.height}`"
            role="img"
            aria-label="Campaign place map"
          >
            <defs>
              <marker
                id="arrow-traveled"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="4"
                orient="auto"
              >
                <path d="M0,0 L8,4 L0,8 Z" fill="#f39c12" />
              </marker>
            </defs>

            <g class="edges">
              <g v-for="(edge, index) in mapStore.edges" :key="`${edge.from}-${edge.to}-${index}`">
                <path
                  :d="edgePath(edge.from, edge.to)"
                  class="edge-line"
                  :stroke="edgeColors[edge.type] || edgeColors.other"
                  :marker-end="edge.type === 'traveled' ? 'url(#arrow-traveled)' : undefined"
                />
              </g>
            </g>

            <g class="nodes">
              <g
                v-for="node in mapStore.nodes"
                :key="node.id"
                class="node-group"
                :class="{ highlighted: highlightedPlaceId === node.id }"
                @click="handleSelectPlace(node.id)"
              >
                <circle
                  :cx="nodePositions.get(node.id)?.x"
                  :cy="nodePositions.get(node.id)?.y"
                  r="28"
                  class="node-circle"
                />
                <text
                  :x="nodePositions.get(node.id)?.x"
                  :y="(nodePositions.get(node.id)?.y ?? 0) + 44"
                  class="node-label"
                >
                  {{ node.label }}
                </text>
              </g>
            </g>
          </svg>

          <div class="legend">
            <span
              v-for="(label, type) in edgeLabels"
              :key="type"
              class="legend-item"
            >
              <i :style="{ background: edgeColors[type as MapEdgeType] }"></i>
              {{ label }}
            </span>
          </div>
        </section>

        <aside class="map-sidebar">
          <h2>Place details</h2>

          <div v-if="!mapStore.selectedNode" class="sidebar-empty">
            Click a place on the map to see related timeline events.
          </div>

          <template v-else>
            <div class="selected-place-card">
              <p class="sidebar-eyebrow">Selected place</p>
              <h3>{{ mapStore.selectedNode.label }}</h3>
            </div>

            <div v-if="selectedEvents.length === 0" class="sidebar-empty">
              No timeline events linked to this place yet.
            </div>

            <ul v-else class="event-list">
              <li v-for="event in selectedEvents" :key="event.id">
                <button class="event-link" @click="openTimelineEvent(event.id)">
                  <span class="event-type">{{ event.event_type }}</span>
                  <strong>{{ event.title }}</strong>
                  <span class="event-time">{{ event.display_time || '—' }}</span>
                </button>
              </li>
            </ul>
          </template>
        </aside>
      </div>
    </div>
  </div>
</template>

<style src="@/assets/styles.css"></style>
<style scoped>
.map-page {
  height: 100vh;
  padding: 60px 1.25rem 1.25rem;
  background-image: url('/bg-texture.jpg');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  background-color: rgba(36, 25, 7, 0.95);
  color: #392401;
  box-sizing: border-box;
  overflow: hidden;
}

.map-shell {
  max-width: 1100px;
  height: 100%;
  margin: 0 auto;
  padding: 1.4rem;
  border-radius: 14px;
  background-color: rgba(163, 148, 95, 0.85);
  border: 1px solid rgba(105, 87, 16, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.map-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.eyebrow,
.sidebar-eyebrow {
  margin: 0;
  color: #695710;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.map-header h1,
.map-sidebar h2,
.selected-place-card h3 {
  margin: 0;
  font-family: 'MedievalSharp', cursive;
  color: #392401;
}

.map-header h1 {
  font-size: 1.6rem;
}

.header-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.back-btn,
.btn {
  padding: 0.5rem 0.85rem;
  border: 1px solid #8e7513;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 700;
  font-family: 'MedievalSharp', cursive;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.back-btn {
  align-self: flex-start;
  background-color: #b74d30;
  color: white;
}

.back-btn:hover {
  background-color: #7e6f34;
}

.btn-primary {
  background-color: #695710;
  color: #fff;
}

.btn-secondary {
  background-color: rgba(53, 73, 94, 0.9);
  color: #fff;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.info-banner,
.error-banner {
  margin-bottom: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  font-size: 0.9rem;
}

.info-banner {
  background: rgba(52, 152, 219, 0.15);
  border: 1px solid rgba(52, 152, 219, 0.35);
}

.error-banner {
  background: rgba(231, 76, 60, 0.15);
  border: 1px solid rgba(231, 76, 60, 0.35);
}

.loading,
.empty-state,
.sidebar-empty {
  color: #4c3e06;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  text-align: center;
}

.map-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.8fr);
  gap: 1rem;
}

.map-canvas-panel,
.map-sidebar {
  min-height: 0;
  border-radius: 12px;
  background: rgba(255, 248, 220, 0.55);
  border: 1px solid rgba(105, 87, 16, 0.25);
}

.map-canvas-panel {
  display: flex;
  flex-direction: column;
  padding: 0.85rem;
}

.map-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: #695710;
}

.map-canvas {
  width: 100%;
  flex: 1;
  min-height: 280px;
  background: rgba(255, 255, 255, 0.35);
  border-radius: 10px;
}

.edge-line {
  fill: none;
  stroke-width: 3;
  opacity: 0.85;
}

.node-group {
  cursor: pointer;
}

.node-circle {
  fill: #d4b86a;
  stroke: #8e7513;
  stroke-width: 3;
  transition: all 0.2s ease;
}

.node-group:hover .node-circle,
.node-group.highlighted .node-circle {
  fill: #f39c12;
  stroke: #b45309;
  stroke-width: 4;
}

.node-label {
  text-anchor: middle;
  font-size: 12px;
  font-weight: 700;
  fill: #392401;
  font-family: 'MedievalSharp', cursive;
  pointer-events: none;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.75rem;
  font-size: 0.8rem;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.legend-item i {
  width: 14px;
  height: 3px;
  border-radius: 999px;
  display: inline-block;
}

.map-sidebar {
  padding: 1rem;
  overflow: auto;
}

.map-sidebar h2 {
  font-size: 1.15rem;
  margin-bottom: 0.75rem;
}

.selected-place-card {
  padding: 0.75rem;
  margin-bottom: 0.85rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(142, 117, 19, 0.25);
}

.event-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.event-link {
  width: 100%;
  text-align: left;
  padding: 0.75rem;
  border: 1px solid rgba(142, 117, 19, 0.25);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  color: #392401;
  font-family: inherit;
}

.event-link:hover {
  background: rgba(243, 156, 18, 0.18);
}

.event-type {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #695710;
  font-weight: 700;
}

.event-time {
  font-size: 0.8rem;
  color: #b45309;
}

@media (max-width: 900px) {
  .map-layout {
    grid-template-columns: 1fr;
  }
}
</style>
