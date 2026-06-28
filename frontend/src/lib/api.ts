import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import type {
  ExportBundlePayload,
  ImportConfirmRequestPayload,
  ImportPreviewPayload,
  ImportResultPayload,
} from '@/types/chat'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const { refreshAuth } = useAuthStore.getState()
      await refreshAuth()
      const { accessToken: newToken } = useAuthStore.getState()
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      }
    }
    return Promise.reject(error)
  }
)

export async function exportSkillsAndAgents(): Promise<ExportBundlePayload> {
  const { data } = await api.get<ExportBundlePayload>('/export')
  return data
}

export async function importSkillsAndAgents(file: File): Promise<ImportPreviewPayload> {
  const text = await file.text()
  const bundle: ExportBundlePayload = JSON.parse(text)
  const { data } = await api.post<ImportPreviewPayload>('/import', bundle)
  return data
}

export async function confirmImport(request: ImportConfirmRequestPayload): Promise<ImportResultPayload> {
  const { data } = await api.post<ImportResultPayload>('/import/confirm', request)
  return data
}
