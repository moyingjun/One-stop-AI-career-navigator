<script setup>
/**
 * Auth.vue — 注册 / 登录双 Tab 表单
 *
 * 功能：
 *   - 注册 Tab：用户名、密码、可选邮箱，调用 authService.registerUser()
 *   - 登录 Tab：用户名、密码，调用 authService.loginUser()
 *   - 成功后跳转 /dashboard
 *   - 失败时展示错误 Toast（显示 error.message）
 *
 * 样式：Dark Cyberpunk + Glassmorphism（与全局设计语言一致）
 *
 * Requirements: 2.5, 7.1, 7.2
 */
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser, loginUser } from '@/services/authService'
import CyberGlassCard from '@/components/CyberGlassCard.vue'
import { User, Lock, Mail, LogIn, UserPlus, Loader2, X, AlertCircle } from 'lucide-vue-next'

const router = useRouter()

// ─────────────────────────────────────────────
// Tab 状态：'login' | 'register'
// ─────────────────────────────────────────────
const activeTab = ref('login')

const switchTab = (tab) => {
  activeTab.value = tab
  // 切换 Tab 时清空错误提示
  toast.visible = false
  toast.message = ''
}

// ─────────────────────────────────────────────
// 表单数据
// ─────────────────────────────────────────────
const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  email: ''   // 可选
})

// ─────────────────────────────────────────────
// 加载状态
// ─────────────────────────────────────────────
const isLoading = ref(false)

// ─────────────────────────────────────────────
// Toast 错误提示
// ─────────────────────────────────────────────
const toast = reactive({
  visible: false,
  message: ''
})

let toastTimer = null

/**
 * 展示错误 Toast，3 秒后自动消失
 * @param {string} message - 错误信息
 */
const showErrorToast = (message) => {
  toast.message = message
  toast.visible = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.visible = false
  }, 3000)
}

const dismissToast = () => {
  toast.visible = false
  if (toastTimer) clearTimeout(toastTimer)
}

// ─────────────────────────────────────────────
// 表单校验（前端轻量校验，后端仍做完整校验）
// ─────────────────────────────────────────────
const validateLoginForm = () => {
  if (!loginForm.username.trim()) return '请输入用户名'
  if (!loginForm.password) return '请输入密码'
  return null
}

const validateRegisterForm = () => {
  if (!registerForm.username.trim()) return '请输入用户名'
  if (registerForm.username.trim().length > 50) return '用户名不能超过 50 个字符'
  if (!/^[a-zA-Z0-9_]+$/.test(registerForm.username.trim())) return '用户名只能包含字母、数字和下划线'
  if (!registerForm.password) return '请输入密码'
  if (registerForm.password.length < 8) return '密码至少需要 8 个字符'
  if (registerForm.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerForm.email)) {
    return '邮箱格式不正确'
  }
  return null
}

// ─────────────────────────────────────────────
// 登录处理
// ─────────────────────────────────────────────
const handleLogin = async () => {
  const validationError = validateLoginForm()
  if (validationError) {
    showErrorToast(validationError)
    return
  }

  isLoading.value = true
  try {
    await loginUser(loginForm.username.trim(), loginForm.password)
    // 登录成功：跳转 /dashboard（Requirements 2.5）
    router.push('/dashboard')
  } catch (error) {
    // 登录失败：展示错误 Toast（Requirements 7.6）
    showErrorToast(error.message || '登录失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

// ─────────────────────────────────────────────
// 注册处理
// ─────────────────────────────────────────────
const handleRegister = async () => {
  const validationError = validateRegisterForm()
  if (validationError) {
    showErrorToast(validationError)
    return
  }

  isLoading.value = true
  try {
    const email = registerForm.email.trim() || undefined
    await registerUser(registerForm.username.trim(), registerForm.password, email)
    // 注册成功：自动登录并跳转 /dashboard（Requirements 7.1）
    await loginUser(registerForm.username.trim(), registerForm.password)
    router.push('/dashboard')
  } catch (error) {
    // 注册失败：展示错误 Toast（Requirements 7.6）
    showErrorToast(error.message || '注册失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

// ─────────────────────────────────────────────
// 键盘 Enter 提交
// ─────────────────────────────────────────────
const handleKeyEnter = () => {
  if (activeTab.value === 'login') {
    handleLogin()
  } else {
    handleRegister()
  }
}
</script>

<template>
  <!-- 全屏深色背景，带微弱网格纹理 -->
  <div class="auth-page min-h-screen flex items-center justify-center bg-[#050508] relative overflow-hidden">

    <!-- 背景装饰：霓虹光晕 -->
    <div class="absolute inset-0 pointer-events-none" aria-hidden="true">
      <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/8 rounded-full blur-3xl"></div>
      <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyan-500/6 rounded-full blur-3xl"></div>
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-900/5 rounded-full blur-3xl"></div>
    </div>

    <!-- 背景网格线 -->
    <div class="absolute inset-0 pointer-events-none opacity-[0.03]" aria-hidden="true"
         style="background-image: linear-gradient(rgba(139,92,246,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(139,92,246,0.5) 1px, transparent 1px); background-size: 40px 40px;">
    </div>

    <!-- 错误 Toast -->
    <Transition name="toast">
      <div
        v-if="toast.visible"
        class="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-xl border border-red-500/30 bg-red-950/80 backdrop-blur-md shadow-[0_0_20px_rgba(239,68,68,0.2)] text-red-300 text-sm max-w-sm w-full"
        role="alert"
        aria-live="assertive"
      >
        <AlertCircle class="w-4 h-4 flex-shrink-0 text-red-400" />
        <span class="flex-1">{{ toast.message }}</span>
        <button
          class="flex-shrink-0 text-red-400/60 hover:text-red-300 transition-colors focus:outline-none focus:ring-1 focus:ring-red-500/50 rounded"
          @click="dismissToast"
          aria-label="关闭提示"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </Transition>

    <!-- 主卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4">
      <CyberGlassCard :headerless="true" class="w-full">
        <div class="p-8 space-y-6">

          <!-- Logo / 标题区 -->
          <div class="text-center space-y-2">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-600/30 to-cyan-500/20 border border-purple-500/30 mb-2">
              <span class="text-2xl" aria-hidden="true">🚀</span>
            </div>
            <h1 class="text-xl font-bold text-white tracking-wide">AI 职业导航员</h1>
            <p class="text-gray-500 text-xs">One-stop AI Career Navigator</p>
          </div>

          <!-- Tab 切换 -->
          <div class="flex rounded-xl overflow-hidden border border-white/8 bg-white/3 p-1 gap-1" role="tablist" aria-label="登录或注册">
            <button
              role="tab"
              :aria-selected="activeTab === 'login'"
              :class="[
                'flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50',
                activeTab === 'login'
                  ? 'bg-gradient-to-r from-purple-600/40 to-purple-500/30 text-purple-200 border border-purple-500/30 shadow-[0_0_12px_rgba(139,92,246,0.2)]'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              ]"
              @click="switchTab('login')"
            >
              <LogIn class="w-4 h-4" />
              登录
            </button>
            <button
              role="tab"
              :aria-selected="activeTab === 'register'"
              :class="[
                'flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50',
                activeTab === 'register'
                  ? 'bg-gradient-to-r from-cyan-600/40 to-cyan-500/30 text-cyan-200 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
              ]"
              @click="switchTab('register')"
            >
              <UserPlus class="w-4 h-4" />
              注册
            </button>
          </div>

          <!-- ── 登录表单 ── -->
          <Transition name="tab-fade" mode="out-in">
            <form
              v-if="activeTab === 'login'"
              key="login"
              class="space-y-4"
              @submit.prevent="handleLogin"
              novalidate
            >
              <!-- 用户名 -->
              <div class="space-y-1.5">
                <label for="login-username" class="block text-xs font-medium text-gray-400 tracking-wide">
                  用户名
                </label>
                <div class="relative">
                  <User class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" aria-hidden="true" />
                  <input
                    id="login-username"
                    v-model="loginForm.username"
                    type="text"
                    autocomplete="username"
                    placeholder="请输入用户名"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-purple-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] transition-all duration-200"
                    :disabled="isLoading"
                    @keydown.enter.prevent="handleKeyEnter"
                  />
                </div>
              </div>

              <!-- 密码 -->
              <div class="space-y-1.5">
                <label for="login-password" class="block text-xs font-medium text-gray-400 tracking-wide">
                  密码
                </label>
                <div class="relative">
                  <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" aria-hidden="true" />
                  <input
                    id="login-password"
                    v-model="loginForm.password"
                    type="password"
                    autocomplete="current-password"
                    placeholder="请输入密码"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-purple-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] transition-all duration-200"
                    :disabled="isLoading"
                    @keydown.enter.prevent="handleKeyEnter"
                  />
                </div>
              </div>

              <!-- 登录按钮 -->
              <button
                type="submit"
                :disabled="isLoading"
                class="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_30px_rgba(139,92,246,0.5)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50 mt-2"
              >
                <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" aria-hidden="true" />
                <LogIn v-else class="w-4 h-4" aria-hidden="true" />
                {{ isLoading ? '登录中...' : '登录' }}
              </button>

              <!-- 切换到注册 -->
              <p class="text-center text-xs text-gray-600">
                还没有账号？
                <button
                  type="button"
                  class="text-purple-400 hover:text-purple-300 transition-colors focus:outline-none focus:underline"
                  @click="switchTab('register')"
                >
                  立即注册
                </button>
              </p>
            </form>

            <!-- ── 注册表单 ── -->
            <form
              v-else
              key="register"
              class="space-y-4"
              @submit.prevent="handleRegister"
              novalidate
            >
              <!-- 用户名 -->
              <div class="space-y-1.5">
                <label for="reg-username" class="block text-xs font-medium text-gray-400 tracking-wide">
                  用户名 <span class="text-gray-600">（字母、数字、下划线，最多 50 字符）</span>
                </label>
                <div class="relative">
                  <User class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" aria-hidden="true" />
                  <input
                    id="reg-username"
                    v-model="registerForm.username"
                    type="text"
                    autocomplete="username"
                    placeholder="请输入用户名"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] transition-all duration-200"
                    :disabled="isLoading"
                    @keydown.enter.prevent="handleKeyEnter"
                  />
                </div>
              </div>

              <!-- 密码 -->
              <div class="space-y-1.5">
                <label for="reg-password" class="block text-xs font-medium text-gray-400 tracking-wide">
                  密码 <span class="text-gray-600">（至少 8 个字符）</span>
                </label>
                <div class="relative">
                  <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" aria-hidden="true" />
                  <input
                    id="reg-password"
                    v-model="registerForm.password"
                    type="password"
                    autocomplete="new-password"
                    placeholder="请设置密码（至少 8 位）"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] transition-all duration-200"
                    :disabled="isLoading"
                    @keydown.enter.prevent="handleKeyEnter"
                  />
                </div>
              </div>

              <!-- 邮箱（可选） -->
              <div class="space-y-1.5">
                <label for="reg-email" class="block text-xs font-medium text-gray-400 tracking-wide">
                  邮箱 <span class="text-gray-600">（可选）</span>
                </label>
                <div class="relative">
                  <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" aria-hidden="true" />
                  <input
                    id="reg-email"
                    v-model="registerForm.email"
                    type="email"
                    autocomplete="email"
                    placeholder="your@email.com（可不填）"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] transition-all duration-200"
                    :disabled="isLoading"
                    @keydown.enter.prevent="handleKeyEnter"
                  />
                </div>
              </div>

              <!-- 注册按钮 -->
              <button
                type="submit"
                :disabled="isLoading"
                class="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 mt-2"
              >
                <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" aria-hidden="true" />
                <UserPlus v-else class="w-4 h-4" aria-hidden="true" />
                {{ isLoading ? '注册中...' : '创建账号' }}
              </button>

              <!-- 切换到登录 -->
              <p class="text-center text-xs text-gray-600">
                已有账号？
                <button
                  type="button"
                  class="text-cyan-400 hover:text-cyan-300 transition-colors focus:outline-none focus:underline"
                  @click="switchTab('login')"
                >
                  直接登录
                </button>
              </p>
            </form>
          </Transition>

          <!-- 底部分隔线 + 返回首页 -->
          <div class="pt-2 border-t border-white/5 text-center">
            <button
              class="text-xs text-gray-600 hover:text-gray-400 transition-colors focus:outline-none focus:underline"
              @click="router.push('/')"
            >
              ← 返回首页
            </button>
          </div>

        </div>
      </CyberGlassCard>
    </div>
  </div>
</template>

<style scoped>
/* ── 页面背景 ── */
.auth-page {
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── 输入框深色赛博朋克风格 ── */
.auth-input {
  caret-color: rgba(139, 92, 246, 0.9);
}

.auth-input:-webkit-autofill,
.auth-input:-webkit-autofill:hover,
.auth-input:-webkit-autofill:focus {
  /* 覆盖浏览器自动填充的白色背景 */
  -webkit-box-shadow: 0 0 0 1000px rgba(10, 10, 20, 0.9) inset;
  -webkit-text-fill-color: #e2e8f0;
  transition: background-color 5000s ease-in-out 0s;
}

/* ── Toast 过渡动画 ── */
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-12px);
}

/* ── Tab 内容切换动画 ── */
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.tab-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.tab-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
