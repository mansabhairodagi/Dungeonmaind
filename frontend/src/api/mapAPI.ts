import { SERVER_CONFIG } from '@/config/config'
import { useSessionStore } from '@/stores/session'
import { UNSAVED_SESSION_ID } from '@/utils/sessionId'

/** Edge types between places on the campaign map. */
/**
 * Directed types read "from is <type> to": `inside` A→B means A is inside B,
 * `north_of` A→B means A is north of B. South and west arrive reversed.
 */
export type MapEdgeType = 'traveled' | 'near' | 'north_of' | 'east_of' | 'inside' | 'other'

/** A place node on the session map. */
export interface MapNode {
  id: string
  label: string
  aliases?: string[]
  event_ids?: string[]
}

/** Backend vocabulary for a stored map link. */
export type MapRelationship = 'travel' | 'proximity'

/** A connection between two places. */
export interface MapEdge {
  from: string
  to: string
  type: MapEdgeType
  /** The backend relationship name (`proximity`, `near`, `north_of`, ...). */
  relationship?: string
}

/** The map graph the views consume, assembled from the backend endpoints. */
export interface MapGraphResponse {
  session_id: string
  nodes: MapNode[]
  edges: MapEdge[]
}

/** Timeline events linked to a single place. */
export interface MapPlaceEventsResponse {
  place_id: string
  event_ids: string[]
}

/** A moment in the session recording where a place was mentioned. */
export interface MapMention {
  /** Seconds into the session recording. */
  start: number
  end: number
  text: string
  speaker: string
  /** `transcript` for a transcript line, `event` for a timeline-event fallback. */
  source: 'transcript' | 'event'
}

/** A resolved place as returned by GET /map/locations. */
export interface MapLocationOut {
  id: string
  canonical_name: string
  aliases?: string[]
  event_ids?: string[]
}

/** An inferred link as returned by GET /map/edges. */
export interface MapEdgeOut {
  from_location_id: string
  to_location_id: string
  relationship: string
}

/**
 * Translate the backend's relationship vocabulary into the edge types the
 * map legend renders. Timeline `proximity` and spoken `near` draw the same.
 */
export function toEdgeType(relationship: string): MapEdgeType {
  switch (relationship) {
    case 'travel':
      return 'traveled'
    case 'proximity':
    case 'near':
      return 'near'
    case 'inside':
    case 'north_of':
    case 'east_of':
      return relationship
    default:
      return 'other'
  }
}

function base(): string {
  return SERVER_CONFIG.BASE_URL
}

/** Identify the current player so the backend can apply the leader role check. */
function leaderPlayerId(): string | undefined {
  const id = useSessionStore().currentPlayer?.id
  return typeof id === 'string' && id.trim() ? id.trim() : undefined
}

/** POST a leader-only map write, sending the player id as header and query. */
async function leaderPost(path: string, body: Record<string, unknown>): Promise<void> {
  const playerId = leaderPlayerId()
  if (!playerId) {
    throw new Error('Join as the leader on this device before editing the map.')
  }
  const url = new URL(path, base())
  url.searchParams.set('actor_id', playerId)
  const res = await fetch(url.toString(), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Player-Id': playerId,
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) await throwMapError(res)
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

/** GET `path` with a `session_id` query parameter and decode the JSON body. */
async function getJson<T>(path: string, sessionId: string): Promise<T> {
  const url = new URL(path, base())
  url.searchParams.set('session_id', sessionId)
  const res = await fetch(url.toString())
  if (!res.ok) await throwMapError(res)
  return (await res.json()) as T
}

/** Turn backend location/edge lists into the graph the map view renders. */
export function graphFromLocationsAndEdges(
  sessionId: string,
  locations: MapLocationOut[] = [],
  edges: MapEdgeOut[] = [],
): MapGraphResponse {
  return {
    session_id: sessionId,
    nodes: locations.map((location) => ({
      id: location.id,
      label: location.canonical_name,
      ...(location.aliases?.length ? { aliases: location.aliases } : {}),
      ...(location.event_ids?.length ? { event_ids: location.event_ids } : {}),
    })),
    edges: edges.map((edge) => ({
      from: edge.from_location_id,
      to: edge.to_location_id,
      type: toEdgeType(edge.relationship),
      relationship: edge.relationship,
    })),
  }
}

export async function getMap(sessionId = UNSAVED_SESSION_ID): Promise<MapGraphResponse> {
  const [locations, edges] = await Promise.all([
    getJson<{ locations: MapLocationOut[] }>('/map/locations', sessionId),
    getJson<{ edges: MapEdgeOut[] }>('/map/edges', sessionId),
  ])

  return graphFromLocationsAndEdges(sessionId, locations.locations ?? [], edges.edges ?? [])
}

/**
 * Resolve places and links from the session timeline and save them on the backend.
 * @param sessionId - The session identifier (defaults to 'unsaved').
 */
export async function generateMap(sessionId = UNSAVED_SESSION_ID): Promise<void> {
  await leaderPost('/map/generate', { session_id: sessionId })
}

/**
 * Fetch timeline event ids linked to a place on the map.
 * @param sessionId - The session identifier.
 * @param placeId - The place node id.
 */
function relationshipFromEdgeType(type: MapEdgeType): MapRelationship {
  return type === 'near' ? 'proximity' : 'travel'
}

async function postOverride(path: string, body: Record<string, unknown>): Promise<void> {
  await leaderPost(path, body)
}

/** Persist a place rename in map_overrides.json. */
export async function renamePlace(
  sessionId: string,
  locationId: string,
  canonicalName: string,
): Promise<void> {
  await postOverride('/map/overrides/rename', {
    session_id: sessionId,
    location_id: locationId,
    canonical_name: canonicalName,
  })
}

/** Fold source places into a surviving target. */
export async function mergePlaces(
  sessionId: string,
  sourceLocationIds: string[],
  targetLocationId: string,
): Promise<void> {
  await postOverride('/map/overrides/merge', {
    session_id: sessionId,
    source_location_ids: sourceLocationIds,
    target_location_id: targetLocationId,
  })
}

/** Carve a new place out of an existing one. */
export async function splitPlace(
  sessionId: string,
  sourceLocationId: string,
  canonicalName: string,
  eventIds: string[],
): Promise<void> {
  await postOverride('/map/overrides/split', {
    session_id: sessionId,
    source_location_id: sourceLocationId,
    canonical_name: canonicalName,
    event_ids: eventIds,
  })
}

/** Add a link between two places. */
export async function connectPlaces(
  sessionId: string,
  fromLocationId: string,
  toLocationId: string,
  type: MapEdgeType = 'traveled',
): Promise<void> {
  await postOverride('/map/overrides/connect', {
    session_id: sessionId,
    from_location_id: fromLocationId,
    to_location_id: toLocationId,
    relationship: relationshipFromEdgeType(type),
  })
}

/** Remove a link between two places. */
export async function disconnectPlaces(
  sessionId: string,
  fromLocationId: string,
  toLocationId: string,
  type?: MapEdgeType,
): Promise<void> {
  await postOverride('/map/overrides/disconnect', {
    session_id: sessionId,
    from_location_id: fromLocationId,
    to_location_id: toLocationId,
    ...(type ? { relationship: relationshipFromEdgeType(type) } : {}),
  })
}

export async function getPlaceEvents(
  sessionId: string,
  placeId: string,
): Promise<MapPlaceEventsResponse> {
  const body = await getJson<{ events: { id: string }[] }>(
    `/map/locations/${encodeURIComponent(placeId)}/events`,
    sessionId,
  )
  return {
    place_id: placeId,
    event_ids: (body.events ?? []).map((event) => event.id),
  }
}

/**
 * Fetch the moments in the session recording where a place was mentioned.
 * @param sessionId - The session identifier.
 * @param placeId - The place node id.
 * @returns Mentions ordered by start time.
 */
export async function getPlaceMentions(sessionId: string, placeId: string): Promise<MapMention[]> {
  const body = await getJson<{ mentions: MapMention[] }>(
    `/map/locations/${encodeURIComponent(placeId)}/mentions`,
    sessionId,
  )
  return body.mentions ?? []
}

/** A transcript line on the map page, with the places it names. */
export interface MapTranscriptLine {
  start: number
  end: number
  text: string
  speaker: string
  location_ids: string[]
}

/** Relationships the DM can tag by hand. South and west are stored reversed. */
export type TaggableRelationship =
  | 'near'
  | 'inside'
  | 'north_of'
  | 'south_of'
  | 'east_of'
  | 'west_of'

/** A DM tag: `from` is <relationship> `to`, said on the line starting at `segment_start`. */
export interface RelationshipTag {
  from_location_id: string
  to_location_id: string
  relationship: TaggableRelationship
  segment_start?: number | null
}

/**
 * Fetch the session transcript with the places each line names.
 * @param sessionId - The session identifier.
 */
export async function getTranscript(sessionId: string): Promise<MapTranscriptLine[]> {
  const body = await getJson<{ lines: MapTranscriptLine[] }>('/map/transcript', sessionId)
  return body.lines ?? []
}

async function sendTag(
  method: 'POST' | 'DELETE',
  sessionId: string,
  playerId: string,
  tag: RelationshipTag,
): Promise<void> {
  const res = await fetch(`${base()}/map/relationships`, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Player-Id': playerId },
    body: JSON.stringify({ session_id: sessionId, ...tag }),
  })
  if (!res.ok) await throwMapError(res)
}

/**
 * Tag a spatial relationship between two places (Leader only).
 * @param sessionId - The session identifier.
 * @param playerId - The leader's player id, sent as X-Player-Id.
 * @param tag - The places, relationship and transcript line.
 */
export function tagRelationship(sessionId: string, playerId: string, tag: RelationshipTag) {
  return sendTag('POST', sessionId, playerId, tag)
}

/**
 * Remove a spatial relationship between two places (Leader only).
 * @param sessionId - The session identifier.
 * @param playerId - The leader's player id, sent as X-Player-Id.
 * @param tag - The places and relationship to remove.
 */
export function untagRelationship(sessionId: string, playerId: string, tag: RelationshipTag) {
  return sendTag('DELETE', sessionId, playerId, tag)
}
