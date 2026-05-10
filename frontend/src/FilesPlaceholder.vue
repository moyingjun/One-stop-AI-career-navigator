<script setup>
import { useRouter } from 'vue-router'
import { ArrowLeft, BriefcaseBusiness, FileText, UploadCloud } from 'lucide-vue-next'

const router = useRouter()
</script>

<template>
  <div class="min-h-[100dvh] bg-[#050505] text-gray-200 relative overflow-hidden">
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-0 left-0 w-[48vw] h-[48vh] bg-gradient-to-br from-cyan-500/10 via-fuchsia-500/5 to-transparent blur-3xl animate-pulse-slow"></div>
      <div class="absolute bottom-0 right-0 w-[48vw] h-[48vh] bg-gradient-to-tl from-emerald-500/10 via-blue-500/5 to-transparent blur-3xl animate-pulse-slower"></div>
      <div class="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>

    <div class="relative z-10 min-h-[100dvh] flex flex-col">
      <header class="bg-white/[0.02] backdrop-blur-xl border-b border-white/[0.05] px-4 py-4">
        <div class="max-w-5xl mx-auto flex items-center gap-3">
          <button @click="router.push('/dashboard')" class="p-2 rounded-lg hover:bg-white/5 transition-all duration-300 group">
            <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
          </button>
          <div class="w-10 h-10 rounded-xl border border-cyan-400/25 bg-cyan-500/10 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.12)]">
            <BriefcaseBusiness class="w-5 h-5 text-cyan-300" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-white">个人求职材料库</h1>
            <p class="text-xs text-gray-500 mt-0.5">Resume / Portfolio / JD Assets</p>
          </div>
        </div>
      </header>

      <main class="flex-1 flex items-center justify-center px-4 py-10">
        <section class="w-full max-w-3xl text-center">
          <div class="mb-8">
            <div class="w-16 h-16 rounded-2xl mx-auto mb-5 bg-cyan-500/10 border border-cyan-400/25 flex items-center justify-center shadow-[0_0_28px_rgba(34,211,238,0.16)]">
              <FileText class="w-8 h-8 text-cyan-300" />
            </div>
            <h2 class="text-2xl font-bold text-white mb-3">个人求职材料库</h2>
            <p class="text-sm md:text-base text-gray-400 leading-relaxed max-w-2xl mx-auto">
              在这里统一管理你的默认简历、作品集和目标岗位 JD，让模拟面试和简历诊断更精准。
            </p>
          </div>

          <div class="rounded-2xl border border-white/10 bg-[#12121b]/70 backdrop-blur-2xl p-4 md:p-6 shadow-[0_0_36px_rgba(6,182,212,0.08)]">
            <div class="min-h-[260px] rounded-xl border-2 border-dashed border-cyan-400/30 bg-black/25 flex flex-col items-center justify-center px-6 py-10 transition-all duration-300 hover:border-cyan-300/60 hover:bg-cyan-500/5">
              <div class="w-14 h-14 rounded-2xl border border-cyan-400/30 bg-cyan-500/10 flex items-center justify-center mb-5">
                <UploadCloud class="w-7 h-7 text-cyan-300" />
              </div>
              <h3 class="text-base font-semibold text-white mb-2">拖拽上传求职材料</h3>
              <p class="text-sm text-gray-500 max-w-md leading-relaxed">
                UI 占位：后续可接入默认简历、作品集、目标岗位 JD 的上传与版本管理。
              </p>
              <button class="mt-6 px-5 py-2.5 rounded-xl border border-cyan-400/30 bg-cyan-500/10 text-cyan-200 text-sm hover:bg-cyan-500/20 hover:text-white transition-all duration-300">
                选择文件
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }
.animate-pulse-slower { animation: pulse-slow 8s ease-in-out infinite; animation-delay: -4s; }
@keyframes pulse-slow { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 1; } }
</style>
