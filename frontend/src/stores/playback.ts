import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/** One piece of session audio this browser recorded or uploaded. */
export interface PlaybackClip {
  /** Object URL of the audio, or null while a recording is still running. */
  url: string | null
  /** Where the clip starts on the session clock, or null until the backend says. */
  start: number | null
  /** Length in seconds, or null until it is known. */
  seconds: number | null
}

/** Where a moment of the session recording is found among the clips. */
export interface PlaybackPosition {
  clipIndex: number
  url: string
  /** Seconds into that clip. */
  offset: number
}

/**
 * Playback store – keeps the audio sent for transcription so the map can jump
 * to the moment a place was mentioned.
 *
 * The backend puts transcript times on one clock per session and reports
 * where each piece of audio it receives starts on that clock
 * (`audio_offset`). Each clip here is anchored at that start, so a transcript
 * time can be turned into a clip and an offset inside it, even when the
 * session already had audio from before this tab was opened. Audio only
 * lives in this browser tab: times outside the kept clips cannot be played.
 */
export const usePlaybackStore = defineStore('playback', () => {
  const sessionId = ref<string | null>(null)
  const clips = ref<PlaybackClip[]>([])

  const hasAudio = computed(() => clips.value.some((clip) => clip.url && clip.start !== null))

  /** Forget clips that belong to another session. */
  function useSession(forSessionId: string) {
    if (sessionId.value === forSessionId) return
    clips.value.forEach((clip) => clip.url && URL.revokeObjectURL(clip.url))
    clips.value = []
    sessionId.value = forSessionId
  }

  /**
   * Keep the clips when a save moves the session to a new key. The backend
   * moves the transcript with it, so the times still match the audio.
   * @param fromSessionId - Key the session was running under.
   * @param toSessionId - Key it was saved under.
   */
  function rekey(fromSessionId: string, toSessionId: string) {
    if (sessionId.value === fromSessionId) sessionId.value = toSessionId
  }

  /**
   * Keep a clip of session audio. Its start and length can follow later.
   * @param forSessionId - Session the audio is transcribed into.
   * @param clip - What is known about the clip so far.
   * @returns The clip's index, for {@link updateClip}.
   */
  function addClip(forSessionId: string, clip: Partial<PlaybackClip> = {}) {
    useSession(forSessionId)
    clips.value.push({ url: null, start: null, seconds: null, ...clip })
    return clips.value.length - 1
  }

  /**
   * Fill in a clip's audio, start or length once known.
   * @param index - Index returned by {@link addClip}.
   * @param update - The fields to set.
   */
  function updateClip(index: number, update: Partial<PlaybackClip>) {
    const clip = clips.value[index]
    if (clip) clips.value[index] = { ...clip, ...update }
  }

  /**
   * Find which clip holds a moment of the session recording.
   * A clip of unknown length is assumed to run until the next clip starts.
   * @param seconds - Time on the session clock (a transcript segment start).
   * @returns The clip and offset, or null if that audio is not in this browser.
   */
  function locate(seconds: number): PlaybackPosition | null {
    let best: PlaybackPosition | null = null
    let bestStart = -Infinity
    clips.value.forEach((clip, clipIndex) => {
      if (!clip.url || clip.start === null) return
      if (seconds < clip.start || clip.start < bestStart) return
      if (clip.seconds !== null && seconds >= clip.start + clip.seconds) return
      best = { clipIndex, url: clip.url, offset: seconds - clip.start }
      bestStart = clip.start
    })
    return best
  }

  return { sessionId, clips, hasAudio, useSession, rekey, addClip, updateClip, locate }
})
