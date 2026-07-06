import * as authApi from '@/api/auth'

function persistTokens(access, refresh) {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export default {
  namespaced: true,
  state: () => ({
    accessToken: localStorage.getItem('access_token') || null,
    refreshToken: localStorage.getItem('refresh_token') || null,
    user: null,
  }),
  mutations: {
    SET_TOKENS(state, { accessToken, refreshToken }) {
      state.accessToken = accessToken
      state.refreshToken = refreshToken
      persistTokens(accessToken, refreshToken)
    },
    SET_USER(state, user) {
      state.user = user
    },
    CLEAR_AUTH(state) {
      state.accessToken = null
      state.refreshToken = null
      state.user = null
      clearTokens()
    },
  },
  actions: {
    async signup({ dispatch }, payload) {
      await authApi.signup(payload)
      await dispatch('login', { email: payload.email, password: payload.password })
    },
    async login({ commit, dispatch }, { email, password }) {
      const { access_token, refresh_token } = await authApi.login({ email, password })
      commit('SET_TOKENS', { accessToken: access_token, refreshToken: refresh_token })
      await dispatch('fetchCurrentUser')
    },
    async logout({ commit, state }) {
      try {
        if (state.refreshToken) await authApi.logout(state.refreshToken)
      } finally {
        commit('CLEAR_AUTH')
      }
    },
    async fetchCurrentUser({ commit }) {
      const user = await authApi.getMe()
      commit('SET_USER', user)
      return user
    },
    async updateProfile({ commit }, fields) {
      const user = await authApi.updateMe(fields)
      commit('SET_USER', user)
      return user
    },
  },
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    currentUser: (state) => state.user,
  },
}
