import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProjects } from '../api/projects'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref([])
  const loading = ref(false)
  const lastFetched = ref(0)

  /**
   * 获取项目列表
   * @param {boolean} force 是否强制重新从后端拉取
   */
  async function fetchProjects(force = false) {
    const now = Date.now()
    // 3秒内非强制拉取且已有数据，则直接复用
    if (!force && projects.value.length > 0 && now - lastFetched.value < 3000) {
      return projects.value
    }
    loading.value = true
    try {
      const res = await getProjects()
      const list = Array.isArray(res) ? res : (res?.projects || res?.data || [])
      projects.value = list
      lastFetched.value = Date.now()
      return projects.value
    } catch (err) {
      console.error('[ProjectsStore] 获取项目列表失败:', err)
      return projects.value
    } finally {
      loading.value = false
    }
  }

  function setProjects(list) {
    projects.value = Array.isArray(list) ? list : []
    lastFetched.value = Date.now()
  }

  function findProjectById(id) {
    if (!id) return null
    return projects.value.find((p) => p.id === id) || null
  }

  return {
    projects,
    loading,
    lastFetched,
    fetchProjects,
    setProjects,
    findProjectById
  }
})
