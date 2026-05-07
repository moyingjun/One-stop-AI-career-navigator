<script setup>
import { useRouter } from 'vue-router'
import { ArrowLeft, FileText, Folder } from 'lucide-vue-next'

const router = useRouter()
</script>

<template>
  <div class="min-h-[100dvh] bg-[#050505] text-gray-200 relative overflow-hidden">
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-0 left-0 w-[50vw] h-[50vh] bg-gradient-to-br from-cyan-500/10 via-purple-500/5 to-transparent blur-3xl animate-pulse-slow"></div>
      <div class="absolute bottom-0 right-0 w-[50vw] h-[50vh] bg-gradient-to-tl from-emerald-500/10 via-blue-500/5 to-transparent blur-3xl animate-pulse-slower"></div>
    </div>
    <div class="relative z-10 min-h-[100dvh] flex flex-col">
      <div class="bg-white/[0.02] backdrop-blur-xl border-b border-white/[0.05] px-4 py-4">
        <div class="max-w-5xl mx-auto flex items-center gap-3">
          <button @click="router.push('/dashboard')" class="p-2 rounded-lg hover:bg-white/5 transition-all duration-300 group">
            <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
          </button>
          <Folder class="w-6 h-6 text-cyan-300" />
          <h1 class="text-xl font-bold text-white">文件管理</h1>
        </div>
      </div>
      <div class="flex-1 flex items-center justify-center px-4">
        <div class="w-full max-w-md rounded-2xl border border-white/10 bg-[#151520]/60 backdrop-blur-2xl p-8 text-center shadow-[0_0_30px_rgba(6,182,212,0.08)]">
          <div class="w-16 h-16 rounded-2xl mx-auto mb-5 bg-cyan-500/10 border border-cyan-400/20 flex items-center justify-center">
            <FileText class="w-8 h-8 text-cyan-300" />
          </div>
          <h2 class="text-lg font-bold text-white mb-2">文件管理模块</h2>
          <p class="text-sm text-gray-400">这里将承载知识库文件、简历资产、行业报告与升学资料的统一管理。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }
.animate-pulse-slower { animation: pulse-slow 8s ease-in-out infinite; animation-delay: -4s; }
@keyframes pulse-slow { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 1; } }
</style>
