import { SERVER_CONFIG } from '@/config/config'

/** Edge types between places on the campaign map. */
export type MapEdgeType = 'traveled' | 'near' | 'north_of' | 'inside' | 'other'

/** A place node on the session map. */
export interface MapNode {
  id: string
  label: string
  aliases?: string[]
}

/** A connection between two places. */
export interface MapEdge {
  from: string
  to: string
  type: MapEdgeType
}

/** Response shape for GET /map/{session_id}. */
export interface MapGraphResponse {
  session_id: string
  nodes: MapNode[]
  edges: MapEdge[]
}

/** Response shape for GET /map/{session_id}/places/{id}/events. */
export interface MapPlaceEventsResponse {
  place_id: string
  event_ids: string[]
}

function base(): string {
  return SERVER_CONFIG.BASE_URL
}

async function throwMapError(res: Response): Promise<never> {
  let message = `HTTP ${res.status}`
  try {
    const body = await res.json()
    if (typeof body.detail === 'string' && body.detail.trim()) {
      message = body.detail
    }
  } catch {
    // Keep the HTTP status when the backend does not return JSON.
  }
  throw new Error(message)
}

/**
 * Fetch the session map graph from the backend.
 * @param sessionId - The session identifier (defaults to 'default').
 */
export async function getMap(sessionId = 'default'): Promise<MapGraphResponse> {
  const url = new URL(`/map/${encodeURIComponent(sessionId)}`, base())
  const res = await fetch(url.toString())
  if (!res.ok) await throwMapError(res)
  return (await res.json()) as MapGraphResponse
}

/**
 * Fetch timeline event ids linked to a place on the map.
 * @param sessionId - The session identifier.
 * @param placeId - The place node id.
 */
export async function getPlaceEvents(
  sessionId: string,
  placeId: string,
): Promise<MapPlaceEventsResponse> {
  const url = new URL(
    `/map/${encodeURIComponent(sessionId)}/places/${encodeURIComponent(placeId)}/events`,
    base(),
  )
  const res = await fetch(url.toString())
  if (!res.ok) await throwMapError(res)
  return (await res.json()) as MapPlaceEventsResponse
}
