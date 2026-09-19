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

const edgeLabels: Record<MapEdgeType, string> = {
  traveled: 'Traveled',
  near: 'Near',
  north_of: 'North of',
  inside: 'Inside',
  other: 'Linked',
}

const edgeColors: Record<MapEdgeType, string> = {
  traveled: '#b45309',
  near: '#2f6f8f',
  north_of: '#2e7d4f',
  inside: '#7b4d8e',
  other: '#8a7a4a',
}

/**
 * Sequential "journey" layout: places are laid out in visit order along a
 * serpentine path (left-to-right, then wrapping back), so the eye follows
 * Start → … → End instead of an orderless ring.
 */
const layout = computed(() => {
  const nodes = mapStore.nodes
  const positions = new Map<string, { x: number; y: number }>()
  const count = nodes.length
  if (count === 0) return { positions, width: 800, height: 460 }

  const cols = Math.min(count, count <= 3 ? count : 4)
  const rows = Math.ceil(count / cols)
  const cellW = 250
  const cellH = 200
  const padX = 130
  const padY = 130

  nodes.forEach((node, index) => {
    const row = Math.floor(index / cols)
    const colInRow = index % cols
    // Reverse direction on odd rows so the trail stays continuous.
    const serpCol = row % 2 === 0 ? colInRow : cols - 1 - colInRow
    positions.set(node.id, { x: padX + serpCol * cellW, y: padY + row * cellH })
  })

  return {
    positions,
    width: padX * 2 + (cols - 1) * cellW,
    height: padY * 2 + (rows - 1) * cellH,
  }
})

const nodePositions = computed(() => layout.value.positions)

/** Ids of the selected place plus everything directly linked to it. */
const connectedNodeIds = computed(() => {
  const selected = highlightedPlaceId.value
  if (!selected) return null
  const ids = new Set<string>([selected])
  mapStore.edges.forEach((edge) => {
    if (edge.from === selected) ids.add(edge.to)
    if (edge.to === selected) ids.add(edge.from)
  })
  return ids
})

function nodeLabel(id: string): string {
  return mapStore.nodes.find((node) => node.id === id)?.label ?? id
}

function nodeDimmed(id: string): boolean {
  const connected = connectedNodeIds.value
  return connected ? !connected.has(id) : false
}

function edgeTouchesSelection(from: string, to: string): boolean {
  const selected = highlightedPlaceId.value
  return selected ? from === selected || to === selected : false
}

function isStart(index: number): boolean {
  return index === 0
}

function isEnd(index: number): boolean {
  return index === mapStore.nodes.length - 1
}

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
  // Gentle curved "trail" — offset the control point perpendicular to the
  // straight line so overlapping routes stay readable, like a treasure map.
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const arc = Math.min(70, len * 0.2)
  const cx = (from.x + to.x) / 2 - (dy / len) * arc
  const cy = (from.y + to.y) / 2 + (dx / len) * arc
  return `M ${from.x} ${from.y} Q ${cx} ${cy} ${to.x} ${to.y}`
}

async function loadMap() {
  // The sidebar resolves linked event ids against the timeline store, so the
  // events have to be loaded whether the graph came from the map API or from
  // the timeline fallback. Only the fallback path used to fetch them, which
  // left "Place details" empty whenever the API answered.
  const timelineReady =
    timelineStore.events.length === 0 && !timelineStore.loading
      ? timelineStore.fetchEvents()
      : Promise.resolve()

  await Promise.all([mapStore.fetchMap(), timelineReady])
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
            :viewBox="`0 0 ${layout.width} ${layout.height}`"
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label="Campaign place map showing the party's journey"
          >
            <defs>
              <marker
                id="arrow-traveled"
                markerWidth="10"
                markerHeight="10"
                refX="9"
                refY="5"
                orient="auto"
                markerUnits="userSpaceOnUse"
              >
                <path d="M0,0 L10,5 L0,10 Z" fill="#b45309" />
              </marker>
              <filter id="node-shadow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow
                  dx="0"
                  dy="3"
                  stdDeviation="4"
                  flood-color="#2b1c04"
                  flood-opacity="0.35"
                />
              </filter>
            </defs>

            <g class="edges">
              <g
                v-for="(edge, index) in mapStore.edges"
                :key="`${edge.from}-${edge.to}-${index}`"
                class="edge-group"
                :class="{
                  dimmed: highlightedPlaceId && !edgeTouchesSelection(edge.from, edge.to),
                  active: edgeTouchesSelection(edge.from, edge.to),
                }"
              >
                <title>
                  {{ edgeLabels[edge.type] || 'Linked' }}: {{ nodeLabel(edge.from) }} →
                  {{ nodeLabel(edge.to) }}
                </title>
                <path
                  :d="edgePath(edge.from, edge.to)"
                  class="edge-line"
                  :class="{ proximity: edge.type !== 'traveled' }"
                  :stroke="edgeColors[edge.type] || edgeColors.other"
                  :marker-end="edge.type === 'traveled' ? 'url(#arrow-traveled)' : undefined"
                />
              </g>
            </g>

            <g class="nodes">
              <g
                v-for="(node, index) in mapStore.nodes"
                :key="node.id"
                class="node-group"
                :class="{
                  highlighted: highlightedPlaceId === node.id,
                  dimmed: nodeDimmed(node.id),
                }"
                role="button"
                tabindex="0"
                :aria-label="`Place ${index + 1}: ${node.label}`"
                @click="handleSelectPlace(node.id)"
                @keyup.enter="handleSelectPlace(node.id)"
              >
                <title>
                  {{ node.label }}<template v-if="node.aliases?.length"> (also:
                  {{ node.aliases.join(', ') }})</template>
                </title>

                <text
                  v-if="isStart(index) || isEnd(index)"
                  :x="nodePositions.get(node.id)?.x"
                  :y="(nodePositions.get(node.id)?.y ?? 0) - 48"
                  class="node-flag"
                >
                  {{ isStart(index) ? 'START' : 'END' }}
                </text>

                <circle
                  :cx="nodePositions.get(node.id)?.x"
                  :cy="nodePositions.get(node.id)?.y"
                  r="34"
                  class="node-circle"
                  filter="url(#node-shadow)"
                />
                <text
                  :x="nodePositions.get(node.id)?.x"
                  :y="(nodePositions.get(node.id)?.y ?? 0) + 6"
                  class="node-index"
                >
                  {{ index + 1 }}
                </text>
                <text
                  :x="nodePositions.get(node.id)?.x"
                  :y="(nodePositions.get(node.id)?.y ?? 0) + 60"
                  class="node-label"
                >
                  {{ node.label }}
                </text>
              </g>
            </g>
          </svg>

          <div class="legend">
            <span v-for="(label, type) in edgeLabels" :key="type" class="legend-item">
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
              <p v-if="mapStore.selectedNode.aliases?.length" class="sidebar-aliases">
                Also known as: {{ mapStore.selectedNode.aliases.join(', ') }}
              </p>
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

<style scoped>
.map-page {
  position: fixed;
  inset: 0;
  z-index: 500;
  height: 100vh;
  width: 100vw;
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
  max-width: 1280px;
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

.sidebar-aliases {
  margin: 0.4rem 0 0;
  color: #5c4a24;
  font-size: 0.9rem;
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

/* Quiet parchment tone rather than the stray slate blue, so "Refresh Map"
   stays the stronger of the two header actions. */
.btn-secondary {
  background-color: rgba(57, 36, 1, 0.14);
  border-color: rgba(57, 36, 1, 0.3);
  color: var(--dm-ink);
}

.btn-secondary:hover:not(:disabled) {
  background-color: rgba(57, 36, 1, 0.24);
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
  min-height: 440px;
  background: radial-gradient(
    circle at 30% 20%,
    rgba(255, 251, 235, 0.9),
    rgba(244, 232, 200, 0.82) 55%,
    rgba(226, 208, 160, 0.85) 100%
  );
  border: 1px solid rgba(105, 87, 16, 0.3);
  border-radius: 12px;
  box-shadow: inset 0 0 40px rgba(120, 92, 30, 0.25);
}

.edge-group {
  transition: opacity 0.2s ease;
}

.edge-group.dimmed {
  opacity: 0.2;
}

.edge-line {
  fill: none;
  stroke-width: 3.5;
  opacity: 0.9;
  stroke-linecap: round;
}

.edge-line.proximity {
  stroke-dasharray: 6 7;
  opacity: 0.75;
}

.edge-group.active .edge-line {
  stroke-width: 5;
  opacity: 1;
}

.node-group {
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.node-group:focus {
  outline: none;
}

.node-group.dimmed {
  opacity: 0.32;
}

.node-circle {
  fill: #e2c583;
  stroke: #8e7513;
  stroke-width: 3;
  transition: all 0.2s ease;
}

.node-group:hover .node-circle,
.node-group:focus .node-circle,
.node-group.highlighted .node-circle {
  fill: #f4b95a;
  stroke: #b45309;
  stroke-width: 4.5;
}

.node-index {
  text-anchor: middle;
  font-size: 22px;
  font-weight: 700;
  fill: #4a3403;
  font-family: 'MedievalSharp', cursive;
  pointer-events: none;
}

.node-flag {
  text-anchor: middle;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  fill: #b45309;
  pointer-events: none;
}

.node-label {
  text-anchor: middle;
  font-size: 15px;
  font-weight: 700;
  fill: #2f1e02;
  font-family: 'MedievalSharp', cursive;
  pointer-events: none;
  paint-order: stroke;
  stroke: rgba(255, 250, 235, 0.9);
  stroke-width: 3px;
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
