<script setup lang="ts">
/**
 * TimelineView – displays session timeline events in a vertical timeline layout.
 * Supports filtering by event type, viewing details in a modal,
 * generating new events, and deleting individual or all events.
 */
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTimelineStore } from '@/stores/timeline'
import { useSessionStore } from '@/stores/session'
import type { TimelineEventOut } from '@/api/timelineAPI'

const router = useRouter()
const timelineStore = useTimelineStore()
const sessionStore = useSessionStore()

const selectedEvent = ref<TimelineEventOut | null>(null)
const showDetail = ref(false)
const filterType = ref<string | null>(null)

const typeColors: Record<string, string> = {
  combat: '#e74c3c',
  discovery: '#2ecc71',
  dialogue: '#3498db',
  travel: '#f39c12',
  rest: '#9b59b6',
  quest: '#1abc9c',
  other: '#95a5a6',
}

const typeIcons: Record<string, string> = {
  combat: '\u2694',
  discovery: '\uD83D\uDD0D',
  dialogue: '\uD83D\uDCAC',
  travel: '\uD83D\uDEE4\uFE0F',
  rest: '\uD83C\uDFD4\uFE0F',
  quest: '\uD83C\uDFF0',
  other: '\uD83D\uDCCC',
}

const filteredEvents = computed(() => {
  if (!filterType.value) return timelineStore.events
  return timelineStore.events.filter((e) => e.event_type === filterType.value)
})

const uniqueTypes = computed(() => {
  const types = new Set(timelineStore.events.map((e) => e.event_type))
  return Array.from(types)
})

function openDetail(event: TimelineEventOut) {
  selectedEvent.value = event
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
  selectedEvent.value = null
}

async function handleGenerate() {
  await timelineStore.generateEvents()
}

async function handleClear() {
  await timelineStore.clearEvents()
}

function goBack() {
  router.push({ name: 'home' })
}

onMounted(() => {
  timelineStore.fetchEvents()
})
</script>

<template>
  <div class="timeline-page">
    <header class="timeline-header">
      <button class="back-btn" @click="goBack">&larr; Back</button>
      <h1>Interactive Timeline</h1>
      <div class="header-actions">
        <button
          class="btn btn-primary"
          :disabled="timelineStore.generating"
          @click="handleGenerate"
        >
          {{ timelineStore.generating ? 'Generating...' : 'Generate Events' }}
        </button>
        <button
          class="btn btn-danger"
          :disabled="timelineStore.events.length === 0"
          @click="handleClear"
        >
          Clear All
        </button>
      </div>
    </header>

    <div v-if="timelineStore.error" class="error-banner">
      {{ timelineStore.error }}
    </div>

    <div v-if="timelineStore.loading" class="loading">Loading events...</div>

    <div v-else-if="timelineStore.events.length === 0" class="empty-state">
      <p>No timeline events yet.</p>
      <p>Record and transcribe a session, then click "Generate Events" to populate the timeline.</p>
    </div>

    <template v-else>
      <div class="filter-bar">
        <span class="filter-label">Filter:</span>
        <button :class="['filter-btn', { active: filterType === null }]" @click="filterType = null">
          All ({{ timelineStore.eventCount }})
        </button>
        <button
          v-for="type in uniqueTypes"
          :key="type"
          :class="['filter-btn', { active: filterType === type }]"
          @click="filterType = type"
        >
          {{ typeIcons[type] || '' }} {{ type }}
        </button>
      </div>

      <div class="timeline-container">
        <div class="timeline-line"></div>
        <div
          v-for="event in filteredEvents"
          :key="event.id"
          class="timeline-event"
          :style="{ '--event-color': typeColors[event.event_type] || '#95a5a6' }"
          @click="openDetail(event)"
        >
          <div class="event-dot"></div>
          <div class="event-card">
            <div
              class="event-type-badge"
              :style="{ background: typeColors[event.event_type] || '#95a5a6' }"
            >
              {{ typeIcons[event.event_type] || '' }} {{ event.event_type }}
            </div>
            <h3 class="event-title">{{ event.title }}</h3>
            <p class="event-description">{{ event.description }}</p>
            <div class="event-meta">
              <span v-if="event.speaker_name" class="meta-item">
                {{ event.speaker_name }}
              </span>
              <span v-if="event.temporal_entities.length" class="meta-item">
                {{ event.temporal_entities.join(', ') }}
              </span>
              <span v-if="event.location_entities.length" class="meta-item">
                {{ event.location_entities.join(', ') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-if="showDetail && selectedEvent" class="modal-overlay" @click.self="closeDetail">
      <div class="modal-content">
        <button class="modal-close" @click="closeDetail">&times;</button>
        <div
          class="modal-type-badge"
          :style="{ background: typeColors[selectedEvent.event_type] || '#95a5a6' }"
        >
          {{ selectedEvent.event_type }}
        </div>
        <h2>{{ selectedEvent.title }}</h2>
        <p class="modal-description">{{ selectedEvent.description }}</p>
        <div class="modal-details">
          <div v-if="selectedEvent.speaker_name" class="detail-row">
            <strong>Speaker:</strong> {{ selectedEvent.speaker_name }}
          </div>
          <div v-if="selectedEvent.temporal_entities.length" class="detail-row">
            <strong>Time:</strong> {{ selectedEvent.temporal_entities.join(', ') }}
          </div>
          <div v-if="selectedEvent.location_entities.length" class="detail-row">
            <strong>Location:</strong> {{ selectedEvent.location_entities.join(', ') }}
          </div>
          <div class="detail-row"><strong>Order:</strong> #{{ selectedEvent.order }}</div>
        </div>
        <button
          class="btn btn-danger"
          @click="
            timelineStore.removeEvent(selectedEvent.id)
            closeDetail()
          "
        >
          Delete Event
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
  color: #e0d5c1;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.timeline-header h1 {
  flex: 1;
  margin: 0;
  font-size: 1.5rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.back-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #e0d5c1;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn {
  padding: 0.4rem 0.8rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-banner {
  background: rgba(231, 76, 60, 0.2);
  border: 1px solid #e74c3c;
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #95a5a6;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  background: rgba(163, 148, 95, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-label {
  font-weight: bold;
  color: #95a5a6;
  font-size: 0.85rem;
}

.filter-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #e0d5c1;
  padding: 0.3rem 0.6rem;
  border-radius: 12px;
  cursor: pointer;
  font-size: 0.8rem;
}

.filter-btn.active {
  background: rgba(163, 148, 95, 0.5);
  border-color: #a3945f;
}

.timeline-container {
  position: relative;
  padding-left: 2rem;
}

.timeline-line {
  position: absolute;
  left: 0.9rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(163, 148, 95, 0.4);
}

.timeline-event {
  position: relative;
  margin-bottom: 1.5rem;
  cursor: pointer;
}

.event-dot {
  position: absolute;
  left: -1.6rem;
  top: 0.8rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--event-color, #95a5a6);
  border: 2px solid rgba(0, 0, 0, 0.3);
  z-index: 1;
}

.event-card {
  background: rgba(163, 148, 95, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 0.8rem 1rem;
  transition: background 0.2s;
}

.event-card:hover {
  background: rgba(163, 148, 95, 0.25);
}

.event-type-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.75rem;
  color: white;
  margin-bottom: 0.4rem;
}

.event-title {
  margin: 0 0 0.3rem;
  font-size: 1rem;
}

.event-description {
  margin: 0 0 0.4rem;
  font-size: 0.85rem;
  color: #b0a590;
  line-height: 1.4;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.meta-item {
  font-size: 0.75rem;
  color: #95a5a6;
  background: rgba(0, 0, 0, 0.2);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #2a2520;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 500px;
  width: 90%;
  position: relative;
  color: #e0d5c1;
}

.modal-close {
  position: absolute;
  top: 0.5rem;
  right: 0.8rem;
  background: none;
  border: none;
  color: #e0d5c1;
  font-size: 1.5rem;
  cursor: pointer;
}

.modal-type-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.8rem;
  color: white;
  margin-bottom: 0.5rem;
}

.modal-content h2 {
  margin: 0 0 0.5rem;
}

.modal-description {
  color: #b0a590;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.modal-details {
  margin-bottom: 1rem;
}

.detail-row {
  margin-bottom: 0.3rem;
  font-size: 0.85rem;
}
</style>
