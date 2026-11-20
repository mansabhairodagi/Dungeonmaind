import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/** One piece of session audio this browser recorded or uploaded. */
export interface PlaybackClip {
  /** Object URL of the audio, or null while a recording is still running. */
  url: string | null
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
 * The backend puts transcript times on one clock per session: every chunk it
 * receives starts where the previous one ended. Clips are kept here in the
 * same order they were sent, so a transcript time can be turned into a clip
 * and an offset inside it. Audio only lives in this browser tab: after a
 * reload, or for a session loaded from disk, there is nothing to play.
 */
export const usePlaybackStore = defineStore('playback', () => {
  const sessionId = ref<string | null>(null)
  const clips = ref<PlaybackClip[]>([])

  const hasAudio = computed(() => clips.value.some((clip) => clip.url !== null))

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
   * Reserve the next place on the session clock for a clip.
   * Call it when the audio is sent, so clips stay in the backend's order.
   * @param forSessionId - Session the audio is transcribed into.
   * @param url - Object URL of the audio, if it is already available.
   * @param seconds - Length of the audio, if known.
   * @returns The clip's index, for {@link finishClip}.
   */
  function addClip(forSessionId: string, url: string | null = null, seconds: number | null = null) {
    useSession(forSessionId)
    clips.value.push({ url, seconds })
    return clips.value.length - 1
  }

  /**
   * Fill in a clip's audio or length once known.
   * @param index - Index returned by {@link addClip}.
   * @param update - The audio URL and/or length.
   */
  function finishClip(index: number, update: Partial<PlaybackClip>) {
    const clip = clips.value[index]
    if (clip) clips.value[index] = { ...clip, ...update }
  }

  /**
   * Find which clip holds a moment of the session recording.
   * A clip of unknown length is assumed to hold everything after its start.
   * @param seconds - Time on the session clock (a transcript segment start).
   * @returns The clip and offset, or null if that audio is not in this browser.
   */
  function locate(seconds: number): PlaybackPosition | null {
    let clipStart = 0
    for (let index = 0; index < clips.value.length; index += 1) {
      const clip = clips.value[index]
      const clipEnd = clip.seconds === null ? Infinity : clipStart + clip.seconds
      if (seconds < clipEnd || index === clips.value.length - 1) {
        if (!clip.url) return null
        return { clipIndex: index, url: clip.url, offset: Math.max(0, seconds - clipStart) }
      }
      clipStart = clipEnd
    }
    return null
  }

  return { sessionId, clips, hasAudio, useSession, rekey, addClip, finishClip, locate }
})
