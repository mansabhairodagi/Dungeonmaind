import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api/timelineAPI'
import type { TimelineEventOut, EventType } from '@/api/timelineAPI'

export const useTimelineStore = defineStore('timeline', () => {
  const events = ref<TimelineEventOut[]>([])
  const loading = ref(false)
  const generating = ref(false)
  const error = ref<string | null>(null)

  const eventCount = computed(() => events.value.length)

  const eventsByType = computed(() => {
    const grouped: Record<EventType, TimelineEventOut[]> = {
      combat: [],
      discovery: [],
      dialogue: [],
      travel: [],
      rest: [],
      quest: [],
      other: [],
    }
    for (const event of events.value) {
      const type = event.event_type as EventType
      if (grouped[type]) {
        grouped[type].push(event)
      } else {
        grouped.other.push(event)
      }
    }
    return grouped
  })

  async function fetchEvents(sessionId = 'default') {
    loading.value = true
    error.value = null
    try {
      const response = await api.listEvents(sessionId)
      events.value = response.events
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load events'
      events.value = []
    } finally {
      loading.value = false
    }
  }

  async function generateEvents(sessionId = 'default') {
    generating.value = true
    error.value = null
    try {
      const response = await api.generateEvents(sessionId)
      events.value = response.events
      return response
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to generate events'
      return null
    } finally {
      generating.value = false
    }
  }

  async function removeEvent(eventId: string) {
    try {
      await api.deleteEvent(eventId)
      events.value = events.value.filter(e => e.id !== eventId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete event'
    }
  }

  async function clearEvents(sessionId = 'default') {
    try {
      await api.clearSessionEvents(sessionId)
      events.value = []
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to clear events'
    }
  }

  return {
    events,
    loading,
    generating,
    error,
    eventCount,
    eventsByType,
    fetchEvents,
    generateEvents,
    removeEvent,
    clearEvents,
  }
})
