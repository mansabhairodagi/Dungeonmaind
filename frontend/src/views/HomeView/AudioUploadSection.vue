<script setup lang="ts">
/**
 * AudioUploadSection – allows the leader to upload a pre-recorded audio file
 * for transcription by the backend.
 */
import { ref } from 'vue'
import { SERVER_CONFIG } from '@/config/config'
import { usePlaybackStore } from '@/stores/playback'
import { useSessionStore } from '@/stores/session'

const selectedAudioFile = ref<File | null>(null)
const audioUploadStatus = ref<string>('')
const isUploading = ref<boolean>(false)

/** Audio upload */
async function handleAudioUpload() {
  if (!selectedAudioFile.value) {
    audioUploadStatus.value = 'Please choose an audio file.'
    return
  }

  const sessionId = useSessionStore().sessionId
  const formData = new FormData()
  formData.append('audio', selectedAudioFile.value)
  formData.append('session_id', sessionId)
  const clipIndex = keepForPlayback(selectedAudioFile.value, sessionId)

  isUploading.value = true
  audioUploadStatus.value = 'Audio is uploading, please wait...'

  try {
    const response = await fetch(
      `${SERVER_CONFIG.BASE_URL}${SERVER_CONFIG.ENDPOINTS.TRANSCRIBE_AUDIO_FILE}`,
      {
        method: 'POST',
        body: formData,
      },
    )
    if (!response.ok) {
      throw new Error(`Upload failed with status ${response.status}`)
    }
    const result = await response.json()
    if (typeof result.audio_offset === 'number') {
      usePlaybackStore().updateClip(clipIndex, { start: result.audio_offset })
    }
    audioUploadStatus.value = `Upload successful: ${result.message || 'Audio file received'}`
  } catch (error) {
    console.error('An error occurred while uploading your audio file:', error)
    audioUploadStatus.value = 'Upload error'
  } finally {
    isUploading.value = false
  }
}

/**
 * Keep the uploaded file so the map can jump to moments in it.
 * The backend's answer says where the file starts on the session clock.
 * @param file - The audio file being uploaded.
 * @param sessionId - Session the audio is transcribed into.
 * @returns The clip's index in the playback store.
 */
function keepForPlayback(file: File, sessionId: string) {
  const playback = usePlaybackStore()
  const url = URL.createObjectURL(file)
  const clipIndex = playback.addClip(sessionId, { url })
  const probe = new Audio()
  probe.preload = 'metadata'
  probe.onloadedmetadata = () => {
    if (Number.isFinite(probe.duration)) playback.updateClip(clipIndex, { seconds: probe.duration })
  }
  probe.src = url
  return clipIndex
}

function onAudioFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  selectedAudioFile.value = target?.files && target.files.length > 0 ? target.files[0] : null
}
</script>

<style scoped>
.output {
  margin-bottom: var(--dm-space-4);
}
</style>

<template>
  <div class="content-section">
    <!-- Leader-only: upload -->
    <h2>Upload Audio File</h2>
    <input type="file" accept="audio/*" @change="onAudioFileChange" class="input-field" />

    <div v-if="audioUploadStatus" class="output">
      <p>{{ audioUploadStatus }}</p>
    </div>

    <button @click="handleAudioUpload" class="submit-button" :disabled="isUploading">
      {{ isUploading ? 'Uploading...' : 'Upload Audio' }}
    </button>
  </div>
</template>
