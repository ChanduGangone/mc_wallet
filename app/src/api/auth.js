import client from './client'

export function signup({ email, password, name, default_currency }) {
  const payload = { email, password }
  if (name) payload.name = name
  if (default_currency) payload.default_currency = default_currency
  return client.post('/auth/signup', payload).then((r) => r.data)
}

export function login({ email, password }) {
  return client.post('/auth/login', { email, password }).then((r) => r.data)
}

export function refresh(refreshToken) {
  return client.post('/auth/refresh', { refresh_token: refreshToken }).then((r) => r.data)
}

export function logout(refreshToken) {
  return client.post('/auth/logout', { refresh_token: refreshToken })
}

export function getMe() {
  return client.get('/users/me').then((r) => r.data)
}

export function updateMe(fields) {
  const formData = new FormData()
  if (fields.name !== undefined) formData.append('name', fields.name)
  if (fields.default_currency !== undefined) formData.append('default_currency', fields.default_currency)
  if (fields.photoFile) {
    formData.append('photo', fields.photoFile)
  } else if (fields.photo_url !== undefined && fields.photo_url !== '') {
    formData.append('photo_url', fields.photo_url)
  }
  return client.patch('/users/me', formData).then((r) => r.data)
}
