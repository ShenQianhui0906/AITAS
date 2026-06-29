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

async function requestBlob(path) {
  const headers = {}
  const token = localStorage.getItem('ai_tutor_token')
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${BASE}${path}`, { headers })
  if (!response.ok) {
    let message = '文件读取失败，请稍后重试。'
    try {
      const payload = await response.json()
      message = payload?.error || message
    } catch { /* non-JSON error response */ }
    throw new Error(message)
  }
  return response.blob()
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
  events(params, options = {}) { return request(buildPath('/api/messages/events', params), options) },
}

export const aiApi = {
  messages(params) { return request(buildPath('/api/ai/messages', params)) },
  ask(body) { return request('/api/ai/chat', { method: 'POST', body }) },
  clear(params) { return request(buildPath('/api/ai/messages', params), { method: 'DELETE' }) },
}

export const ragApi = {
  status(params, opts) { return request(buildPath('/api/rag/status', params), opts) },
  messages(params) { return request(buildPath('/api/rag/messages', params)) },
  ask(body, opts) { return request('/api/rag/ask', { method: 'POST', body, ...opts }) },
  index(body, opts) { return request('/api/rag/index', { method: 'POST', body, ...opts }) },
  clear(params) { return request(buildPath('/api/rag/messages', params), { method: 'DELETE' }) },
}

export const agentApi = {
  messages(params) { return request(buildPath('/api/ai/agent/messages', params)) },
  ask(body) { return request('/api/ai/agent', { method: 'POST', body }) },
  clear(params) { return request(buildPath('/api/ai/agent/messages', params), { method: 'DELETE' }) },
}

export const assignmentsApi = {
  list(params) { return request(buildPath('/api/assignments', params)) },
  detail(id) { return request(`/api/assignments/${id}`) },
  create(body) { return request('/api/assignments', { method: 'POST', body }) },
  delete(id) { return request(`/api/assignments/${id}`, { method: 'DELETE' }) },
  submit(id, formData) { return request(`/api/assignments/${id}/submit`, { method: 'POST', body: formData }) },
  grade(assignmentId, submissionId, body) {
    return request(`/api/assignments/${assignmentId}/submissions/${submissionId}/grade`, { method: 'PUT', body })
  },
  rubric(assignmentId) {
    return request(`/api/assignments/${assignmentId}/rubric`)
  },
  saveRubric(assignmentId, body) {
    return request(`/api/assignments/${assignmentId}/rubric`, { method: 'PUT', body })
  },
  regenerateRubric(assignmentId) {
    return request(`/api/assignments/${assignmentId}/rubric/regenerate`, { method: 'POST' })
  },
  aiGrade(assignmentId, submissionId) {
    return request(`/api/assignments/${assignmentId}/submissions/${submissionId}/ai-grade`, { method: 'POST' })
  },
  discardAiGrade(assignmentId, submissionId) {
    return request(`/api/assignments/${assignmentId}/submissions/${submissionId}/ai-grade`, { method: 'DELETE' })
  },
  file(fileId, { download = false } = {}) {
    return requestBlob(buildPath(`/api/assignments/files/${fileId}`, { download: download ? 1 : '' }))
  },
  preview(fileId) { return requestBlob(`/api/assignments/files/${fileId}/preview`) },
}

export const quizApi = {
  list(params) { return request(buildPath('/api/quizzes', params)) },
  detail(id) { return request(`/api/quizzes/${id}`) },
  submissions(id) { return request(`/api/quizzes/${id}/submissions`) },
  reviewSubmission(quizId, submissionId, body) {
    return request(`/api/quizzes/${quizId}/submissions/${submissionId}/review`, { method: 'PUT', body })
  },
  generate(body) { return request('/api/quizzes/generate', { method: 'POST', body }) },
  publish(body) { return request('/api/quizzes', { method: 'POST', body }) },
  submit(id, body) { return request(`/api/quizzes/${id}/submit`, { method: 'POST', body }) },
  grade(id) { return request(`/api/quizzes/${id}/grade`, { method: 'POST' }) },
  delete(id) { return request(`/api/quizzes/${id}`, { method: 'DELETE' }) },
}

export const notificationApi = {
  list(params) { return request(buildPath('/api/notifications', params)) },
  unreadCount() { return request('/api/notifications/unread-count') },
  markRead(id) { return request(`/api/notifications/${id}/read`, { method: 'POST' }) },
  markAllRead() { return request('/api/notifications/read-all', { method: 'POST' }) },
}
