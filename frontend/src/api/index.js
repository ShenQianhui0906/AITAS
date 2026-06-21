const BASE = ''

async function request(path, options = {}) {
  const config = { method: 'GET', ...options }
  config.headers = { ...(config.headers || {}) }

  const token = localStorage.getItem('ai_tutor_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  if (config.body && !(config.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json'
    config.body = JSON.stringify(config.body)
  }

  const response = await fetch(`${BASE}${path}`, config)
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const payload = isJson ? await response.json() : null

  if (!response.ok) {
    throw new Error(payload?.error || '请求失败，请稍后重试。')
  }

  return payload
}

function buildPath(path, params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      search.set(key, value)
    }
  })
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

export const authApi = {
  login(body) { return request('/api/auth/login', { method: 'POST', body }) },
  register(body) { return request('/api/auth/register', { method: 'POST', body }) },
  logout() { return request('/api/auth/logout', { method: 'POST' }) },
  me() { return request('/api/me') },
}

export const dashboardApi = {
  get(params) { return request(buildPath('/api/dashboard', params)) },
}

export const usersApi = {
  list() { return request('/api/users') },
  create(body) { return request('/api/users', { method: 'POST', body }) },
  update(id, body) { return request(`/api/users/${id}`, { method: 'PUT', body }) },
  delete(id) { return request(`/api/users/${id}`, { method: 'DELETE' }) },
}

export const classesApi = {
  list() { return request('/api/classes') },
  available() { return request('/api/classes/available') },
  create(body) { return request('/api/classes', { method: 'POST', body }) },
  update(id, body) { return request(`/api/classes/${id}`, { method: 'PUT', body }) },
  delete(id) { return request(`/api/classes/${id}`, { method: 'DELETE' }) },
  members(id) { return request(`/api/classes/${id}/members`) },
  addMember(classId, studentId) { return request(`/api/classes/${classId}/members`, { method: 'POST', body: { student_id: studentId } }) },
  removeMember(classId, memberId) { return request(`/api/classes/${classId}/members/${memberId}`, { method: 'DELETE' }) },
  join(body) { return request('/api/classes/join', { method: 'POST', body }) },
  approveRequest(id) { return request(`/api/classes/requests/${id}/approve`, { method: 'POST' }) },
  rejectRequest(id) { return request(`/api/classes/requests/${id}/reject`, { method: 'POST' }) },
}

export const coursewaresApi = {
  list(params) { return request(buildPath('/api/coursewares', params)) },
  create(formData) { return request('/api/coursewares', { method: 'POST', body: formData }) },
  update(id, body) { return request(`/api/coursewares/${id}`, { method: 'PUT', body }) },
  delete(id) { return request(`/api/coursewares/${id}`, { method: 'DELETE' }) },
}

export const evaluationsApi = {
  list(params) { return request(buildPath('/api/evaluations', params)) },
  create(body) { return request('/api/evaluations', { method: 'POST', body }) },
}

export const discussionsApi = {
  list(params) { return request(buildPath('/api/discussions', params)) },
  create(body) { return request('/api/discussions', { method: 'POST', body }) },
  reply(discussionId, body) { return request(`/api/discussions/${discussionId}/replies`, { method: 'POST', body }) },
}

export const messagesApi = {
  contacts(params) { return request(buildPath('/api/messages/contacts', params)) },
  conversations() { return request('/api/messages/conversations') },
  addConversation(body) { return request('/api/messages/conversations', { method: 'POST', body }) },
  removeConversation(id) { return request(`/api/messages/conversations/${id}`, { method: 'DELETE' }) },
  thread(userId) { return request(`/api/messages/thread/${userId}`) },
  send(body) { return request('/api/messages', { method: 'POST', body }) },
  events(params) { return request(buildPath('/api/messages/events', params)) },
}

export const aiApi = {
  messages(params) { return request(buildPath('/api/ai/messages', params)) },
  ask(body) { return request('/api/ai/messages', { method: 'POST', body }) },
  clear(params) { return request(buildPath('/api/ai/messages', params), { method: 'DELETE' }) },
}

export const ragApi = {
  status(params) { return request(buildPath('/api/rag/status', params)) },
  messages(params) { return request(buildPath('/api/rag/messages', params)) },
  ask(body) { return request('/api/rag/ask', { method: 'POST', body }) },
  index(body) { return request('/api/rag/index', { method: 'POST', body }) },
  clear(params) { return request(buildPath('/api/rag/messages', params), { method: 'DELETE' }) },
}

export const agentApi = {
  ask(body) { return request('/api/ai/agent', { method: 'POST', body }) },
}
