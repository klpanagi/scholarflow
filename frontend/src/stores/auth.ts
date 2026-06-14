import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '@/lib/api'

interface User {
  id: string
  email: string
  name: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  refreshAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const formData = new URLSearchParams()
        formData.append('username', email)
        formData.append('password', password)

        const response = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        })

        const { access_token, refresh_token } = response.data
        set({ accessToken: access_token, refreshToken: refresh_token, isAuthenticated: true })

        const userResponse = await api.get('/auth/me', {
          headers: { Authorization: `Bearer ${access_token}` },
        })
        set({ user: userResponse.data })
      },

      register: async (email, password, fullName) => {
        await api.post('/auth/register', {
          email,
          password,
          name: fullName,
        })

        const formData = new URLSearchParams()
        formData.append('username', email)
        formData.append('password', password)

        const loginResponse = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        })

        const { access_token, refresh_token } = loginResponse.data
        set({ accessToken: access_token, refreshToken: refresh_token, isAuthenticated: true })

        const userResponse = await api.get('/auth/me', {
          headers: { Authorization: `Bearer ${access_token}` },
        })
        set({ user: userResponse.data })
      },

      logout: () => {
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      refreshAuth: async () => {
        const { refreshToken } = get()
        if (!refreshToken) return

        try {
          const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
          const { access_token, refresh_token } = response.data
          set({ accessToken: access_token, refreshToken: refresh_token })
        } catch {
          get().logout()
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
