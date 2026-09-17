import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：自动注入 Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('calypso_api_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：统一数据解包与错误提示
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '网络请求异常，请稍后重试'
    ElMessage.error({
      message: `请求失败: ${message}`,
      duration: 4000
    })
    return Promise.reject(error)
  }
)

export default apiClient
export { apiClient }
