import type { MapEdge, MapNode } from '@/api/mapAPI'

/** A place's centre on the map canvas. */
export interface Point {
  x: number
  y: number
}

/** Node positions plus the canvas size the map view draws them on. */
export interface MapLayout {
  positions: Map<string, Point>
  width: number
  height: number
}

const CELL_W = 250
const CELL_H = 200
const PAD_X = 130
const PAD_Y = 130

/** Smallest distance between two place centres (circle r=34 plus its label). */
export const MIN_SEPARATION = 140
/** A place inside another sits this close to it (closer than any other pair). */
export const INSIDE_DISTANCE = 115
/** A north/south or east/west pair is at least this far apart on its axis. */
export const DIRECTION_GAP = 170
/** Places that are near each other are pulled to at most this distance. */
export const NEAR_DISTANCE = 220

const CONSTRAINT_PASSES = 120
const SEPARATION_PASSES = 40

/**
 * Sequential "journey" layout: places are laid out in visit order along a
 * serpentine path (left-to-right, then wrapping back), so the eye follows
 * Start → … → End instead of an orderless ring.
 * @param nodes - Places in visit order.
 */
export function journeyLayout(nodes: MapNode[]): MapLayout {
  const positions = new Map<string, Point>()
  const count = nodes.length
  if (count === 0) return { positions, width: 800, height: 460 }

  const cols = Math.min(count, count <= 3 ? count : 4)
  const rows = Math.ceil(count / cols)

  nodes.forEach((node, index) => {
    const row = Math.floor(index / cols)
    const colInRow = index % cols
    const serpCol = row % 2 === 0 ? colInRow : cols - 1 - colInRow
    positions.set(node.id, { x: PAD_X + serpCol * CELL_W, y: PAD_Y + row * CELL_H })
  })

  return {
    positions,
    width: Math.max(PAD_X * 2 + (cols - 1) * CELL_W, 520),
    height: Math.max(PAD_Y * 2 + (rows - 1) * CELL_H + 40, 280),
  }
}

function isSpatial(edge: MapEdge): boolean {
  return (
    edge.type === 'north_of' ||
    edge.type === 'east_of' ||
    edge.type === 'inside' ||
    edge.type === 'near'
  )
}

function pairKey(a: string, b: string): string {
  return a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`
}

/** Move `a` by `aShare` of (dx, dy) and `b` by the rest in the opposite direction. */
function shift(a: Point, b: Point, dx: number, dy: number, aShare = 0.5) {
  a.x += dx * aShare
  a.y += dy * aShare
  b.x -= dx * (1 - aShare)
  b.y -= dy * (1 - aShare)
}

/**
 * Pull or push two points so they are `target` apart, along the line between
 * them. Coincident points are split along a fixed angle chosen from `salt`
 * so the result stays deterministic.
 */
function setDistance(a: Point, b: Point, target: number, salt: number, aShare = 0.5) {
  let dx = a.x - b.x
  let dy = a.y - b.y
  let distance = Math.hypot(dx, dy)
  if (distance < 1e-6) {
    const angle = (salt * 2.399963) % (2 * Math.PI)
    dx = Math.cos(angle)
    dy = Math.sin(angle)
    distance = 1
  }
  const change = (target - distance) / distance
  shift(a, b, dx * change, dy * change, aShare)
}

/**
 * Lay places out using their spatial relationships.
 *
 * Starts from the journey layout and repeatedly nudges places until:
 * a `north_of` place sits above the other one and an `east_of` place to its
 * right (at least {@link DIRECTION_GAP} apart on that axis), an `inside`
 * place sits next to its container, and `near` places are within
 * {@link NEAR_DISTANCE}. A final separation pass keeps every pair at least
 * {@link MIN_SEPARATION} apart (an inside pair: {@link INSIDE_DISTANCE}).
 * Runs a fixed number of passes, so contradictory relationships still
 * finish, and uses no randomness, so the same graph always lays out the same.
 *
 * Maps with no spatial relationships keep the plain journey layout.
 * @param nodes - Places in visit order.
 * @param edges - All links between them. Only near/inside/north_of/east_of move places.
 */
export function relationshipLayout(nodes: MapNode[], edges: MapEdge[]): MapLayout {
  const known = new Set(nodes.map((node) => node.id))
  const spatial = edges.filter(
    (edge) =>
      isSpatial(edge) && edge.from !== edge.to && known.has(edge.from) && known.has(edge.to),
  )
  const base = journeyLayout(nodes)
  if (spatial.length === 0) return base

  const points = nodes.map((node) => ({ ...base.positions.get(node.id)! }))
  const indexOf = new Map(nodes.map((node, index) => [node.id, index]))
  const insidePairs = new Set(
    spatial.filter((edge) => edge.type === 'inside').map((edge) => pairKey(edge.from, edge.to)),
  )

  const applyConstraints = () => {
    spatial.forEach((edge) => {
      const i = indexOf.get(edge.from)!
      const j = indexOf.get(edge.to)!
      const a = points[i]
      const b = points[j]
      if (edge.type === 'north_of') {
        const deficit = a.y - (b.y - DIRECTION_GAP)
        if (deficit > 0) shift(a, b, 0, -deficit)
      } else if (edge.type === 'east_of') {
        const deficit = b.x + DIRECTION_GAP - a.x
        if (deficit > 0) shift(a, b, deficit, 0)
      } else if (edge.type === 'inside') {
        // The contained place moves to its container, not the other way round.
        setDistance(a, b, INSIDE_DISTANCE, i, 0.8)
      } else if (Math.hypot(a.x - b.x, a.y - b.y) > NEAR_DISTANCE) {
        setDistance(a, b, NEAR_DISTANCE, i)
      }
    })
  }

  const separate = () => {
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        const minimum = insidePairs.has(pairKey(nodes[i].id, nodes[j].id))
          ? INSIDE_DISTANCE
          : MIN_SEPARATION
        const a = points[i]
        const b = points[j]
        if (Math.hypot(a.x - b.x, a.y - b.y) < minimum) setDistance(a, b, minimum, i + j)
      }
    }
  }

  for (let pass = 0; pass < CONSTRAINT_PASSES; pass += 1) {
    applyConstraints()
    separate()
  }
  for (let pass = 0; pass < SEPARATION_PASSES; pass += 1) separate()

  const minX = Math.min(...points.map((point) => point.x))
  const minY = Math.min(...points.map((point) => point.y))
  const positions = new Map<string, Point>()
  nodes.forEach((node, index) => {
    positions.set(node.id, {
      x: Math.round(points[index].x - minX + PAD_X),
      y: Math.round(points[index].y - minY + PAD_Y),
    })
  })
  const maxX = Math.max(...[...positions.values()].map((point) => point.x))
  const maxY = Math.max(...[...positions.values()].map((point) => point.y))
  return {
    positions,
    width: Math.max(maxX + PAD_X, 520),
    height: Math.max(maxY + PAD_Y + 40, 280),
  }
}
