<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import {
  ArrowLeft,
  Bot,
  Bookmark,
  Compass,
  FileText,
  History,
  Loader2,
  Search,
  Star,
  Trash2,
  X
} from 'lucide-vue-next'
import CustomDropdown from '@/components/CustomDropdown.vue'

const router = useRouter()

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const historyRecords = ref([])
const isLoading = ref(true)
const searchQuery = ref('')
const filterCategory = ref('all')
const filterSaved = ref('all')

/** 类型过滤选项列表，供 CustomDropdown 使用 Requirements: 12.1, 12.2, 12.3, 12.4 */
const categoryFilterOptions = [
  { value: 'all', label: '全部类型' },
  { value: 'resume_diagnosis', label: '简历诊断' },
  { value: 'interview', label: '面试评估' },
  { value: 'career_planning', label: '职业规划' },
  { value: 'general_chat', label: '职场助理' },
  { value: 'agent_', label: 'Agent 对话' }
]
const showClearConfirm = ref(false)
const isClearing = ref(false)
const busyRecordIds = ref(new Set())

const loadHistory = async () => {
  isLoading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/history?limit=100`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    historyRecords.value = data.records || []
  } catch (err) {
    console.error('加载历史记录失败:', err)
  } finally {
    isLoading.value = false
  }
}

const filteredRecords = computed(() => {
  let records = historyRecords.value

  // 收藏状态过滤
  if (filterSaved.value === 'saved') {
    records = records.filter(r => r.is_saved === 1 || r.is_saved === true)
  }

  // 类型过滤：interview_ 和 agent_ 前缀类型使用 startsWith 匹配，其余精确匹配
  if (filterCategory.value !== 'all') {
    if (filterCategory.value === 'interview') {
      records = records.filter(r => r.category?.startsWith('interview'))
    } else if (filterCategory.value === 'agent_') {
      records = records.filter(r => r.category?.startsWith('agent_'))
    } else {
      records = records.filter(r => r.category === filterCategory.value)
    }
  }

  // 搜索过滤（保留原有逻辑）
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    records = records.filter(r =>
      String(r.user_input || '').toLowerCase().includes(query) ||
      String(r.ai_result || '').toLowerCase().includes(query)
    )
  }

  return records
})

const getCategoryLabel = (cat) => {
  if (cat === 'resume_diagnosis') return '简历诊断'
  if (cat === 'interview_evaluate') return '面试评估'
  if (cat?.startsWith?.('interview')) return '模拟面试'
  if (cat === 'career_planning') return '职业规划'
  if (cat?.startsWith?.('agent_')) return 'Agent 对话'
  if (cat === 'general_chat') return '职场助理'
  return cat || '未知记录'
}

const getCategoryIcon = (cat) => {
  if (cat === 'resume_diagnosis') return FileText
  if (cat?.startsWith?.('interview')) return Bot
  if (cat === 'career_planning') return Compass
  if (cat?.startsWith?.('agent_')) return Bookmark
  return History
}

const getCategoryColor = (cat) => {
  if (cat === 'resume_diagnosis') return 'text-purple-400 border-purple-500/30 bg-purple-500/5'
  if (cat?.startsWith?.('interview')) return 'text-pink-400 border-pink-500/30 bg-pink-500/5'
  if (cat === 'career_planning') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5'
  if (cat?.startsWith?.('agent_')) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/5'
  return 'text-gray-400 border-gray-500/30 bg-gray-500/5'
}

const goToRecord = (record) => {
  if (record.category === 'resume_diagnosis') router.push(`/resume-diagnosis?id=${record.id}`)
  else if (record.category?.startsWith?.('interview')) router.push(`/interview?id=${record.id}`)
  else if (record.category === 'career_planning') router.push(`/career-planning?id=${record.id}`)
  // 新增：Agent 对话 + 通用聊天 → Dashboard 恢复上下文
  else if (record.category?.startsWith?.('agent_') || record.category === 'general_chat')
    router.push(`/dashboard?chat_id=${record.id}`)
}

const markBusy = (recordId, busy) => {
  const next = new Set(busyRecordIds.value)
  if (busy) next.add(recordId)
  else next.delete(recordId)
  busyRecordIds.value = next
}

const deleteHistoryRecord = async (record) => {
  markBusy(record.id, true)
  try {
    const res = await fetch(`${API_BASE_URL}/history/${record.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    historyRecords.value = historyRecords.value.filter((item) => item.id !== record.id)
  } catch (err) {
    console.error('删除历史记录失败:', err)
  } finally {
    markBusy(record.id, false)
  }
}

const toggleSaveRecord = async (record) => {
  const nextSaved = !record.is_saved
  markBusy(record.id, true)
  try {
    const res = await fetch(`${API_BASE_URL}/history/${record.id}/save`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_saved: nextSaved })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    historyRecords.value = historyRecords.value.map((item) =>
      item.id === record.id ? { ...item, is_saved: nextSaved } : item
    )
  } catch (err) {
    console.error('保存状态切换失败:', err)
  } finally {
    markBusy(record.id, false)
  }
}

const clearAllHistory = async () => {
  isClearing.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/history/clear`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    historyRecords.value = []
    showClearConfirm.value = false
  } catch (err) {
    console.error('清空历史记录失败:', err)
  } finally {
    isClearing.value = false
  }
}

const parseScores = (scores) => {
  try {
    const parsed = typeof scores === 'string' ? JSON.parse(scores) : scores
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

onMounted(loadHistory)
</script>

<template>
  <div class="min-h-[100dvh] bg-[#050505] relative overflow-hidden text-gray-200">
    <div class="absolute inset-0 pointer-events-none z-0">
      <div class="absolute top-0 left-0 w-[50vw] h-[50vh] bg-gradient-to-br from-purple-600/10 via-pink-500/5 to-transparent blur-3xl animate-pulse-slow"></div>
      <div class="absolute bottom-0 right-0 w-[50vw] h-[50vh] bg-gradient-to-tl from-cyan-500/10 via-blue-500/5 to-transparent blur-3xl animate-pulse-slower"></div>
    </div>

    <div class="relative z-10 flex flex-col h-full">
      <div class="bg-white/[0.02] backdrop-blur-xl border-b border-white/[0.05] px-4 py-4">
        <div class="max-w-6xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <button @click="router.push('/dashboard')" class="p-2 rounded-lg hover:bg-white/5 transition-all duration-300 group">
              <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
            </button>
            <div class="flex items-center gap-2">
              <History class="w-6 h-6 text-purple-400" />
              <h1 class="text-xl font-bold text-white">历史档案</h1>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <!-- Segmented Control 收藏过滤 -->
            <div class="flex items-center gap-1 p-1 rounded-lg bg-white/5 backdrop-blur-sm border border-white/10">
              <button
                @click="filterSaved = 'all'"
                :class="[
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200',
                  filterSaved === 'all'
                    ? 'bg-purple-500/20 text-purple-300 shadow-[0_0_10px_rgba(168,85,247,0.3)] border border-purple-500/30'
                    : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
                ]"
              >
                全部记录
              </button>
              <button
                @click="filterSaved = 'saved'"
                :class="[
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200',
                  filterSaved === 'saved'
                    ? 'bg-purple-500/20 text-purple-300 shadow-[0_0_10px_rgba(168,85,247,0.3)] border border-purple-500/30'
                    : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
                ]"
              >
                🌟 仅看收藏
              </button>
            </div>
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                v-model="searchQuery"
                type="text"
                placeholder="搜索记录..."
                class="bg-white/5 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500/50 w-48 md:w-64 transition-all duration-300"
              />
            </div>
            <!-- 类型过滤下拉：使用 CustomDropdown 替换原生 select Requirements: 11.9, 12.1-12.4 -->
            <div class="w-44">
              <CustomDropdown
                v-model="filterCategory"
                :options="categoryFilterOptions"
                placeholder="全部类型"
              />
            </div>
            <button
              v-if="historyRecords.length > 0"
              @click="showClearConfirm = true"
              class="px-3 py-2 rounded-lg border border-red-500/25 bg-red-500/5 text-sm text-red-300 hover:bg-red-500/15 hover:border-red-400/50 hover:shadow-[0_0_18px_rgba(248,113,113,0.18)] transition-all duration-300 flex items-center gap-2"
            >
              <Trash2 class="w-4 h-4" />
              清空全部
            </button>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4 md:p-6">
        <div class="max-w-6xl mx-auto">
          <div v-if="isLoading" class="flex items-center justify-center h-64">
            <Loader2 class="w-8 h-8 text-purple-400 animate-spin" />
          </div>

          <div v-else-if="filteredRecords.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
            <component :is="filterSaved === 'saved' ? Star : History" class="w-12 h-12 text-gray-600 mb-4" />
            <p class="text-gray-500">
              {{ filterSaved === 'saved' ? '暂无收藏记录，去收藏一些对话吧 🌟' : '暂无历史记录' }}
            </p>
          </div>

          <div v-else v-auto-animate class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="record in filteredRecords"
              :key="record.id"
              @click="goToRecord(record)"
              class="group relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-2xl p-5 pb-14 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-purple-500/30 hover:shadow-[0_0_20px_rgba(168,85,247,0.1)]"
            >
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2 min-w-0">
                  <component :is="getCategoryIcon(record.category)" class="w-4 h-4 flex-shrink-0" :class="getCategoryColor(record.category).split(' ')[0]" />
                  <span class="text-xs px-2 py-0.5 rounded-full border truncate font-bold" :class="getCategoryColor(record.category)">{{ getCategoryLabel(record.category) }}</span>
                </div>
                <span class="text-[10px] text-gray-600 flex-shrink-0 ml-2">{{ record.created_at }}</span>
              </div>
              <p class="text-sm text-gray-300 line-clamp-2 mb-2">{{ record.user_input || '无输入记录' }}</p>
              <p v-if="record.ai_result" class="text-xs text-gray-500 line-clamp-2">{{ record.ai_result.substring(0, 100) }}...</p>
              <div v-if="Object.keys(parseScores(record.scores)).length" class="mt-3 flex flex-wrap gap-1">
                <span v-for="(value, key) in parseScores(record.scores)" :key="key" class="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400">
                  {{ key }}: {{ value }}
                </span>
              </div>

              <div class="absolute right-4 bottom-4 flex items-center gap-2">
                <button
                  @click.stop="toggleSaveRecord(record)"
                  :disabled="busyRecordIds.has(record.id)"
                  class="w-9 h-9 rounded-full border backdrop-blur flex items-center justify-center transition-all duration-300"
                  :class="record.is_saved
                    ? 'border-amber-300/50 bg-amber-400/10 text-amber-300 shadow-[0_0_16px_rgba(251,191,36,0.22)]'
                    : 'border-white/10 bg-black/20 text-gray-500 hover:text-amber-300 hover:border-amber-300/40 hover:bg-amber-400/10'"
                  title="保存/取消保存"
                >
                  <Star class="w-4 h-4" :fill="record.is_saved ? 'currentColor' : 'none'" />
                </button>
                <button
                  @click.stop="deleteHistoryRecord(record)"
                  :disabled="busyRecordIds.has(record.id)"
                  class="w-9 h-9 rounded-full border border-white/10 bg-black/20 text-gray-500 backdrop-blur flex items-center justify-center hover:text-red-300 hover:border-red-400/40 hover:bg-red-500/10 hover:shadow-[0_0_16px_rgba(248,113,113,0.18)] transition-all duration-300"
                  title="删除记录"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showClearConfirm" class="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showClearConfirm = false"></div>
      <div class="relative w-full max-w-md rounded-2xl border border-red-400/25 bg-[#101018]/90 backdrop-blur-2xl p-6 shadow-[0_0_40px_rgba(248,113,113,0.12)]">
        <button @click="showClearConfirm = false" class="absolute right-4 top-4 text-gray-500 hover:text-white transition-colors">
          <X class="w-4 h-4" />
        </button>
        <div class="w-12 h-12 rounded-xl bg-red-500/10 border border-red-400/20 flex items-center justify-center mb-4">
          <Trash2 class="w-6 h-6 text-red-300" />
        </div>
        <h2 class="text-lg font-bold text-white mb-2">确定要清空所有历史记录吗？</h2>
        <p class="text-sm text-gray-400 mb-6">此操作不可恢复。</p>
        <div class="flex gap-3">
          <button @click="showClearConfirm = false" class="flex-1 py-2.5 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 transition-all duration-300">取消</button>
          <button
            @click="clearAllHistory"
            :disabled="isClearing"
            class="flex-1 py-2.5 rounded-xl bg-red-500/15 border border-red-400/30 text-red-200 hover:bg-red-500/25 hover:shadow-[0_0_18px_rgba(248,113,113,0.2)] transition-all duration-300 flex items-center justify-center gap-2"
          >
            <Loader2 v-if="isClearing" class="w-4 h-4 animate-spin" />
            确认清空
          </button>
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
