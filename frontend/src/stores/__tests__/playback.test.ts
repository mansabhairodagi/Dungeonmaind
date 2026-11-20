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
    playback.addClip('s1', 'blob:upload', 600)

    expect(playback.locate(125.5)).toEqual({ clipIndex: 0, url: 'blob:upload', offset: 125.5 })
  })

  it('maps session time across clips sent one after another', () => {
    const playback = usePlaybackStore()
    playback.addClip('s1', 'blob:recording', 90)
    playback.addClip('s1', 'blob:upload', 300)

    expect(playback.locate(30)).toEqual({ clipIndex: 0, url: 'blob:recording', offset: 30 })
    expect(playback.locate(100)).toEqual({ clipIndex: 1, url: 'blob:upload', offset: 10 })
  })

  it('has nothing to play while a reserved recording is still running', () => {
    const playback = usePlaybackStore()
    const index = playback.addClip('s1')

    expect(playback.hasAudio).toBe(false)
    expect(playback.locate(5)).toBeNull()

    playback.finishClip(index, { url: 'blob:recording', seconds: 40 })
    expect(playback.locate(5)).toEqual({ clipIndex: 0, url: 'blob:recording', offset: 5 })
  })

  it('treats a clip of unknown length as reaching to the end', () => {
    const playback = usePlaybackStore()
    playback.addClip('s1', 'blob:upload')

    expect(playback.locate(4000)?.offset).toBe(4000)
  })

  it('drops audio from another session but keeps it when a save re-keys the session', () => {
    const playback = usePlaybackStore()
    playback.addClip('draft', 'blob:recording', 60)

    playback.rekey('draft', 'Campaign/Session_1')
    playback.addClip('Campaign/Session_1', 'blob:upload', 30)
    expect(playback.clips).toHaveLength(2)

    playback.addClip('Other/Session_2', 'blob:other', 10)
    expect(playback.clips).toEqual([{ url: 'blob:other', seconds: 10 }])
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:recording')
  })
})
