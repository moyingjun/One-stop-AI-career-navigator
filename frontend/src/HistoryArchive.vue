<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, History, FileText, Bot, Compass, Search, Loader2 } from 'lucide-vue-next'

const router = useRouter()

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const historyRecords = ref([])
const isLoading = ref(true)
const searchQuery = ref('')
const filterCategory = ref('all')

const loadHistory = async () => {
  isLoading.value = true
  try {
    const res = await fetch(`${API_BASE_URL.replace('/api', '')}/api/history?limit=100`)
    if (res.ok) {
      const data = await res.json()
      historyRecords.value = data.records || []
    }
  } catch (err) {
    console.error('加载历史记录失败:', err)
  } finally {
    isLoading.value = false
  }
}

const filteredRecords = ref([])

const applyFilter = () => {
  let records = historyRecords.value
  if (filterCategory.value !== 'all') {
    records = records.filter(r => r.category === filterCategory.value)
  }
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    records = records.filter(r => 
      (r.user_input && r.user_input.toLowerCase().includes(query)) ||
      (r.ai_result && r.ai_result.toLowerCase().includes(query))
    )
  }
  filteredRecords.value = records
}

const getCategoryLabel = (cat) => {
  if (cat === 'resume_diagnosis') return '简历诊断'
  if (cat === 'interview_evaluate') return '面试评估'
  if (cat === 'career_planning') return '职业规划'
  return cat
}

const getCategoryIcon = (cat) => {
  if (cat === 'resume_diagnosis') return FileText
  if (cat === 'interview_evaluate') return Bot
  if (cat === 'career_planning') return Compass
  return History
}

const getCategoryColor = (cat) => {
  if (cat === 'resume_diagnosis') return 'text-purple-400 border-purple-500/30 bg-purple-500/5'
  if (cat === 'interview_evaluate') return 'text-pink-400 border-pink-500/30 bg-pink-500/5'
  if (cat === 'career_planning') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5'
  return 'text-gray-400 border-gray-500/30 bg-gray-500/5'
}

const goToRecord = (record) => {
  if (record.category === 'resume_diagnosis') router.push(`/resume-diagnosis?id=${record.id}`)
  else if (record.category === 'interview_evaluate') router.push(`/interview?id=${record.id}`)
  else if (record.category === 'career_planning') router.push(`/career-planning?id=${record.id}`)
}

onMounted(async () => {
  await loadHistory()
  applyFilter()
})
</script>

<template>
  <div class="min-h-[100dvh] bg-[#050505] relative overflow-hidden">
    <div class="absolute top-0 left-0 w-full h-full pointer-events-none z-0">
      <div class="absolute top-0 left-0 w-[50vw] h-[50vh] bg-gradient-to-br from-purple-600/10 via-pink-500/5 to-transparent blur-3xl animate-pulse-slow"></div>
      <div class="absolute bottom-0 right-0 w-[50vw] h-[50vh] bg-gradient-to-tl from-cyan-500/10 via-blue-500/5 to-transparent blur-3xl animate-pulse-slower"></div>
    </div>

    <div class="relative z-10 flex flex-col h-full">
      <div class="bg-white/[0.02] backdrop-blur-xl border-b border-white/[0.05] px-4 py-4">
        <div class="max-w-6xl mx-auto flex items-center justify-between">
          <div class="flex items-center gap-3">
            <button @click="router.push('/dashboard')" class="p-2 rounded-lg hover:bg-white/5 transition-all duration-300 group">
              <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
            </button>
            <div class="flex items-center gap-2">
              <History class="w-6 h-6 text-purple-400" />
              <h1 class="text-xl font-bold text-white">历史档案</h1>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                v-model="searchQuery"
                @input="applyFilter"
                type="text"
                placeholder="搜索记录..."
                class="bg-white/5 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500/50 w-48 md:w-64 transition-all duration-300"
              />
            </div>
            <select
              v-model="filterCategory"
              @change="applyFilter"
              class="bg-white/5 border border-white/10 rounded-lg py-2 px-3 text-sm text-gray-300 focus:outline-none focus:border-purple-500/50 transition-all duration-300"
            >
              <option value="all">全部类型</option>
              <option value="resume_diagnosis">简历诊断</option>
              <option value="interview_evaluate">面试评估</option>
              <option value="career_planning">职业规划</option>
            </select>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4 md:p-6">
        <div class="max-w-6xl mx-auto">
          <div v-if="isLoading" class="flex items-center justify-center h-64">
            <Loader2 class="w-8 h-8 text-purple-400 animate-spin" />
          </div>

          <div v-else-if="filteredRecords.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
            <History class="w-12 h-12 text-gray-600 mb-4" />
            <p class="text-gray-500">暂无历史记录</p>
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="record in filteredRecords"
              :key="record.id"
              @click="goToRecord(record)"
              class="group relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-2xl p-5 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-purple-500/30 hover:shadow-[0_0_20px_rgba(168,85,247,0.1)]"
            >
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                  <component :is="getCategoryIcon(record.category)" class="w-4 h-4" :class="getCategoryColor(record.category).split(' ')[0]" />
                  <span class="text-xs px-2 py-0.5 rounded-full border" :class="getCategoryColor(record.category)">{{ getCategoryLabel(record.category) }}</span>
                </div>
                <span class="text-[10px] text-gray-600">{{ record.created_at }}</span>
              </div>
              <p class="text-sm text-gray-300 line-clamp-2 mb-2">{{ record.user_input || '无输入记录' }}</p>
              <p v-if="record.ai_result" class="text-xs text-gray-500 line-clamp-2">{{ record.ai_result.substring(0, 100) }}...</p>
              <div v-if="record.scores" class="mt-3 flex flex-wrap gap-1">
                <span v-for="(value, key) in JSON.parse(record.scores)" :key="key" class="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400">
                  {{ key }}: {{ value }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }
.animate-pulse-slower { animation: pulse-slow 8s ease-in-out infinite; animation-delay: -4s; }
@keyframes pulse-slow { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 1; } }
.line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
