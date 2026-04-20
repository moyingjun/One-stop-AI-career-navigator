<script setup>
import { ref } from 'vue'
import { llmService } from '@/services/llm_service.js'
import { useRouter } from 'vue-router'

const router = useRouter()

// 响应式数据
const userId = ref('user_001') // 默认用户ID
const selectedFile = ref(null) // 存储选中的文件
const isUploading = ref(false) // 上传状态
const chatMessages = ref([]) // 聊天记录
const dropZoneActive = ref(false) // 拖拽区域激活状态
const userInput = ref('') // 用户输入文本
const activeWorkspace = ref('机构') // 当前选中的工作区

// 处理文件选择
const handleFileChange = (event) => {
  selectedFile.value = event.target.files[0]
}

// 处理拖拽开始
const handleDragStart = (event) => {
  event.preventDefault()
}

// 处理拖拽进入
const handleDragEnter = (event) => {
  event.preventDefault()
  dropZoneActive.value = true
}

// 处理拖拽离开
const handleDragLeave = (event) => {
  event.preventDefault()
  dropZoneActive.value = false
}

// 处理拖拽释放
const handleDrop = (event) => {
  event.preventDefault()
  dropZoneActive.value = false
  selectedFile.value = event.dataTransfer.files[0]
}

// 处理发送
const handleSend = async () => {
  if (!selectedFile.value) {
    alert('请先选择一个文件')
    return
  }

  isUploading.value = true

  try {
    const result = await llmService.diagnoseResume(selectedFile.value, userId.value)
    chatMessages.value.push({
      type: 'ai',
      content: JSON.stringify(result, null, 2)
    })
    userInput.value = ''
    selectedFile.value = null
  } catch (error) {
    alert('网络错误，请稍后重试：' + error.message)
  } finally {
    isUploading.value = false
  }
}

// 快捷操作
const quickActions = [
  '简历诊断',
  '模拟面试',
  '职业规划',
  '技能评估',
  '求职建议',
  '简历优化'
]

// 工作区选项
const workspaces = [
  '机构',
  '团队',
  '个人',
  '营销',
  '线索'
]

// 菜单项
const menuItems = [
  {
    category: '主要功能',
    items: [
      { icon: '📋', label: '功能模板' },
      { icon: '💾', label: '保存的对话' },
      { icon: '📁', label: '文件管理' },
      { icon: '🕒', label: '历史记录' },
      { icon: '🔌', label: '插件集成' },
      { icon: '⚙️', label: '系统设置' }
    ]
  },
  {
    category: '我的项目',
    items: [
      { icon: '💼', label: '商业分析' },
      { icon: '👤', label: '个人规划' },
      { icon: '📊', label: '项目进度' }
    ]
  }
]
</script>

<template>
  <div class="app-container relative min-h-screen text-gray-300 overflow-hidden">
    <!-- 背景光影效果 -->
    <div class="absolute top-0 left-0 w-full h-full bg-[#050505] z-0">
      <div class="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-1/2 bg-gradient-to-b from-purple-500/10 via-pink-500/5 to-transparent blur-3xl"></div>
      <div class="absolute bottom-0 left-0 w-1/2 h-1/2 bg-gradient-to-t from-cyan-500/10 via-purple-500/5 to-transparent blur-3xl"></div>
    </div>

    <div class="relative z-10 flex h-screen">
      <!-- 左侧侧边栏 -->
      <div class="left-sidebar w-64 bg-[#0a0a0a] border-r border-gray-800 fixed h-full overflow-y-auto">
        <div class="logo p-4 border-b border-gray-800 pl-4 cursor-pointer" @click="router.push('/')">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-purple-500/20">
              <span class="text-white text-sm font-bold">AI</span>
            </div>
            <div class="flex flex-col">
              <h1 class="text-xl font-bold text-white leading-tight">AI 职业导航</h1>
              <p class="text-xs text-gray-500 leading-tight mt-0.5">智能助手</p>
            </div>
          </div>
        </div>

        <div class="new-chat p-4">
          <button class="w-full bg-gray-800 hover:bg-gray-700 hover:shadow-lg hover:shadow-purple-500/20 text-white py-2 px-4 rounded-full transition-all duration-300 flex items-center gap-2 border border-gray-700 hover:border-purple-500/50 hover:-translate-y-0.5">
            <span class="text-lg">+</span>
            <span>新建对话</span>
          </button>
        </div>

        <div class="navigation p-4">
          <div v-for="menu in menuItems" :key="menu.category" class="mb-6">
            <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">
              {{ menu.category }}
            </h2>
            <div class="space-y-1">
              <div
                v-for="(item, index) in menu.items"
                :key="index"
                class="menu-item flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800 transition-all duration-300 cursor-pointer hover:translate-x-2 hover:text-white"
                :class="{ 'bg-gray-800 text-white': item.label === '历史记录' }"
              >
                <span class="text-lg">{{ item.icon }}</span>
                <span class="text-sm">{{ item.label }}</span>
              </div>
            </div>
          </div>

          <div v-if="chatMessages.length > 0" class="history mt-8">
            <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">
              最近
            </h2>-->
            <div class="space-y-1">
              <div
                v-for="(message, index) in chatMessages"
                :key="index"
                class="history-item p-2 rounded-lg hover:bg-gray-800 transition-all duration-300 cursor-pointer hover:translate-x-2"
              >
                <p class="text-sm truncate text-left">AI分析 - {{ new Date().toLocaleDateString() }}</p>
              </div>
            </div>
          </div>

          <div class="add-topic mt-8">
            <button class="w-full flex items-center gap-2 text-gray-500 hover:text-white transition-colors duration-300 hover:translate-x-2">
              <span class="text-lg">+</span>
              <span class="text-sm">添加主题</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧主工作区 -->
      <div class="right-workspace ml-64 flex-1 flex flex-col">
        <div class="top-bar p-4 border-b border-gray-800 flex items-center justify-between animate-[fadeIn_0.3s_ease-out]">
          <div class="search-container flex items-center gap-2">
            <div class="relative">
              <input
                type="text"
                placeholder="搜索..."
                class="bg-gray-800 border border-gray-700 rounded-lg py-2 px-4 pl-10 text-sm w-64 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
              />
              <span class="absolute left-3 top-2.5 text-gray-500">🔍</span>
            </div>
          </div>
          <button class="bg-gray-800 border border-gray-700 rounded-lg py-2 px-4 text-sm hover:bg-gray-700 hover:border-purple-500/50 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/20">
            邀请
          </button>
        </div>

        <div class="main-content flex-1 p-6 overflow-y-auto">
          <div class="welcome-section mb-8 text-left animate-[fadeInUp_0.5s_ease-out]">
            <h1 class="text-3xl font-bold text-gray-200 mb-2">你好，Moyingjun</h1>
            <p class="text-2xl text-gray-400">今天想探索些什么？</p>
          </div>

          <div class="workspaces mb-8 text-left animate-[fadeInUp_0.5s_ease-out_0.1s_both]">
            <h2 class="text-sm text-gray-500 uppercase mb-3 font-semibold pl-1">工作区</h2>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="(workspace, index) in workspaces"
                :key="workspace"
                class="px-4 py-2 rounded-full text-sm transition-all duration-300"
                :class="activeWorkspace === workspace
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50 hover:-translate-y-0.5'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700 hover:-translate-y-0.5'"
                @click="activeWorkspace = workspace"
              >
                {{ workspace }}
              </button>
            </div>
          </div>

          <div class="templates-section mb-12 animate-[fadeInUp_0.5s_ease-out_0.2s_both]">
            <div class="template-container relative border border-gray-800 rounded-xl overflow-hidden">
              <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-pink-500 to-cyan-500"></div>

              <div class="p-6 bg-[#0a0a0a]/80 backdrop-blur-md">
                <div class="flex items-center justify-between mb-4">
                  <h2 class="text-lg font-semibold text-gray-200 text-left">核心功能</h2>
                  <div class="flex items-center gap-2">
                    <button class="text-gray-400 hover:text-white hover:scale-110 transition-all duration-300">
                      +
                    </button>
                    <button class="text-gray-400 hover:text-white hover:scale-110 transition-all duration-300">
                      ...
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-4">
                  <div class="card bg-gray-900/50 backdrop-blur-sm p-5 rounded-lg border border-gray-800 hover:border-purple-500/50 transition-all duration-300 cursor-pointer group text-left flex flex-col items-start"
                       style="box-shadow: 0 0 0 rgba(139, 92, 246, 0);"
                       onmouseenter="this.style.boxShadow='0 0 30px rgba(139, 92, 246, 0.25)'; this.style.transform='translateY(-8px)';"
                       onmouseleave="this.style.boxShadow='0 0 0 rgba(139, 92, 246, 0)'; this.style.transform='translateY(0)';">
                    <div class="card-icon text-4xl mb-4 group-hover:scale-110 transition-transform duration-300">📄</div>
                    <h3 class="text-base font-semibold mb-2 text-left">简历诊断</h3>
                    <p class="text-xs text-gray-500 text-left leading-relaxed">分析简历优缺点，提供优化建议</p>
                  </div>

                  <div class="card bg-gray-900/50 backdrop-blur-sm p-5 rounded-lg border border-gray-800 hover:border-pink-500/50 transition-all duration-300 cursor-pointer group text-left flex flex-col items-start"
                       style="box-shadow: 0 0 0 rgba(236, 72, 153, 0);"
                       onmouseenter="this.style.boxShadow='0 0 30px rgba(236, 72, 153, 0.25)'; this.style.transform='translateY(-8px)';"
                       onmouseleave="this.style.boxShadow='0 0 0 rgba(236, 72, 153, 0)'; this.style.transform='translateY(0)';">
                    <div class="card-icon text-4xl mb-4 group-hover:scale-110 transition-transform duration-300">🤖</div>
                    <h3 class="text-base font-semibold mb-2 text-left">模拟面试</h3>
                    <p class="text-xs text-gray-500 text-left leading-relaxed">AI 模拟面试，提供反馈和建议</p>
                  </div>

                  <div class="card bg-gray-900/50 backdrop-blur-sm p-5 rounded-lg border border-gray-800 hover:border-cyan-500/50 transition-all duration-300 cursor-pointer group text-left flex flex-col items-start"
                       style="box-shadow: 0 0 0 rgba(34, 211, 238, 0);"
                       onmouseenter="this.style.boxShadow='0 0 30px rgba(34, 211, 238, 0.25)'; this.style.transform='translateY(-8px)';"
                       onmouseleave="this.style.boxShadow='0 0 0 rgba(34, 211, 238, 0)'; this.style.transform='translateY(0)';">
                    <div class="card-icon text-4xl mb-4 group-hover:scale-110 transition-transform duration-300">🎯</div>
                    <h3 class="text-base font-semibold mb-2 text-left">职业规划</h3>
                    <p class="text-xs text-gray-500 text-left leading-relaxed">基于你的背景，制定职业发展路径</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="chat-messages mb-8 space-y-4 animate-[fadeInUp_0.5s_ease-out_0.3s_both]" v-if="chatMessages.length > 0">
            <div v-for="(message, index) in chatMessages" :key="index" class="chat-message">
              <div class="ai-message bg-gray-900/50 backdrop-blur-sm p-4 rounded-lg border border-gray-800 hover:border-purple-500/30 transition-all duration-300">
                <div class="flex items-start gap-3">
                  <div class="ai-avatar w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                    <span class="text-white text-sm font-bold">AI</span>
                  </div>
                  <div class="flex-1">
                    <pre class="text-sm whitespace-pre-wrap text-gray-300">{{ message.content }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="quick-actions-bubbles mb-4 flex flex-wrap gap-2 justify-start animate-[fadeInUp_0.5s_ease-out_0.4s_both]">
            <button
              v-for="action in quickActions"
              :key="action"
              class="quick-action px-3 py-1 rounded-full bg-gray-800/80 hover:bg-gray-700 hover:scale-105 text-xs text-gray-300 transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/20"
            >
              {{ action }}
            </button>
          </div>

          <div class="input-container fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-4xl animate-[fadeInUp_0.5s_ease-out_0.5s_both]">
            <div
              class="input-wrapper relative bg-white/5 backdrop-blur-xl rounded-xl border border-gray-700 p-4 mx-4 transition-all duration-300"
              :class="{ 'border-purple-500/50 shadow-lg shadow-purple-500/20': dropZoneActive }"
              @dragstart="handleDragStart"
              @dragenter="handleDragEnter"
              @dragleave="handleDragLeave"
              @drop="handleDrop"
            >
              <input
                type="file"
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                @change="handleFileChange"
                accept=".pdf,.doc,.docx"
              />

              <div class="flex items-center gap-3">
                <div class="attachment-icon text-gray-400 hover:text-purple-400 cursor-pointer transition-colors duration-300 hover:scale-110">
                  📎
                </div>

                <div class="flex-1">
                  <input
                    type="text"
                    v-model="userInput"
                    class="w-full bg-transparent border-none outline-none text-gray-300 placeholder-gray-500"
                    placeholder="输入你的问题或拖拽文件到这里..."
                  />
                  <p v-if="selectedFile" class="text-xs text-green-400 mt-1">
                    已选择：{{ selectedFile.name }}
                  </p>
                </div>

                <button
                  class="send-button bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-5 py-2 rounded-full hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-300 hover:-translate-y-0.5 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:scale-100"
                  @click="handleSend"
                  :disabled="isUploading"
                >
                  {{ isUploading ? '分析中...' : '发送' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  background-color: #050505;
}

.left-sidebar::-webkit-scrollbar,
.main-content::-webkit-scrollbar {
  width: 6px;
}

.left-sidebar::-webkit-scrollbar-track,
.main-content::-webkit-scrollbar-track {
  background: #0a0a0a;
}

.left-sidebar::-webkit-scrollbar-thumb,
.main-content::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 3px;
}

.left-sidebar::-webkit-scrollbar-thumb:hover,
.main-content::-webkit-scrollbar-thumb:hover {
  background: #484f58;
}

.input-wrapper:focus-within {
  border-color: rgba(168, 85, 247, 0.5) !important;
  box-shadow: 0 0 20px rgba(168, 85, 247, 0.2) !important;
}

.menu-item:hover {
  position: relative;
}

.menu-item:hover::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(to bottom, #a855f7, #4f46e5);
  border-radius: 0 2px 2px 0;
}

.card {
  transition: all 0.3s ease;
}

button.bg-gradient-to-r.from-purple-500.to-indigo-600 {
  box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.menu-item {
  transition: all 0.3s ease;
}

.menu-item:hover span:last-child {
  color: white;
}

.history-item {
  transition: all 0.3s ease;
}

.quick-action {
  transition: all 0.2s ease;
}
</style>
