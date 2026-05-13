<template>
  <div class="min-h-screen flex items-center justify-center bg-[#050505]">
    <CyberGlassCard title="登录 / 注册" class="w-full max-w-md mx-4">
      <div class="text-center space-y-6">
        <p class="text-gray-400 text-sm leading-relaxed">
          认证系统即将上线，敬请期待...
        </p>
        <button
          class="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg border border-purple-500/30 text-purple-200 hover:bg-purple-500/10 hover:border-purple-400/50 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
          @click="goHome"
        >
          返回首页
        </button>
      </div>
    </CyberGlassCard>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import CyberGlassCard from './components/CyberGlassCard.vue'

const router = useRouter()

/** 返回首页导航 */
const goHome = () => {
  router.push('/')
}
</script>
