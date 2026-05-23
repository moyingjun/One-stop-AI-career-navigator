<script setup>
/**
 * DataSourceModal.vue — 数据面板设置弹窗
 *
 * 接受由父组件（Dashboard）已按 activeTab 过滤的 records 数组，
 * 不再自行从 historyRecords 过滤，避免数据源错位。
 *
 * Props 契约（v2，2026-05 重构）：
 *   - records:    Array — 已过滤好的最近 10 条记录
 *   - activeType: 'resume' | 'interview' | 'career'
 *   - visible:    Boolean
 *
 * 选择记录后只 emit('select', record)，父组件统一处理 radar 切换 / 浮窗打开。
 */
import { computed } from 'vue'
import { X, Database, Clock, Tag } from 'lucide-vue-next'
import { useUserStore } from '@/stores/userStore.js'
import { formatRecordTime } from '@/utils/dateFormat.js'
import { hasNonZeroScores } from '@/utils/radarMapping.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  records: { type: Array, default: () => [] },
  activeType: { type: String, default: 'resume' }
})

const emit = defineEmits(['close', 'select'])

const userStore = useUserStore()

// ── 当前 type 的标签文案 ─────────────────────────────────
const typeLabel = computed(() => {
  if (props.activeType === 'resume') return '简历诊断'
  if (props.activeType === 'interview') return '模拟面试'
  if (props.activeType === 'career') return '职业规划'
  return '历史记录'
})

const typeColorClass = computed(() => {
  if (props.activeType === 'resume') return 'text-purple-400 border-purple-500/30 bg-purple-500/10'
  if (props.activeType === 'interview') return 'text-pink-400 border-pink-500/30 bg-pink-500/10'
  if (props.activeType === 'career') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10'
  return 'text-gray-400 border-gray-500/30 bg-gray-500/10'
})

// ── 摘要文本提取（按 type 优先字段不同）────────────────────
function getSummary(record) {
  if (!record) return '暂无摘要'
  const text = String(record.user_input || record.ai_result || '').trim()
  if (!text) return '暂无摘要'
  return text.length > 60 ? text.slice(0, 60) + '…' : text
}

function selectRecord(record) {
  if (record && record.id != null) {
    userStore.activeDataSourceId = record.id
  }
  emit('select', record)
}

function closeModal() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[110] flex items-center justify-center px-4 bg-black/70 backdrop-blur-sm"
        @click.self="closeModal"
        role="dialog"
        aria-modal="true"
        aria-label="数据面板设置"
      >
        <div class="relative w-full max-w-lg rounded-2xl backdrop-blur-xl bg-white/[0.02] border border-cyan-500/20 shadow-[0_0_40px_rgba(6,182,212,0.12)] overflow-hidden">
          <div class="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"></div>

          <!-- 头部 -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                <Database class="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-200">数据面板设置</h3>
                <p class="text-xs text-gray-500 mt-0.5">{{ typeLabel }} · 最近 {{ records.length }} 条记录</p>
              </div>
            </div>

            <button
              @click="closeModal"
              class="w-7 h-7 flex items-center justify-center rounded-lg border border-white/10 bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-all duration-200"
              aria-label="关闭"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- 内容区 -->
          <div class="px-5 py-4 max-h-[60vh] overflow-y-auto">
            <div v-if="records.length > 0" class="space-y-2">
              <div
                v-for="record in records"
                :key="record.id"
                class="group relative rounded-xl border transition-all duration-200 cursor-pointer p-3 border-white/[0.06] bg-white/[0.02] hover:border-cyan-500/30 hover:bg-cyan-500/[0.04]"
                @click="selectRecord(record)"
              >
                <div class="flex items-center justify-between gap-2 mb-2">
                  <div class="flex items-center gap-1.5 min-w-0">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border shrink-0"
                      :class="typeColorClass"
                    >
                      <Tag class="w-3 h-3" />
                      {{ typeLabel }}
                    </span>
                    <!-- 简历/面试 才需要"无评分"徽章；career 不需要 scores -->
                    <span
                      v-if="(activeType === 'resume' || activeType === 'interview') && !hasNonZeroScores(record.scores)"
                      class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] border border-gray-600/40 bg-gray-700/30 text-gray-500 shrink-0"
                    >
                      无评分
                    </span>
                  </div>
                  <span class="flex items-center gap-1 text-xs text-gray-500 shrink-0">
                    <Clock class="w-3 h-3" />
                    {{ formatRecordTime(record) }}
                  </span>
                </div>

                <p class="text-xs text-gray-400 leading-relaxed line-clamp-2">
                  {{ getSummary(record) }}
                </p>

                <div
                  v-if="userStore.activeDataSourceId === record.id"
                  class="absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]"
                ></div>
              </div>
            </div>

            <div v-else class="flex flex-col items-center justify-center py-10 text-center">
              <div class="w-12 h-12 rounded-xl bg-gray-500/10 border border-gray-500/20 flex items-center justify-center mb-3">
                <Database class="w-6 h-6 text-gray-500" />
              </div>
              <p class="text-sm text-gray-400 font-medium">暂无可用数据源</p>
              <p class="text-xs text-gray-500 mt-1 leading-relaxed">
                <span v-if="activeType === 'resume'">完成一次简历诊断后<br>评分数据将在此处显示</span>
                <span v-else-if="activeType === 'interview'">完成一次模拟面试评估后<br>评分数据将在此处显示</span>
                <span v-else-if="activeType === 'career'">在职业规划页生成一次<br>职业蓝图后将在此处显示</span>
                <span v-else>暂无可用记录</span>
              </p>
            </div>
          </div>

          <div class="px-5 py-3 border-t border-white/[0.06] flex items-center justify-between">
            <span class="text-xs text-gray-500">
              共 {{ records.length }} 条记录
            </span>
            <button
              @click="closeModal"
              class="px-3 py-1.5 rounded-lg text-xs text-gray-400 border border-white/10 bg-white/5 hover:text-gray-300 hover:bg-white/10 transition-all duration-200"
            >
              关闭
            </button>
          </div>

          <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent"></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active .relative,
.modal-fade-leave-active .relative {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.modal-fade-enter-from .relative,
.modal-fade-leave-to .relative {
  transform: translateY(-8px);
  opacity: 0;
}

.overflow-y-auto::-webkit-scrollbar { width: 4px; }
.overflow-y-auto::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); border-radius: 2px; }
.overflow-y-auto::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 2px; }
.overflow-y-auto::-webkit-scrollbar-thumb:hover { background: rgba(34, 211, 238, 0.2); }

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
