import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null

async function performRefresh() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('No refresh token available')

  // Bare axios call, not `client` — avoids recursively triggering these
  // same interceptors on the refresh request itself.
  const { data } = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
  )

  // Refresh tokens rotate on every use — always persist the newest pair.
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  return data.access_token
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthEndpoint = config?.url?.includes('/auth/login')
      || config?.url?.includes('/auth/refresh')
      || config?.url?.includes('/auth/signup')

    if (response?.status !== 401 || isAuthEndpoint || config._retried) {
      return Promise.reject(error)
    }

    config._retried = true

    try {
      if (!refreshPromise) {
        refreshPromise = performRefresh().finally(() => {
          refreshPromise = null
        })
      }
      const newAccessToken = await refreshPromise
      config.headers.Authorization = `Bearer ${newAccessToken}`
      return client(config)
    } catch (refreshError) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return Promise.reject(refreshError)
    }
  },
)

export default client
