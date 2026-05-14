<script setup>
/**
 * DataSourceModal.vue
 * 数据源切换弹窗组件
 *
 * 职责：按当前激活 Tab 过滤历史评估记录，供用户切换当前 Dashboard 展示的数据源。
 * 无有效评分的记录仍显示，但以灰显样式或"无评分"徽章区分。
 * 与 SetupModal（个人信息配置）彻底解耦。
 *
 * 对应需求：Requirements 9.1, 9.2, 9.5
 */
import { computed } from 'vue'
import { X, Database, Clock, Tag } from 'lucide-vue-next'
import { hasValidScores } from '@/utils/dataSourceUtils.js'
import { useUserStore } from '@/stores/userStore.js'

// ─── Props & Emits ────────────────────────────────────────────────────────────

const props = defineProps({
  /** 控制弹窗显示/隐藏 */
  visible: {
    type: Boolean,
    default: false
  },
  /** 历史评估记录数组，由父组件（Dashboard）传入 */
  historyRecords: {
    type: Array,
    default: () => []
  },
  /**
   * 当前激活的 Bento 面板 Tab，决定按哪种 category 过滤记录。
   * 取值：'resume' | 'interview' | 'career'
   * Requirements: 9.1, 9.2
   */
  activeTab: {
    type: String,
    default: 'resume'
  }
})

const emit = defineEmits(['close', 'select'])

// ─── Store ────────────────────────────────────────────────────────────────────

const userStore = useUserStore()

// ─── Computed ─────────────────────────────────────────────────────────────────

/**
 * 按 activeTab 过滤 historyRecords，映射规则：
 *   resume    → category === 'resume_diagnosis'
 *   interview → category.startsWith('interview')
 *   career    → category === 'career_planning'
 *
 * 所有匹配 Tab 的记录均显示（含无有效评分的记录），
 * 无有效评分的记录在模板中以灰显样式或"无评分"徽章区分。
 *
 * Requirements: 9.1, 9.2, 9.5
 */
const filteredByTab = computed(() => {
  if (!Array.isArray(props.historyRecords)) return []

  return props.historyRecords.filter(record => {
    const category = record?.category ?? ''
    if (props.activeTab === 'resume') {
      return category === 'resume_diagnosis'
    }
    if (props.activeTab === 'interview') {
      return category.startsWith('interview')
    }
    if (props.activeTab === 'career') {
      return category === 'career_planning'
    }
    // 未知 tab 值时不显示任何记录
    return false
  })
})

// ─── Category Helpers ─────────────────────────────────────────────────────────

/**
 * 将后端 category 枚举值映射为中文标签
 * @param {string} category
 * @returns {string}
 */
function getCategoryLabel(category) {
  const labelMap = {
    resume_diagnosis: '简历诊断',
    interview_beginner: '温和面试',
    interview_standard: '标准面试',
    interview_p8: 'P8压力面',
    career_planning: '职业规划',
    general_chat: '职业助手'
  }
  if (category in labelMap) return labelMap[category]
  if (category?.startsWith('interview')) return '面试评估'
  return category || '未知类型'
}

/**
 * 根据 category 返回对应的 Tailwind 颜色类（与 Dashboard 风格一致）
 * @param {string} category
 * @returns {string}
 */
function getCategoryColorClass(category) {
  if (category === 'resume_diagnosis') return 'text-purple-400 border-purple-500/30 bg-purple-500/10'
  if (category === 'interview_beginner') return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
  if (category === 'interview_standard') return 'text-blue-400 border-blue-500/30 bg-blue-500/10'
  if (category === 'interview_p8') return 'text-pink-400 border-pink-500/30 bg-pink-500/10'
  if (category?.startsWith('interview')) return 'text-pink-400 border-pink-500/30 bg-pink-500/10'
  if (category === 'career_planning') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10'
  return 'text-gray-400 border-gray-500/30 bg-gray-500/10'
}

/**
 * 格式化时间戳为可读字符串
 * @param {string} timestamp
 * @returns {string}
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '未知时间'
  try {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timestamp
  }
}

/**
 * 截取 user_input 作为摘要，最多显示 60 个字符
 * @param {string} userInput
 * @returns {string}
 */
function getSummary(userInput) {
  if (!userInput) return '暂无摘要'
  const text = String(userInput).trim()
  return text.length > 60 ? text.slice(0, 60) + '…' : text
}

// ─── Actions ──────────────────────────────────────────────────────────────────

/**
 * 用户选择某条历史记录作为数据源时调用。
 * 解析 scores → 更新 userStore.radarData → 更新 activeDataSourceId → emit('select', record)
 *
 * 前置条件：record 已通过 hasValidScores 筛选，scores 字段有效
 * 后置条件：userStore.radarData 反映选中记录的评分；emit 通知父组件关闭弹窗
 *
 * @param {Object} record - 含有效评分的历史记录对象
 */
function selectDataSource(record) {
  let scores = record.scores

  // scores 可能是 JSON 字符串，需安全解析
  if (typeof scores === 'string') {
    try {
      scores = JSON.parse(scores)
    } catch {
      // 解析失败时静默退出，不更新 Store
      return
    }
  }

  if (scores && typeof scores === 'object' && Object.keys(scores).length > 0) {
    userStore.updateRadarData(scores)
    userStore.activeDataSourceId = record.id
  }

  emit('select', record)
}

/**
 * 关闭弹窗
 */
function closeModal() {
  emit('close')
}
</script>

<template>
  <!-- 遮罩层：点击背景关闭弹窗（Requirements 13.3） -->
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[110] flex items-center justify-center px-4 bg-black/70 backdrop-blur-sm"
        @click.self="closeModal"
        role="dialog"
        aria-modal="true"
        aria-label="数据源选择"
      >
        <!-- 弹窗主体：赛博朋克深色毛玻璃风格（Requirements 11.3, 12.3） -->
        <div class="relative w-full max-w-lg rounded-2xl backdrop-blur-xl bg-white/[0.02] border border-cyan-500/20 shadow-[0_0_40px_rgba(6,182,212,0.12)] overflow-hidden">

          <!-- 顶部装饰光条 -->
          <div class="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"></div>

          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                <Database class="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-200">数据面板设置</h3>
                <p class="text-xs text-gray-500 mt-0.5">选择雷达图展示的评估数据源</p>
              </div>
            </div>

            <!-- 关闭按钮（Requirements 5.2） -->
            <button
              @click="closeModal"
              class="w-7 h-7 flex items-center justify-center rounded-lg border border-white/10 bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-all duration-200"
              aria-label="关闭数据源选择"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- 弹窗内容区 -->
          <div class="px-5 py-4 max-h-[60vh] overflow-y-auto">

            <!-- Tab 过滤后的记录列表（Requirements 9.1, 9.2, 9.5） -->
            <div v-if="filteredByTab.length > 0" class="space-y-2">
              <div
                v-for="record in filteredByTab"
                :key="record.id"
                class="group relative rounded-xl border transition-all duration-200 cursor-pointer p-3"
                :class="hasValidScores(record)
                  ? 'border-white/[0.06] bg-white/[0.02] hover:border-cyan-500/30 hover:bg-cyan-500/[0.04]'
                  : 'border-white/[0.03] bg-white/[0.01] opacity-50 hover:opacity-70'"
                @click="selectDataSource(record)"
              >
                <!-- 记录头部：类别标签 + 时间 + 无评分徽章 -->
                <div class="flex items-center justify-between gap-2 mb-2">
                  <div class="flex items-center gap-1.5 min-w-0">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border shrink-0"
                      :class="getCategoryColorClass(record.category)"
                    >
                      <Tag class="w-3 h-3" />
                      {{ getCategoryLabel(record.category) }}
                    </span>
                    <!-- 无有效评分时显示"无评分"徽章（Requirements 9.5） -->
                    <span
                      v-if="!hasValidScores(record)"
                      class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] border border-gray-600/40 bg-gray-700/30 text-gray-500 shrink-0"
                    >
                      无评分
                    </span>
                  </div>
                  <span class="flex items-center gap-1 text-xs text-gray-500 shrink-0">
                    <Clock class="w-3 h-3" />
                    {{ formatTimestamp(record.created_at) }}
                  </span>
                </div>

                <!-- 记录摘要 -->
                <p class="text-xs text-gray-400 leading-relaxed line-clamp-2">
                  {{ getSummary(record.user_input) }}
                </p>

                <!-- 当前激活数据源标识 -->
                <div
                  v-if="userStore.activeDataSourceId === record.id"
                  class="absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]"
                ></div>
              </div>
            </div>

            <!-- 空状态：当前 Tab 无匹配记录 -->
            <div v-else class="flex flex-col items-center justify-center py-10 text-center">
              <div class="w-12 h-12 rounded-xl bg-gray-500/10 border border-gray-500/20 flex items-center justify-center mb-3">
                <Database class="w-6 h-6 text-gray-500" />
              </div>
              <p class="text-sm text-gray-400 font-medium">暂无可用数据源</p>
              <p class="text-xs text-gray-500 mt-1 leading-relaxed">
                完成一次简历诊断或面试评估后，<br>评分数据将在此处显示
              </p>
            </div>

          </div>

          <!-- 弹窗底部 -->
          <div class="px-5 py-3 border-t border-white/[0.06] flex items-center justify-between">
            <span class="text-xs text-gray-500">
              共 {{ filteredByTab.length }} 条记录
            </span>
            <button
              @click="closeModal"
              class="px-3 py-1.5 rounded-lg text-xs text-gray-400 border border-white/10 bg-white/5 hover:text-gray-300 hover:bg-white/10 transition-all duration-200"
            >
              关闭
            </button>
          </div>

          <!-- 底部装饰光条 -->
          <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent"></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 弹窗淡入淡出动画 */
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

/* 记录列表滚动条美化 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 2px;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(34, 211, 238, 0.2);
}

/* 文本行数限制 */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
