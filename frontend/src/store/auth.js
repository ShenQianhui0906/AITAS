import { defineStore } from 'pinia'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('ai_tutor_token') || '',
    user: null,
    authMode: 'login',
  }),

  getters: {
    isLoggedIn: (state) => !!state.token && !!state.user,
    role: (state) => state.user?.role || null,
    displayName: (state) => state.user?.display_name || state.user?.username || '',
    userInitial: (state) => {
      const name = state.user?.display_name || state.user?.username || 'U'
      return name.slice(0, 1).toUpperCase()
    },
  },

  actions: {
    async login(username, password) {
      const data = await authApi.login({ username, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('ai_tutor_token', this.token)
      return data
    },

    async register(form) {
      const data = await authApi.register(form)
      this.token = data.token
      this.user = data.user
      localStorage.setItem('ai_tutor_token', this.token)
      return data
    },

    async logout() {
      try { await authApi.logout() } catch (_) { /* ignore */ }
      this.token = ''
      this.user = null
      localStorage.removeItem('ai_tutor_token')
    },

    async bootstrap() {
      if (!this.token) return false
      try {
        const data = await authApi.me()
        this.user = data.user
        return true
      } catch {
        this.token = ''
        this.user = null
        localStorage.removeItem('ai_tutor_token')
        return false
      }
    },

    setAuthMode(mode) {
      this.authMode = mode
    },
  },
})
