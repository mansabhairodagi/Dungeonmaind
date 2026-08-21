import type { MapEdge, MapGraphResponse, MapNode } from '@/api/mapAPI'
import type { TimelineEventOut } from '@/api/timelineAPI'

/** Convert a place label into a stable map node id. */
export function placeToId(label: string): string {
  const slug = label
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || 'unknown-place'
}

/** Compare place labels case-insensitively. */
export function placesMatch(a: string, b: string): boolean {
  return a.trim().toLowerCase() === b.trim().toLowerCase()
}

/**
 * Build a schematic map from Release 2 timeline events until the map API exists.
 * Uses unique location_entities as nodes and travel order for traveled edges.
 */
export function buildMapFromTimeline(
  events: TimelineEventOut[],
  sessionId = 'default',
): MapGraphResponse {
  const nodeById = new Map<string, MapNode>()
  const edges: MapEdge[] = []
  const edgeKeys = new Set<string>()

  for (const event of events) {
    for (const location of event.location_entities) {
      const label = location.trim()
      if (!label) continue
      const id = placeToId(label)
      if (!nodeById.has(id)) {
        nodeById.set(id, { id, label })
      }
    }
  }

  const sorted = [...events].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
  let lastPlaceId: string | null = null

  for (const event of sorted) {
    const locations = event.location_entities.map((l) => l.trim()).filter(Boolean)
    if (locations.length === 0) continue

    const primary = locations[0]
    const currentId = placeToId(primary)

    if (!nodeById.has(currentId)) {
      nodeById.set(currentId, { id: currentId, label: primary })
    }

    if (lastPlaceId && lastPlaceId !== currentId) {
      const key = `${lastPlaceId}->${currentId}`
      if (!edgeKeys.has(key)) {
        edgeKeys.add(key)
        edges.push({
          from: lastPlaceId,
          to: currentId,
          type: event.event_type === 'travel' ? 'traveled' : 'other',
        })
      }
    }

    lastPlaceId = currentId
  }

  return {
    session_id: sessionId,
    nodes: Array.from(nodeById.values()),
    edges,
  }
}
