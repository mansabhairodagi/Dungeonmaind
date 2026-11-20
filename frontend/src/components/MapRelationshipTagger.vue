<script setup lang="ts">
/**
 * MapRelationshipTagger – lets the Leader tag where a place lies relative to
 * another one ("the cellar is inside the keep") on the transcript line where
 * it was said, and remove spatial relationships that are wrong.
 *
 * Tags are saved in map_overrides.json by the backend, so they survive
 * regenerating the map. Only rendered for the Leader.
 */
import { computed, ref, watch } from 'vue'
import * as mapApi from '@/api/mapAPI'
import type { MapTranscriptLine, TaggableRelationship } from '@/api/mapAPI'
import { useMapStore } from '@/stores/map'
import { useSessionStore } from '@/stores/session'

const props = defineProps<{
  /** The selected place the tags start from. */
  placeId: string
}>()

const mapStore = useMapStore()
const sessionStore = useSessionStore()

const relationshipLabels: Record<TaggableRelationship, string> = {
  near: 'is near',
  inside: 'is inside',
  north_of: 'is north of',
  south_of: 'is south of',
  east_of: 'is east of',
  west_of: 'is west of',
}
const relationshipOrder = Object.keys(relationshipLabels) as TaggableRelationship[]

/** Backend relationships the DM can remove from here. */
const REMOVABLE = new Set(['near', 'inside', 'north_of', 'east_of'])

const transcript = ref<MapTranscriptLine[]>([])
const selectedLineStart = ref<number | null>(null)
const relationship = ref<TaggableRelationship>('near')
const otherPlaceId = ref('')
const busy = ref(false)
const message = ref('')

const placeLabel = computed(
  () => mapStore.nodes.find((node) => node.id === props.placeId)?.label ?? props.placeId,
)

const otherPlaces = computed(() => mapStore.nodes.filter((node) => node.id !== props.placeId))

/** Transcript lines that name the selected place. */
const lines = computed(() =>
  transcript.value.filter((line) => line.location_ids.includes(props.placeId)),
)

const selectedLine = computed(
  () => lines.value.find((line) => line.start === selectedLineStart.value) ?? null,
)

/** Spatial relationships touching the selected place that the DM can remove. */
const spatialLinks = computed(() =>
  mapStore.edges.filter(
    (edge) =>
      REMOVABLE.has(edge.relationship ?? '') &&
      (edge.from === props.placeId || edge.to === props.placeId),
  ),
)

function nodeLabel(id: string): string {
  return mapStore.nodes.find((node) => node.id === id)?.label ?? id
}

function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/** Pick a transcript line and suggest the other place it names. */
function chooseLine(line: MapTranscriptLine) {
  selectedLineStart.value = line.start
  const suggested = line.location_ids.find((id) => id !== props.placeId)
  if (suggested) otherPlaceId.value = suggested
}

async function loadTranscript() {
  try {
    transcript.value = await mapApi.getTranscript(mapStore.sessionId)
  } catch {
    transcript.value = []
  }
}

/**
 * Send a tag change as the Leader, then reload the map so the layout updates.
 * @param action - The API call, given the Leader's player id.
 * @param done - Message shown when it succeeds.
 */
async function run(action: (playerId: string) => Promise<void>, done: string) {
  const playerId = sessionStore.currentPlayer?.id
  if (!playerId) {
    message.value = 'Join as the Leader to edit relationships.'
    return
  }
  busy.value = true
  message.value = ''
  try {
    await action(playerId)
    await mapStore.fetchMap(mapStore.sessionId)
    message.value = done
  } catch (err) {
    message.value = err instanceof Error ? err.message : 'Could not save the relationship.'
  } finally {
    busy.value = false
  }
}

function saveTag() {
  if (!otherPlaceId.value) return
  const tag = {
    from_location_id: props.placeId,
    to_location_id: otherPlaceId.value,
    relationship: relationship.value,
    segment_start: selectedLine.value?.start ?? null,
  }
  void run(
    (playerId) => mapApi.tagRelationship(mapStore.sessionId, playerId, tag),
    'Relationship saved.',
  )
}

function removeLink(from: string, to: string, linkRelationship: string) {
  const tag = {
    from_location_id: from,
    to_location_id: to,
    relationship: linkRelationship as TaggableRelationship,
  }
  void run(
    (playerId) => mapApi.untagRelationship(mapStore.sessionId, playerId, tag),
    'Relationship removed.',
  )
}

watch(
  () => props.placeId,
  () => {
    selectedLineStart.value = null
    otherPlaceId.value = ''
    message.value = ''
  },
)

watch(() => mapStore.sessionId, loadTranscript, { immediate: true })
</script>

<template>
  <div class="tagger">
    <p class="tagger-title">Tag a relationship (Leader)</p>

    <ul v-if="spatialLinks.length" class="tagger-links">
      <li v-for="link in spatialLinks" :key="`${link.from}-${link.relationship}-${link.to}`">
        <span>
          {{ nodeLabel(link.from) }}
          {{ relationshipLabels[link.relationship as TaggableRelationship] }}
          {{ nodeLabel(link.to) }}
        </span>
        <button
          type="button"
          class="tagger-remove"
          :disabled="busy"
          :aria-label="`Remove: ${nodeLabel(link.from)} ${link.relationship} ${nodeLabel(link.to)}`"
          @click="removeLink(link.from, link.to, link.relationship ?? '')"
        >
          ✕
        </button>
      </li>
    </ul>

    <p v-if="lines.length" class="tagger-hint">Pick the line where it was said:</p>
    <ul v-if="lines.length" class="tagger-lines">
      <li v-for="line in lines" :key="line.start">
        <button
          type="button"
          class="tagger-line"
          :class="{ active: line.start === selectedLineStart }"
          @click="chooseLine(line)"
        >
          <span class="tagger-time">{{ formatClock(line.start) }}</span>
          {{ line.text }}
        </button>
      </li>
    </ul>

    <form class="tagger-form" @submit.prevent="saveTag">
      <span class="tagger-subject">{{ placeLabel }}</span>
      <select v-model="relationship" aria-label="Relationship">
        <option v-for="option in relationshipOrder" :key="option" :value="option">
          {{ relationshipLabels[option] }}
        </option>
      </select>
      <select v-model="otherPlaceId" aria-label="Other place">
        <option value="" disabled>choose a place</option>
        <option v-for="node in otherPlaces" :key="node.id" :value="node.id">
          {{ node.label }}
        </option>
      </select>
      <button type="submit" class="tagger-save" :disabled="busy || !otherPlaceId">Save</button>
    </form>
    <p v-if="message" class="tagger-message">{{ message }}</p>
  </div>
</template>

<style scoped>
.tagger {
  margin-bottom: 0.85rem;
  padding: 0.75rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px dashed rgba(142, 117, 19, 0.4);
}

.tagger-title {
  margin: 0;
  color: #695710;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.tagger-links,
.tagger-lines {
  list-style: none;
  margin: 0.4rem 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.tagger-links li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
}

.tagger-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #8b2e1c;
  font-size: 0.9rem;
}

.tagger-hint,
.tagger-message {
  margin: 0.4rem 0;
  font-size: 0.8rem;
  color: #4c3e06;
}

.tagger-lines {
  max-height: 10rem;
  overflow-y: auto;
}

.tagger-line {
  width: 100%;
  text-align: left;
  padding: 0.35rem 0.5rem;
  border-radius: 8px;
  border: 1px solid rgba(142, 117, 19, 0.25);
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  font-size: 0.8rem;
  color: #392401;
}

.tagger-line.active {
  border-color: #b45309;
  background: rgba(243, 156, 18, 0.22);
}

.tagger-time {
  font-weight: 700;
  margin-right: 0.3rem;
  font-variant-numeric: tabular-nums;
}

.tagger-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
}

.tagger-subject {
  font-weight: 700;
}

.tagger-form select {
  max-width: 100%;
  padding: 0.25rem;
  border-radius: 6px;
  border: 1px solid rgba(142, 117, 19, 0.35);
  background: rgba(255, 255, 255, 0.7);
  color: #392401;
}

.tagger-save {
  padding: 0.3rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #b45309;
  background: rgba(243, 156, 18, 0.25);
  color: #392401;
  cursor: pointer;
}

.tagger-save:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
