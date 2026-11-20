import { describe, expect, it } from 'vitest'
import type { MapEdge, MapEdgeType, MapNode } from '@/api/mapAPI'
import {
  DIRECTION_GAP,
  INSIDE_DISTANCE,
  MIN_SEPARATION,
  NEAR_DISTANCE,
  journeyLayout,
  relationshipLayout,
  type MapLayout,
} from '@/utils/mapLayout'

function nodes(...ids: string[]): MapNode[] {
  return ids.map((id) => ({ id, label: id }))
}

function edge(from: string, type: MapEdgeType, to: string): MapEdge {
  return { from, to, type }
}

function at(layout: MapLayout, id: string) {
  const point = layout.positions.get(id)
  if (!point) throw new Error(`no position for ${id}`)
  return point
}

function distance(layout: MapLayout, a: string, b: string): number {
  const p = at(layout, a)
  const q = at(layout, b)
  return Math.hypot(p.x - q.x, p.y - q.y)
}

// Positions are rounded to whole pixels, so allow a pixel of slack.
const SLACK = 1.5

describe('relationshipLayout', () => {
  it('keeps the journey layout when there are no spatial relationships', () => {
    const places = nodes('a', 'b', 'c', 'd', 'e')
    const travel = [edge('a', 'traveled', 'b'), edge('b', 'traveled', 'c')]

    expect(relationshipLayout(places, travel)).toEqual(journeyLayout(places))
  })

  it('puts a north_of place above the other one', () => {
    // In journey order 'a' would be on the same row as 'b'.
    const layout = relationshipLayout(nodes('b', 'a'), [edge('a', 'north_of', 'b')])

    expect(at(layout, 'b').y - at(layout, 'a').y).toBeGreaterThanOrEqual(DIRECTION_GAP - SLACK)
  })

  it('puts an east_of place to the right of the other one', () => {
    // Journey order would put 'a' on the left.
    const layout = relationshipLayout(nodes('a', 'b'), [edge('a', 'east_of', 'b')])

    expect(at(layout, 'a').x - at(layout, 'b').x).toBeGreaterThanOrEqual(DIRECTION_GAP - SLACK)
  })

  it('keeps an inside place next to its container', () => {
    // 'cellar' starts far from 'keep' in the journey layout.
    const places = nodes('keep', 'road', 'bridge', 'gate', 'cellar')
    const layout = relationshipLayout(places, [edge('cellar', 'inside', 'keep')])

    expect(distance(layout, 'cellar', 'keep')).toBeCloseTo(INSIDE_DISTANCE, 0)
    for (const other of ['road', 'bridge', 'gate']) {
      expect(distance(layout, 'cellar', 'keep')).toBeLessThan(distance(layout, 'cellar', other))
    }
  })

  it('pulls near places together', () => {
    const places = nodes('a', 'b', 'c', 'd', 'e', 'f')
    const layout = relationshipLayout(places, [edge('a', 'near', 'f')])

    expect(distance(layout, 'a', 'f')).toBeLessThanOrEqual(NEAR_DISTANCE + SLACK)
  })

  it('never lets two places overlap', () => {
    const places = nodes('a', 'b', 'c', 'd', 'e', 'f', 'g')
    const layout = relationshipLayout(places, [
      edge('a', 'near', 'b'),
      edge('b', 'near', 'c'),
      edge('c', 'near', 'a'),
      edge('d', 'inside', 'a'),
      edge('e', 'north_of', 'a'),
      edge('f', 'east_of', 'e'),
      edge('g', 'near', 'f'),
    ])

    for (let i = 0; i < places.length; i += 1) {
      for (let j = i + 1; j < places.length; j += 1) {
        const pair = [places[i].id, places[j].id].sort().join('')
        const minimum = pair === 'ad' ? INSIDE_DISTANCE : MIN_SEPARATION
        expect(distance(layout, places[i].id, places[j].id)).toBeGreaterThanOrEqual(minimum - SLACK)
      }
    }
  })

  it('finishes on contradictory relationships', () => {
    const layout = relationshipLayout(nodes('a', 'b'), [
      edge('a', 'north_of', 'b'),
      edge('b', 'north_of', 'a'),
    ])

    expect(Number.isFinite(at(layout, 'a').y)).toBe(true)
    expect(distance(layout, 'a', 'b')).toBeGreaterThanOrEqual(MIN_SEPARATION - SLACK)
  })

  it('lays out the same graph the same way every time', () => {
    const places = nodes('a', 'b', 'c', 'd')
    const links = [edge('b', 'inside', 'a'), edge('c', 'north_of', 'a'), edge('d', 'near', 'c')]

    expect(relationshipLayout(places, links)).toEqual(relationshipLayout(places, links))
  })

  it('keeps every place on the canvas', () => {
    const layout = relationshipLayout(nodes('a', 'b', 'c'), [
      edge('a', 'north_of', 'b'),
      edge('c', 'east_of', 'b'),
    ])

    for (const point of layout.positions.values()) {
      expect(point.x).toBeGreaterThan(0)
      expect(point.y).toBeGreaterThan(0)
      expect(point.x).toBeLessThan(layout.width)
      expect(point.y).toBeLessThan(layout.height)
    }
  })

  it('ignores links to places that are not on the map', () => {
    const places = nodes('a', 'b')

    expect(relationshipLayout(places, [edge('a', 'near', 'ghost')])).toEqual(journeyLayout(places))
  })
})
