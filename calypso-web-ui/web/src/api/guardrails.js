import apiClient from './client'

export const getRules = () => {
  return apiClient.get('/guardrails/rules')
}

export const createRule = (data) => {
  return apiClient.post('/guardrails/rules', data)
}

export const getPresets = () => {
  return apiClient.get('/guardrails/presets')
}

export const scanPrompt = (data) => {
  return apiClient.post('/guardrails/scan', data)
}

export const getGuardrailsLogs = (params) => {
  return apiClient.get('/guardrails/logs', { params })
}
