<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Bot, Bookmark, Compass, FileText, Loader2, Search, Star, Trash2, X } from 'lucide-vue-next'

const router = useRouter()
const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const records = ref([])
const isLoading = ref(true)
const searchQuery = ref('')
const busyRecordIds = ref(new Set())
const selectedChat = ref(null)
const showChatModal = ref(false)

const loadSavedChats = async () => {
  isLoading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/history/saved`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    records.value = data.records || []
  } catch (err) {
    console.error('加载保存对话失败:', err)
  } finally {
    isLoading.value = false
  }
}

const filteredRecords = computed(() => {
  if (!searchQuery.value.trim()) return records.value
  const query = searchQuery.value.toLowerCase()
  return records.value.filter((record) =>
    String(record.user_input || '').toLowerCase().includes(query) ||
    String(record.ai_result || '').toLowerCase().includes(query)
  )
})

const getCategoryLabel = (cat) => {
  if (cat === 'resume_diagnosis') return '简历诊断'
  if (cat?.startsWith?.('interview')) return '模拟面试'
  if (cat === 'career_planning') return '职业规划'
  if (cat?.startsWith?.('agent_')) return 'Agent 对话'
  if (cat === 'general_chat') return '职场助理'
  return cat || '已保存对话'
}

const getCategoryIcon = (cat) => {
  if (cat === 'resume_diagnosis') return FileText
  if (cat?.startsWith?.('interview')) return Bot
  if (cat === 'career_planning') return Compass
  return Bookmark
}

const getCategoryColor = (cat) => {
  if (cat === 'resume_diagnosis') return 'text-purple-400 border-purple-500/30 bg-purple-500/5'
  if (cat?.startsWith?.('interview')) return 'text-pink-400 border-pink-500/30 bg-pink-500/5'
  if (cat === 'career_planning') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5'
  return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/5'
}

const normalizeChatHistory = (record) => {
  let history = record?.chat_history

  if (typeof history === 'string') {
    try {
      history = JSON.parse(history)
    } catch {
      history = []
    }
  }

  if (Array.isArray(history) && history.length > 0) {
    return history.map((message, index) => ({
      id: message.id || `${record.id}-history-${index}`,
      role: message.role || message.type || message.sender || 'assistant',
      content: message.content || message.text || message.message || ''
    })).filter((message) => String(message.content || '').trim())
  }

  const fallback = []
  if (record?.user_input) {
    fallback.push({ id: `${record.id}-user`, role: 'user', content: record.user_input })
  }
  if (record?.ai_result) {
    fallback.push({ id: `${record.id}-assistant`, role: 'assistant', content: record.ai_result })
  }
  return fallback
}

const selectedChatMessages = computed(() => normalizeChatHistory(selectedChat.value))

const isUserMessage = (message) => {
  const role = String(message.role || '').toLowerCase()
  return role === 'user' || role === 'human'
}

const openChatModal = (record) => {
  selectedChat.value = record
  showChatModal.value = true
}

const closeChatModal = () => {
  showChatModal.value = false
  selectedChat.value = null
}

const markBusy = (recordId, busy) => {
  const next = new Set(busyRecordIds.value)
  if (busy) next.add(recordId)
  else next.delete(recordId)
  busyRecordIds.value = next
}

const unsaveRecord = async (record) => {
  markBusy(record.id, true)
  try {
    const res = await fetch(`${API_BASE_URL}/history/${record.id}/save`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_saved: false })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    records.value = records.value.filter((item) => item.id !== record.id)
  } catch (err) {
    console.error('取消保存失败:', err)
  } finally {
    markBusy(record.id, false)
  }
}

const deleteRecord = async (record) => {
  markBusy(record.id, true)
  try {
    const res = await fetch(`${API_BASE_URL}/history/${record.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    records.value = records.value.filter((item) => item.id !== record.id)
  } catch (err) {
    console.error('删除保存对话失败:', err)
  } finally {
    markBusy(record.id, false)
  }
}

onMounted(loadSavedChats)
</script>

<template>
  <div class="min-h-[100dvh] bg-[#050505] relative overflow-hidden text-gray-200">
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-0 left-0 w-[50vw] h-[50vh] bg-gradient-to-br from-amber-500/10 via-purple-500/5 to-transparent blur-3xl animate-pulse-slow"></div>
      <div class="absolute bottom-0 right-0 w-[50vw] h-[50vh] bg-gradient-to-tl from-cyan-500/10 via-emerald-500/5 to-transparent blur-3xl animate-pulse-slower"></div>
    </div>

    <div class="relative z-10">
      <div class="bg-white/[0.02] backdrop-blur-xl border-b border-white/[0.05] px-4 py-4">
        <div class="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <button @click="router.push('/dashboard')" class="p-2 rounded-lg hover:bg-white/5 transition-all duration-300 group">
              <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
            </button>
            <div class="flex items-center gap-2">
              <Star class="w-6 h-6 text-amber-300" fill="currentColor" />
              <h1 class="text-xl font-bold text-white">保存的对话</h1>
            </div>
          </div>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索已保存..."
              class="bg-white/5 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-400/50 w-48 md:w-64 transition-all duration-300"
            />
          </div>
        </div>
      </div>

      <div class="p-4 md:p-6">
        <div class="max-w-6xl mx-auto">
          <div v-if="isLoading" class="flex items-center justify-center h-64">
            <Loader2 class="w-8 h-8 text-amber-300 animate-spin" />
          </div>
          <div v-else-if="filteredRecords.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
            <Star class="w-12 h-12 text-gray-600 mb-4" />
            <p class="text-gray-500">暂无保存的对话</p>
          </div>
          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="record in filteredRecords"
              :key="record.id"
              @click="openChatModal(record)"
              class="group relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-2xl p-5 pb-14 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-amber-400/30 hover:shadow-[0_0_20px_rgba(251,191,36,0.12)]"
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
              <div class="absolute right-4 bottom-4 flex items-center gap-2">
                <button
                  @click.stop="unsaveRecord(record)"
                  :disabled="busyRecordIds.has(record.id)"
                  class="w-9 h-9 rounded-full border border-amber-300/50 bg-amber-400/10 text-amber-300 shadow-[0_0_16px_rgba(251,191,36,0.22)] backdrop-blur flex items-center justify-center transition-all duration-300"
                  title="取消保存"
                >
                  <Star class="w-4 h-4" fill="currentColor" />
                </button>
                <button
                  @click.stop="deleteRecord(record)"
                  :disabled="busyRecordIds.has(record.id)"
                  class="w-9 h-9 rounded-full border border-white/10 bg-black/20 text-gray-500 backdrop-blur flex items-center justify-center hover:text-red-300 hover:border-red-400/40 hover:bg-red-500/10 transition-all duration-300"
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

    <Teleport to="body">
      <transition name="modal-fade">
        <div
          v-if="showChatModal && selectedChat"
          class="fixed inset-0 z-[120] flex items-center justify-center px-4 bg-black/75 backdrop-blur-sm"
          @click.self="closeChatModal"
        >
          <div class="w-full max-w-3xl max-h-[80vh] overflow-y-auto bg-gray-900 border border-cyan-500/30 rounded-2xl shadow-[0_0_40px_rgba(34,211,238,0.16)]">
            <div class="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-cyan-500/20 bg-gray-900/95 backdrop-blur px-5 py-4">
              <div class="min-w-0">
                <div class="flex items-center gap-2 mb-2">
                  <component :is="getCategoryIcon(selectedChat.category)" class="w-4 h-4" :class="getCategoryColor(selectedChat.category).split(' ')[0]" />
                  <span class="text-xs px-2 py-0.5 rounded-full border" :class="getCategoryColor(selectedChat.category)">{{ getCategoryLabel(selectedChat.category) }}</span>
                </div>
                <h2 class="text-lg font-semibold text-white truncate">{{ selectedChat.user_input || '保存的对话' }}</h2>
                <p class="text-xs text-gray-500 mt-1">{{ selectedChat.created_at }}</p>
              </div>
              <button
                @click="closeChatModal"
                class="w-10 h-10 rounded-xl border border-cyan-400/40 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20 hover:text-white hover:shadow-[0_0_18px_rgba(34,211,238,0.22)] transition-all duration-300 flex items-center justify-center flex-shrink-0"
                title="关闭"
              >
                <X class="w-5 h-5" />
              </button>
            </div>

            <div class="p-5 space-y-4">
              <div v-if="selectedChatMessages.length === 0" class="rounded-xl border border-white/10 bg-black/20 p-6 text-center text-sm text-gray-500">
                暂无可展示的对话历史
              </div>

              <div
                v-for="message in selectedChatMessages"
                :key="message.id"
                class="flex"
                :class="isUserMessage(message) ? 'justify-end' : 'justify-start'"
              >
                <div
                  class="max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap border"
                  :class="isUserMessage(message)
                    ? 'bg-cyan-500/20 border-cyan-400/30 text-cyan-50 rounded-tr-sm shadow-[0_0_18px_rgba(34,211,238,0.08)]'
                    : 'bg-black/35 border-white/10 text-gray-200 rounded-tl-sm'"
                >
                  <div class="mb-1 text-[10px] font-semibold uppercase tracking-wider" :class="isUserMessage(message) ? 'text-cyan-200' : 'text-emerald-300'">
                    {{ isUserMessage(message) ? 'User' : 'AI' }}
                  </div>
                  {{ message.content }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }
.animate-pulse-slower { animation: pulse-slow 8s ease-in-out infinite; animation-delay: -4s; }
@keyframes pulse-slow { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 1; } }
.line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.modal-fade-enter-active,
.modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; }
</style>
