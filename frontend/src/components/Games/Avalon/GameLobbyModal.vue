<script setup>
/**
 * GameLobbyModal — 职场情商对抗模拟器大厅
 * 基于 BaseModal 扩展，使用 Mock 数据展示 UI 骨架。
 * 视觉策略：大框架继承主站紫青调性，内部标题/按钮/特效采用
 * 警示霓虹红橙（Neon Red/Orange）+ 矩阵毒液绿（Matrix Green）
 * 拉满"高压对抗"紧张张力。
 */
import { ref, computed } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import { Cpu, Users, Plus, ChevronRight, Zap, Shield, Swords } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const handleClose = () => emit('update:modelValue', false)

// ── Mock 数据：房间列表 ──────────────────────────────────────────
const mockRooms = ref([
  { id: 1024, status: '等待中', current: 3, max: 5, difficulty: 'normal', host: 'Agent_Merlin' },
  { id: 2077, status: '等待中', current: 2, max: 6, difficulty: 'hard',   host: 'Agent_Percival' },
  { id: 3090, status: '游戏中', current: 5, max: 5, difficulty: 'normal', host: 'Agent_Mordred' },
  { id: 4096, status: '等待中', current: 1, max: 5, difficulty: 'easy',   host: 'Agent_Oberon' },
])

const difficultyConfig = {
  easy:   { label: '训练模式', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' },
  normal: { label: '标准对抗', color: 'text-orange-400',  bg: 'bg-orange-500/10 border-orange-500/30' },
  hard:   { label: '高压博弈', color: 'text-red-400',     bg: 'bg-red-500/10 border-red-500/30' },
}

const selectedRoom = ref(null)

const selectRoom = (room) => {
  if (room.status === '游戏中') return
  selectedRoom.value = room.id === selectedRoom.value ? null : room.id
}

// ── 创建房间面板 ─────────────────────────────────────────────────
const aiCount = ref(4)
const totalPlayers = ref(5)

const humanCount = computed(() => totalPlayers.value - aiCount.value)

const handleAiCountChange = (e) => {
  const val = Number(e.target.value)
  // 至少保留 1 个人类玩家
  aiCount.value = Math.min(val, totalPlayers.value - 1)
}

const handleLaunch = () => {
  // TODO: 接入后端 /api/game/avalon/rooms POST
  console.log('[Avalon] 启动模拟，AI 补位数量:', aiCount.value)
}

const handleJoinRoom = () => {
  if (!selectedRoom.value) return
  // TODO: 接入后端 /api/game/avalon/rooms/{id}/join
  console.log('[Avalon] 加入房间:', selectedRoom.value)
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    max-width="max-w-4xl"
    :close-on-overlay="true"
    @close="handleClose"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="p-6 md:p-8">

      <!-- ── 顶部标题区 ─────────────────────────────────────── -->
      <div class="mb-6 flex items-start gap-4">
        <!-- 图标 -->
        <div class="flex-shrink-0 w-12 h-12 rounded-xl border border-orange-500/40 bg-orange-500/10 flex items-center justify-center shadow-[0_0_20px_rgba(249,115,22,0.3)] avalon-icon-pulse">
          <Cpu class="w-6 h-6 text-orange-400" />
        </div>
        <!-- 文字 -->
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-mono text-orange-400/70 tracking-widest uppercase">Project Avalon · Beta</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">LIVE</span>
          </div>
          <h2 class="text-xl md:text-2xl font-black tracking-tight text-white avalon-title-glow">
            无领导小组对抗训练
          </h2>
          <p class="text-sm text-gray-400 mt-0.5">
            与多个 AI 角色进行高压博弈推理，训练职场情商与决策力
          </p>
        </div>
      </div>

      <!-- ── 主体双栏布局 ────────────────────────────────────── -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">

        <!-- 左栏：房间列表 -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <Shield class="w-4 h-4 text-cyan-400" />
              当前房间
            </h3>
            <span class="text-xs text-gray-500 font-mono">{{ mockRooms.filter(r => r.status === '等待中').length }} 个等待中</span>
          </div>

          <div class="space-y-2">
            <div
              v-for="room in mockRooms"
              :key="room.id"
              class="room-card group relative rounded-xl border p-3.5 transition-all duration-200 cursor-pointer"
              :class="[
                room.status === '游戏中'
                  ? 'border-white/5 bg-white/[0.02] opacity-50 cursor-not-allowed'
                  : selectedRoom === room.id
                    ? 'border-orange-500/60 bg-orange-500/[0.07] shadow-[0_0_20px_rgba(249,115,22,0.15)]'
                    : 'border-white/8 bg-white/[0.03] hover:border-orange-500/30 hover:bg-orange-500/[0.04] hover:shadow-[0_0_14px_rgba(249,115,22,0.1)]'
              ]"
              @click="selectRoom(room)"
            >
              <!-- 选中指示线 -->
              <div
                v-if="selectedRoom === room.id"
                class="absolute left-0 top-3 bottom-3 w-0.5 rounded-full bg-gradient-to-b from-orange-400 to-red-500"
              />

              <div class="flex items-center justify-between">
                <!-- 左侧信息 -->
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold font-mono"
                    :class="room.status === '游戏中' ? 'bg-gray-500/20 text-gray-400' : 'bg-orange-500/15 text-orange-300'">
                    #{{ room.id }}
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium text-gray-200">房间 {{ room.id }}</span>
                      <span
                        class="px-1.5 py-0.5 rounded text-[10px] border"
                        :class="difficultyConfig[room.difficulty].bg + ' ' + difficultyConfig[room.difficulty].color"
                      >
                        {{ difficultyConfig[room.difficulty].label }}
                      </span>
                    </div>
                    <div class="flex items-center gap-1.5 mt-0.5">
                      <Users class="w-3 h-3 text-gray-500" />
                      <span class="text-xs text-gray-500">{{ room.current }}/{{ room.max }} 人</span>
                      <span class="text-gray-600">·</span>
                      <span class="text-xs text-gray-500 truncate max-w-[80px]">{{ room.host }}</span>
                    </div>
                  </div>
                </div>

                <!-- 右侧状态 -->
                <div class="flex items-center gap-2">
                  <div class="flex items-center gap-1">
                    <div
                      class="w-1.5 h-1.5 rounded-full"
                      :class="room.status === '游戏中' ? 'bg-red-500 animate-pulse' : 'bg-emerald-400 animate-pulse'"
                    />
                    <span class="text-xs" :class="room.status === '游戏中' ? 'text-red-400' : 'text-emerald-400'">
                      {{ room.status }}
                    </span>
                  </div>
                  <ChevronRight
                    v-if="room.status !== '游戏中'"
                    class="w-4 h-4 text-gray-600 group-hover:text-orange-400 transition-colors duration-200"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 加入按钮 -->
          <button
            class="mt-3 w-full py-2.5 rounded-xl border text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2"
            :class="selectedRoom
              ? 'border-orange-500/50 bg-orange-500/15 text-orange-300 hover:bg-orange-500/25 hover:shadow-[0_0_20px_rgba(249,115,22,0.2)]'
              : 'border-white/5 bg-white/[0.02] text-gray-600 cursor-not-allowed'"
            :disabled="!selectedRoom"
            @click="handleJoinRoom"
          >
            <Swords class="w-4 h-4" />
            {{ selectedRoom ? `加入房间 #${selectedRoom}` : '请先选择一个房间' }}
          </button>
        </div>

        <!-- 右栏：创建房间 -->
        <div>
          <div class="flex items-center gap-2 mb-3">
            <Plus class="w-4 h-4 text-green-400" />
            <h3 class="text-sm font-semibold text-gray-300">创建新房间</h3>
          </div>

          <div class="rounded-xl border border-white/8 bg-white/[0.025] p-4 space-y-5">

            <!-- AI 补位数量滑动条 -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-xs text-gray-400">AI 补位数量</label>
                <div class="flex items-center gap-1.5">
                  <span class="text-lg font-black font-mono text-green-400 avalon-count-glow">{{ aiCount }}</span>
                  <span class="text-xs text-gray-500">/ {{ totalPlayers - 1 }} 最大</span>
                </div>
              </div>

              <input
                type="range"
                :min="1"
                :max="totalPlayers - 1"
                :value="aiCount"
                class="avalon-slider w-full"
                @input="handleAiCountChange"
              />

              <!-- 玩家构成可视化 -->
              <div class="mt-3 flex items-center gap-1.5">
                <div
                  v-for="i in totalPlayers"
                  :key="i"
                  class="flex-1 h-2 rounded-full transition-all duration-300"
                  :class="i <= humanCount ? 'bg-cyan-500/60' : 'bg-green-500/70 shadow-[0_0_6px_rgba(74,222,128,0.5)]'"
                />
              </div>
              <div class="flex justify-between mt-1.5">
                <span class="text-[10px] text-cyan-400">你 ({{ humanCount }} 人类)</span>
                <span class="text-[10px] text-green-400">{{ aiCount }} AI 对手</span>
              </div>
            </div>

            <!-- 总人数选择 -->
            <div>
              <label class="text-xs text-gray-400 block mb-2">房间总人数</label>
              <div class="flex gap-2">
                <button
                  v-for="n in [5, 6, 7]"
                  :key="n"
                  class="flex-1 py-1.5 rounded-lg border text-sm font-mono font-bold transition-all duration-200"
                  :class="totalPlayers === n
                    ? 'border-orange-500/50 bg-orange-500/15 text-orange-300 shadow-[0_0_12px_rgba(249,115,22,0.2)]'
                    : 'border-white/8 bg-white/[0.03] text-gray-500 hover:border-white/15 hover:text-gray-300'"
                  @click="totalPlayers = n; aiCount = Math.min(aiCount, n - 1)"
                >
                  {{ n }}P
                </button>
              </div>
            </div>

            <!-- 系统提示 -->
            <div class="rounded-lg border border-green-500/20 bg-green-500/[0.04] p-3">
              <div class="flex items-start gap-2">
                <Zap class="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                <p class="text-[11px] text-green-300/80 leading-relaxed">
                  AI 对手将扮演不同职场角色，具备独立推理能力与隐藏目标。
                  你的任务：在高压博弈中识别盟友，完成团队使命。
                </p>
              </div>
            </div>

            <!-- 启动按钮 -->
            <button
              class="avalon-launch-btn w-full py-3.5 rounded-xl font-bold text-sm tracking-wider transition-all duration-300 flex items-center justify-center gap-2"
              @click="handleLaunch"
            >
              <Cpu class="w-4 h-4" />
              启动模拟
            </button>
          </div>
        </div>
      </div>

      <!-- ── 底部免责声明 ─────────────────────────────────────── -->
      <p class="mt-5 text-center text-[10px] text-gray-600 font-mono">
        PROJECT AVALON · 职场情商训练系统 · 所有 AI 角色均为虚构，不代表真实人物
      </p>
    </div>
  </BaseModal>
</template>

<style scoped>
/* 标题辉光 */
.avalon-title-glow {
  text-shadow: 0 0 20px rgba(249, 115, 22, 0.3);
}

/* 图标脉冲 */
.avalon-icon-pulse {
  animation: avalon-icon-breathe 2.5s ease-in-out infinite;
}
@keyframes avalon-icon-breathe {
  0%, 100% { box-shadow: 0 0 20px rgba(249, 115, 22, 0.3); }
  50%       { box-shadow: 0 0 35px rgba(249, 115, 22, 0.55), 0 0 60px rgba(249, 115, 22, 0.15); }
}

/* 数字辉光 */
.avalon-count-glow {
  text-shadow: 0 0 12px rgba(74, 222, 128, 0.6);
}

/* 自定义滑动条 */
.avalon-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 9999px;
  background: linear-gradient(
    to right,
    rgba(74, 222, 128, 0.7) 0%,
    rgba(74, 222, 128, 0.7) calc(var(--val, 80%) ),
    rgba(255, 255, 255, 0.08) calc(var(--val, 80%)),
    rgba(255, 255, 255, 0.08) 100%
  );
  outline: none;
  cursor: pointer;
}
.avalon-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #4ade80;
  border: 2px solid rgba(0, 0, 0, 0.4);
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.7);
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.avalon-slider::-webkit-slider-thumb:hover {
  box-shadow: 0 0 18px rgba(74, 222, 128, 0.9);
}
.avalon-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #4ade80;
  border: 2px solid rgba(0, 0, 0, 0.4);
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.7);
  cursor: pointer;
}

/* 启动按钮 */
.avalon-launch-btn {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(249, 115, 22, 0.25) 100%);
  border: 1px solid rgba(249, 115, 22, 0.5);
  color: #fb923c;
  text-shadow: 0 0 10px rgba(249, 115, 22, 0.5);
  box-shadow: 0 0 20px rgba(249, 115, 22, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.avalon-launch-btn:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.3) 0%, rgba(249, 115, 22, 0.35) 100%);
  box-shadow: 0 0 35px rgba(249, 115, 22, 0.35), 0 0 60px rgba(249, 115, 22, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}
.avalon-launch-btn:active {
  transform: translateY(0);
}
</style>
