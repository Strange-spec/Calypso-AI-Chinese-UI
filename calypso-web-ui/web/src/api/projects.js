import apiClient from './client'

export const getProjects = () => {
  return apiClient.get('/projects')
}

export const getProject = (id) => {
  return apiClient.get(`/projects/${id}`)
}

export const createProject = (data) => {
  return apiClient.post('/projects', data)
}

export const updateProject = (id, data) => {
  return apiClient.put(`/projects/${id}`, data)
}

export const deleteProject = (id) => {
  return apiClient.delete(`/projects/${id}`)
}
