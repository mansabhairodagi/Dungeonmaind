import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePlaybackStore } from '@/stores/playback'

describe('playback store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    URL.revokeObjectURL = vi.fn()
  })

  it('finds a moment inside a single uploaded file', () => {
    const playback = usePlaybackStore()
    playback.addClip('s1', { url: 'blob:upload', start: 0, seconds: 600 })

    expect(playback.locate(125.5)).toEqual({ clipIndex: 0, url: 'blob:upload', offset: 125.5 })
  })

  it('uses where the backend placed each clip on the session clock', () => {
    const playback = usePlaybackStore()
    playback.addClip('s1', { url: 'blob:recording', start: 0, seconds: 90 })
    playback.addClip('s1', { url: 'blob:upload', start: 90, seconds: 300 })

    expect(playback.locate(30)).toEqual({ clipIndex: 0, url: 'blob:recording', offset: 30 })
    expect(playback.locate(100)).toEqual({ clipIndex: 1, url: 'blob:upload', offset: 10 })
  })

  it('does not play earlier session audio that this tab never had', () => {
    // E.g. after a reload: the backend already had 10 minutes for this session.
    const playback = usePlaybackStore()
    playback.addClip('s1', { url: 'blob:recording', start: 600, seconds: 60 })

    expect(playback.locate(30)).toBeNull()
    expect(playback.locate(630)).toEqual({ clipIndex: 0, url: 'blob:recording', offset: 30 })
    expect(playback.locate(700)).toBeNull()
  })

  it('cannot play a clip until it has both audio and a start', () => {
    const playback = usePlaybackStore()
    const index = playback.addClip('s1')

    expect(playback.hasAudio).toBe(false)
    playback.updateClip(index, { url: 'blob:recording', seconds: 40 })
    expect(playback.locate(5)).toBeNull()

    playback.updateClip(index, { start: 0 })
    expect(playback.hasAudio).toBe(true)
    expect(playback.locate(5)).toEqual({ clipIndex: 0, url: 'blob:recording', offset: 5 })
  })

  it('lets a later clip win over an earlier clip of unknown length', () => {
    const playback = usePlaybackStore()
    playback.addClip('s1', { url: 'blob:upload', start: 0 })
    playback.addClip('s1', { url: 'blob:recording', start: 300, seconds: 60 })

    expect(playback.locate(4000)?.url).toBe('blob:upload')
    expect(playback.locate(310)).toEqual({ clipIndex: 1, url: 'blob:recording', offset: 10 })
  })

  it('drops audio from another session but keeps it when a save re-keys the session', () => {
    const playback = usePlaybackStore()
    playback.addClip('draft', { url: 'blob:recording', start: 0, seconds: 60 })

    playback.rekey('draft', 'Campaign/Session_1')
    playback.addClip('Campaign/Session_1', { url: 'blob:upload', start: 60, seconds: 30 })
    expect(playback.clips).toHaveLength(2)

    playback.addClip('Other/Session_2', { url: 'blob:other', start: 0, seconds: 10 })
    expect(playback.clips).toEqual([{ url: 'blob:other', start: 0, seconds: 10 }])
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:recording')
  })
})
