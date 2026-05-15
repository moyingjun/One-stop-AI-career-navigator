<script setup>
/**
 * Auth.vue — 注册 / 登录双 Tab 表单（邮箱验证码注册体系）
 *
 * 注册流程：
 *   1. 输入邮箱 → 点击"发送验证码" → 弹出 Turnstile 人机验证 Modal
 *   2. Turnstile 回调拿到 token → 自动关闭 Modal → 请求后端发送验证码
 *   3. 输入验证码 + 密码 → 点击"创建账号"
 *
 * 登录流程：
 *   1. 输入邮箱 + 密码 → 点击"登录"
 *   2. 成功后跳转 /dashboard
 *
 * Turnstile 集成（斩首方案）：
 *   - 不在 onMounted 初始化，彻底避免"容器不存在"问题
 *   - 用户点击"发送验证码"时弹出 Modal，Modal 内含 #turnstile-container
 *   - Modal 打开后 nextTick 确保容器已渲染，再调用 turnstile.render()
 *   - Turnstile callback 拿到 token → 自动关闭 Modal → 发送验证码
 *   - 本地未配置 VITE_TURNSTILE_SITE_KEY 时回退到官方测试 Key（永远成功）
 */
import { ref, reactive, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { sendCode, registerWithCode, loginUser } from '@/services/authService'
import { useUserStore } from '@/stores/userStore'
import CyberGlassCard from '@/components/CyberGlassCard.vue'
import {
  Mail, Lock, ShieldCheck, LogIn, UserPlus,
  Loader2, X, AlertCircle, Send, CheckCircle2, ShieldAlert
} from 'lucide-vue-next'

const router = useRouter()
const userStore = useUserStore()

// ─────────────────────────────────────────────
// Tab 状态：'login' | 'register'
// ─────────────────────────────────────────────
const activeTab = ref('login')

const switchTab = (tab) => {
  activeTab.value = tab
  dismissToast()
  codeSent.value = false
  countdown.value = 0
}

// ─────────────────────────────────────────────
// 表单数据
// ─────────────────────────────────────────────
const loginForm = reactive({ email: '', password: '' })

const registerForm = reactive({
  email: '',
  password: '',
  code: ''
})

// ─────────────────────────────────────────────
// 验证码发送状态
// ─────────────────────────────────────────────
const codeSent = ref(false)
const isSendingCode = ref(false)
const countdown = ref(0)
let countdownTimer = null

const startCountdown = (seconds = 60) => {
  countdown.value = seconds
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      countdown.value = 0
    }
  }, 1000)
}

// ─────────────────────────────────────────────
// Cloudflare Turnstile — 斩首方案
// 渲染时机绑定在"发送验证码"按钮点击事件上，
// 而非 onMounted，彻底消除容器不存在的问题。
// ─────────────────────────────────────────────
const turnstileToken = ref('')
const turnstileWidgetId = ref(null)
const showTurnstileModal = ref(false)  // 控制人机验证 Modal 的显示

// SDK 只需加载一次，用此标志防止重复注入 script 标签
let sdkLoaded = false

/**
 * 确保 Turnstile SDK 已加载。
 * 若已加载则直接 resolve，否则动态注入 script 并等待 onload。
 */
const ensureSdkLoaded = () => {
  return new Promise((resolve, reject) => {
    if (window.turnstile) { resolve(); return }
    if (sdkLoaded) {
      // script 已注入但 SDK 还未初始化，轮询等待（最多 5 秒）
      let waited = 0
      const poll = setInterval(() => {
        waited += 100
        if (window.turnstile) { clearInterval(poll); resolve() }
        else if (waited >= 5000) { clearInterval(poll); reject(new Error('Turnstile SDK 加载超时')) }
      }, 100)
      return
    }
    sdkLoaded = true
    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
    script.async = true
    script.defer = true
    script.onload = resolve
    script.onerror = () => reject(new Error('Turnstile SDK 加载失败'))
    document.head.appendChild(script)
  })
}

/**
 * 打开人机验证 Modal 并渲染 Turnstile widget。
 * 此时 #turnstile-modal-container 由 v-if="showTurnstileModal" 保证已存在。
 */
const openTurnstileModal = async () => {
  // 先显示 Modal，让 Vue 把容器节点渲染到 DOM
  showTurnstileModal.value = true

  // 等待 Vue 完成本次渲染（此时容器节点 100% 存在）
  await nextTick()

  const siteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'
  const container = document.getElementById('turnstile-modal-container')

  if (!container) {
    // 理论上不会走到这里，但保留兜底日志
    console.error('[Auth] #turnstile-modal-container 未找到，请检查模板')
    showTurnstileModal.value = false
    return
  }

  try {
    await ensureSdkLoaded()
  } catch (err) {
    console.error('[Auth]', err.message)
    showTurnstileModal.value = false
    showToast('人机验证组件加载失败，请检查网络后重试')
    return
  }

  // 若之前渲染过 widget，先销毁再重建（避免重复渲染报错）
  if (turnstileWidgetId.value !== null) {
    try { window.turnstile.remove(turnstileWidgetId.value) } catch { /* 静默 */ }
    turnstileWidgetId.value = null
  }

  turnstileToken.value = ''
  turnstileWidgetId.value = window.turnstile.render(container, {
    sitekey: siteKey,
    theme: 'dark',
    callback: (token) => {
      // 拿到 token → 关闭 Modal → 继续发送验证码流程
      turnstileToken.value = token
      showTurnstileModal.value = false
      doSendCode(token)
    },
    'expired-callback': () => { turnstileToken.value = '' },
    'error-callback': () => {
      turnstileToken.value = ''
      showToast('人机验证失败，请重试')
    }
  })
}

/**
 * 关闭人机验证 Modal（用户手动关闭，不发送验证码）
 */
const closeTurnstileModal = () => {
  showTurnstileModal.value = false
  isSendingCode.value = false
}

// ─────────────────────────────────────────────
// 加载状态
// ─────────────────────────────────────────────
const isLoading = ref(false)

// ─────────────────────────────────────────────
// Toast 提示（支持 error / success 两种类型）
// ─────────────────────────────────────────────
const toast = reactive({ visible: false, message: '', type: 'error' })
let toastTimer = null

const showToast = (message, type = 'error') => {
  toast.message = message
  toast.type = type
  toast.visible = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.visible = false }, 4000)
}

const dismissToast = () => {
  toast.visible = false
  if (toastTimer) clearTimeout(toastTimer)
}

// ─────────────────────────────────────────────
// 表单校验
// ─────────────────────────────────────────────
const validateEmail = (email) => {
  if (!email.trim()) return '请输入邮箱地址'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return '邮箱格式不正确'
  return null
}

const validatePassword = (password) => {
  if (!password) return '请输入密码'
  if (password.length < 8) return '密码至少需要 8 个字符'
  return null
}

// ─────────────────────────────────────────────
// 发送验证码（两步：先弹 Turnstile Modal，再发请求）
// ─────────────────────────────────────────────

/**
 * 第一步：校验邮箱 → 弹出 Turnstile Modal
 * Turnstile callback 会自动调用 doSendCode(token)
 */
const handleSendCode = async () => {
  const emailError = validateEmail(registerForm.email)
  if (emailError) { showToast(emailError); return }

  if (countdown.value > 0) {
    showToast(`请 ${countdown.value} 秒后再试`)
    return
  }

  isSendingCode.value = true
  await openTurnstileModal()
  // 注意：isSendingCode 会在 doSendCode 的 finally 里重置
  // 若用户手动关闭 Modal，closeTurnstileModal 会重置它
}

/**
 * 第二步：拿到 Turnstile token 后，真正请求后端发送验证码
 * 由 Turnstile callback 自动触发，不由用户直接调用
 *
 * @param {string} token - Turnstile 返回的验证 token
 */
const doSendCode = async (token) => {
  try {
    await sendCode(registerForm.email.trim(), token)
    codeSent.value = true
    startCountdown(60)
    showToast('验证码已发送，请查收邮件', 'success')
  } catch (error) {
    showToast(error.message || '验证码发送失败，请稍后重试')
  } finally {
    isSendingCode.value = false
  }
}

// ─────────────────────────────────────────────
// 注册处理
// ─────────────────────────────────────────────
const handleRegister = async () => {
  const emailError = validateEmail(registerForm.email)
  if (emailError) { showToast(emailError); return }

  const passwordError = validatePassword(registerForm.password)
  if (passwordError) { showToast(passwordError); return }

  if (!registerForm.code.trim()) { showToast('请输入验证码'); return }
  if (!/^\d{6}$/.test(registerForm.code.trim())) { showToast('验证码必须为 6 位数字'); return }

  isLoading.value = true
  try {
    const data = await registerWithCode(
      registerForm.email.trim(),
      registerForm.password,
      registerForm.code.trim()
    )
    userStore.login(data)
    showToast('注册成功，欢迎加入！', 'success')
    setTimeout(() => router.push('/dashboard'), 800)
  } catch (error) {
    showToast(error.message || '注册失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

// ─────────────────────────────────────────────
// 登录处理
// ─────────────────────────────────────────────
const handleLogin = async () => {
  const emailError = validateEmail(loginForm.email)
  if (emailError) { showToast(emailError); return }

  const passwordError = validatePassword(loginForm.password)
  if (passwordError) { showToast(passwordError); return }

  isLoading.value = true
  try {
    const data = await loginUser(loginForm.email.trim(), loginForm.password)
    userStore.login(data)
    router.push('/dashboard')
  } catch (error) {
    showToast(error.message || '邮箱或密码错误')
  } finally {
    isLoading.value = false
  }
}

const handleKeyEnter = () => {
  if (activeTab.value === 'login') handleLogin()
  else handleRegister()
}

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<template>
  <div class="auth-page min-h-screen flex items-center justify-center bg-[#050508] relative overflow-hidden">

    <!-- 背景装饰 -->
    <div class="absolute inset-0 pointer-events-none" aria-hidden="true">
      <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/8 rounded-full blur-3xl"></div>
      <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyan-500/6 rounded-full blur-3xl"></div>
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-900/5 rounded-full blur-3xl"></div>
    </div>
    <div class="absolute inset-0 pointer-events-none opacity-[0.03]" aria-hidden="true"
         style="background-image: linear-gradient(rgba(139,92,246,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(139,92,246,0.5) 1px, transparent 1px); background-size: 40px 40px;">
    </div>

    <!-- Toast -->
    <Transition name="toast">
      <div
        v-if="toast.visible"
        :class="[
          'fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-xl border backdrop-blur-md shadow-lg text-sm max-w-sm w-full',
          toast.type === 'success'
            ? 'border-emerald-500/30 bg-emerald-950/80 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.2)]'
            : 'border-red-500/30 bg-red-950/80 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.2)]'
        ]"
        role="alert"
        aria-live="assertive"
      >
        <CheckCircle2 v-if="toast.type === 'success'" class="w-4 h-4 flex-shrink-0 text-emerald-400" />
        <AlertCircle v-else class="w-4 h-4 flex-shrink-0 text-red-400" />
        <span class="flex-1">{{ toast.message }}</span>
        <button class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity focus:outline-none rounded"
                @click="dismissToast" aria-label="关闭提示">
          <X class="w-4 h-4" />
        </button>
      </div>
    </Transition>

    <!-- ══════════════════════════════════════════
         Turnstile 人机验证 Modal
         v-if 保证：Modal 打开时容器节点 100% 存在，
         nextTick 后立即调用 turnstile.render()
    ══════════════════════════════════════════ -->
    <Transition name="modal-fade">
      <div
        v-if="showTurnstileModal"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="人机验证"
        @click.self="closeTurnstileModal"
      >
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm"></div>

        <!-- 弹窗主体 -->
        <div class="relative z-10 w-full max-w-sm rounded-2xl border border-white/10 bg-gray-950/95 shadow-[0_0_60px_rgba(139,92,246,0.2)] p-6 space-y-4">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <ShieldAlert class="w-5 h-5 text-cyan-400" />
              <span class="text-sm font-semibold text-white">人机身份验证</span>
            </div>
            <button
              class="text-gray-500 hover:text-gray-300 transition-colors focus:outline-none rounded"
              aria-label="关闭验证窗口"
              @click="closeTurnstileModal"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <p class="text-xs text-gray-500 leading-relaxed">
            为保护账号安全，请完成下方验证。验证通过后将自动发送验证码。
          </p>

          <!-- Turnstile 挂载点 —— 此时由 v-if 保证节点已存在 -->
          <div
            id="turnstile-modal-container"
            style="min-height: 65px; display: flex; justify-content: center; align-items: center;"
          >
            <!-- Turnstile widget 将被注入此处 -->
            <Loader2 class="w-5 h-5 text-gray-600 animate-spin" />
          </div>

          <p class="text-[11px] text-gray-600 text-center">
            由 Cloudflare Turnstile 提供保护 · 验证通过后自动继续
          </p>
        </div>
      </div>
    </Transition>

    <!-- 主卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4">
      <CyberGlassCard :headerless="true" class="w-full">
        <div class="p-8 space-y-6">

          <!-- Logo -->
          <div class="text-center space-y-2">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-600/30 to-cyan-500/20 border border-purple-500/30 mb-2">
              <span class="text-2xl" aria-hidden="true">🚀</span>
            </div>
            <h1 class="text-xl font-bold text-white tracking-wide">AI 职业导航员</h1>
            <p class="text-gray-500 text-xs">One-stop AI Career Navigator</p>
          </div>

          <!-- Tab 切换 -->
          <div class="flex rounded-xl overflow-hidden border border-white/8 bg-white/3 p-1 gap-1" role="tablist">
            <button
              role="tab" :aria-selected="activeTab === 'login'"
              :class="['flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50',
                activeTab === 'login'
                  ? 'bg-gradient-to-r from-purple-600/40 to-purple-500/30 text-purple-200 border border-purple-500/30 shadow-[0_0_12px_rgba(139,92,246,0.2)]'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5']"
              @click="switchTab('login')"
            >
              <LogIn class="w-4 h-4" />登录
            </button>
            <button
              role="tab" :aria-selected="activeTab === 'register'"
              :class="['flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50',
                activeTab === 'register'
                  ? 'bg-gradient-to-r from-cyan-600/40 to-cyan-500/30 text-cyan-200 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5']"
              @click="switchTab('register')"
            >
              <UserPlus class="w-4 h-4" />注册
            </button>
          </div>

          <Transition name="tab-fade" mode="out-in">

            <!-- ── 登录表单 ── -->
            <form v-if="activeTab === 'login'" key="login" class="space-y-4" @submit.prevent="handleLogin" novalidate>

              <div class="space-y-1.5">
                <label for="login-email" class="block text-xs font-medium text-gray-400 tracking-wide">邮箱</label>
                <div class="relative">
                  <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                  <input id="login-email" v-model="loginForm.email" type="email" autocomplete="email"
                    placeholder="your@email.com"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-purple-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] transition-all duration-200"
                    :disabled="isLoading" @keydown.enter.prevent="handleKeyEnter" />
                </div>
              </div>

              <div class="space-y-1.5">
                <label for="login-password" class="block text-xs font-medium text-gray-400 tracking-wide">密码</label>
                <div class="relative">
                  <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                  <input id="login-password" v-model="loginForm.password" type="password" autocomplete="current-password"
                    placeholder="请输入密码"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-purple-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] transition-all duration-200"
                    :disabled="isLoading" @keydown.enter.prevent="handleKeyEnter" />
                </div>
              </div>

              <button type="submit" :disabled="isLoading"
                class="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_30px_rgba(139,92,246,0.5)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50 mt-2">
                <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
                <LogIn v-else class="w-4 h-4" />
                {{ isLoading ? '登录中...' : '登录' }}
              </button>

              <p class="text-center text-xs text-gray-600">
                还没有账号？
                <button type="button" class="text-purple-400 hover:text-purple-300 transition-colors focus:outline-none focus:underline" @click="switchTab('register')">立即注册</button>
              </p>
            </form>

            <!-- ── 注册表单 ── -->
            <form v-else key="register" class="space-y-4" @submit.prevent="handleRegister" novalidate>

              <!-- 邮箱 + 发送验证码 -->
              <div class="space-y-1.5">
                <label for="reg-email" class="block text-xs font-medium text-gray-400 tracking-wide">邮箱</label>
                <div class="flex gap-2">
                  <div class="relative flex-1">
                    <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                    <input id="reg-email" v-model="registerForm.email" type="email" autocomplete="email"
                      placeholder="your@email.com"
                      class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] transition-all duration-200"
                      :disabled="isLoading || isSendingCode" />
                  </div>
                  <button type="button"
                    :disabled="isSendingCode || countdown > 0 || isLoading"
                    class="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="codeSent && countdown > 0
                      ? 'border-gray-600/40 bg-gray-800/40 text-gray-500'
                      : 'border-cyan-500/40 bg-cyan-900/20 text-cyan-300 hover:bg-cyan-900/40 hover:border-cyan-400/60'"
                    @click="handleSendCode">
                    <Loader2 v-if="isSendingCode" class="w-3 h-3 animate-spin" />
                    <Send v-else class="w-3 h-3" />
                    {{ countdown > 0 ? `${countdown}s` : (codeSent ? '重新发送' : '发送验证码') }}
                  </button>
                </div>
                <!-- 验证码发送后的安全提示 -->
                <Transition name="hint-fade">
                  <p v-if="codeSent" class="flex items-start gap-1.5 text-[11px] leading-relaxed mt-2 px-1">
                    <span class="flex-shrink-0 mt-px" aria-hidden="true">⚠️</span>
                    <span class="text-amber-400/80">
                      验证码已通过专属加密通道发送。由于本站邮件安全评级较高，部分邮箱（如 Gmail）可能将其归档至
                      <span class="font-semibold text-amber-300">【广告邮件】</span>或
                      <span class="font-semibold text-amber-300">【垃圾箱】</span>，请注意查收。
                    </span>
                  </p>
                </Transition>
              </div>

              <!-- 验证码输入 -->
              <div class="space-y-1.5">
                <label for="reg-code" class="block text-xs font-medium text-gray-400 tracking-wide">
                  验证码 <span class="text-gray-600">（6 位数字，10 分钟内有效）</span>
                </label>
                <div class="relative">
                  <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                  <input id="reg-code" v-model="registerForm.code" type="text" inputmode="numeric"
                    maxlength="6" placeholder="请输入邮件中的 6 位验证码"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] transition-all duration-200 tracking-widest"
                    :disabled="isLoading" @keydown.enter.prevent="handleKeyEnter" />
                </div>
                <p class="flex items-start gap-1.5 text-[11px] text-gray-600 leading-relaxed px-1 pt-0.5">
                  <span class="flex-shrink-0 mt-px" aria-hidden="true">💡</span>
                  <span>
                    Tip: 建议将
                    <span class="text-cyan-500/80 font-mono select-all">noreply@onestopainav.com</span>
                    加入邮箱白名单，以确保未来顺利接收系统通知。
                  </span>
                </p>
              </div>

              <!-- 密码 -->
              <div class="space-y-1.5">
                <label for="reg-password" class="block text-xs font-medium text-gray-400 tracking-wide">
                  密码 <span class="text-gray-600">（至少 8 个字符）</span>
                </label>
                <div class="relative">
                  <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                  <input id="reg-password" v-model="registerForm.password" type="password" autocomplete="new-password"
                    placeholder="请设置密码（至少 8 位）"
                    class="auth-input w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 text-sm focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] transition-all duration-200"
                    :disabled="isLoading" @keydown.enter.prevent="handleKeyEnter" />
                </div>
              </div>

              <button type="submit" :disabled="isLoading"
                class="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 mt-2">
                <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
                <UserPlus v-else class="w-4 h-4" />
                {{ isLoading ? '注册中...' : '创建账号' }}
              </button>

              <p class="text-center text-xs text-gray-600">
                已有账号？
                <button type="button" class="text-cyan-400 hover:text-cyan-300 transition-colors focus:outline-none focus:underline" @click="switchTab('login')">直接登录</button>
              </p>
            </form>

          </Transition>

          <!-- 返回首页 -->
          <div class="pt-2 border-t border-white/5 text-center">
            <button class="text-xs text-gray-600 hover:text-gray-400 transition-colors focus:outline-none focus:underline"
                    @click="router.push('/')">
              ← 返回首页
            </button>
          </div>

        </div>
      </CyberGlassCard>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.auth-input {
  caret-color: rgba(139, 92, 246, 0.9);
}

.auth-input:-webkit-autofill,
.auth-input:-webkit-autofill:hover,
.auth-input:-webkit-autofill:focus {
  -webkit-box-shadow: 0 0 0 1000px rgba(10, 10, 20, 0.9) inset;
  -webkit-text-fill-color: #e2e8f0;
  transition: background-color 5000s ease-in-out 0s;
}

/* Toast 动画 */
.toast-enter-active, .toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-12px);
}

/* Tab 切换动画 */
.tab-fade-enter-active, .tab-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.tab-fade-enter-from { opacity: 0; transform: translateY(6px); }
.tab-fade-leave-to   { opacity: 0; transform: translateY(-6px); }

/* 提示文字动画 */
.hint-fade-enter-active, .hint-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.hint-fade-enter-from, .hint-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Turnstile Modal 动画 */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active .relative,
.modal-fade-leave-active .relative {
  transition: transform 0.2s ease;
}
.modal-fade-enter-from .relative {
  transform: scale(0.95) translateY(8px);
}
.modal-fade-leave-to .relative {
  transform: scale(0.95) translateY(8px);
}
</style>
