<script setup>
import { useRouter } from 'vue-router'
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const router = useRouter()

const mouseX = ref(0)
const mouseY = ref(0)
const smokeCanvas = ref(null)
let smokeRenderer = null
let smokeScene = null
let smokeCamera = null
let smokeGeometry = null
let smokeMaterial = null
let smokeFrameId = null
let smokeStartTime = 0

const smokeVertexShader = `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`

const smokeFragmentShader = `
  precision highp float;

  uniform float u_time;
  uniform vec2 u_resolution;
  varying vec2 vUv;

  vec3 mod289(vec3 x) {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
  }

  vec4 mod289(vec4 x) {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
  }

  vec4 permute(vec4 x) {
    return mod289(((x * 34.0) + 1.0) * x);
  }

  vec4 taylorInvSqrt(vec4 r) {
    return 1.79284291400159 - 0.85373472095314 * r;
  }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);

    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);

    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;

    i = mod289(i);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));

    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;

    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);

    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);

    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);

    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));

    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);

    vec4 norm = taylorInvSqrt(vec4(
      dot(p0, p0),
      dot(p1, p1),
      dot(p2, p2),
      dot(p3, p3)
    ));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;

    vec4 m = max(0.6 - vec4(
      dot(x0, x0),
      dot(x1, x1),
      dot(x2, x2),
      dot(x3, x3)
    ), 0.0);
    m = m * m;
    return 42.0 * dot(m * m, vec4(
      dot(p0, x0),
      dot(p1, x1),
      dot(p2, x2),
      dot(p3, x3)
    ));
  }

  float fbm(vec3 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;

    for (int i = 0; i < 6; i++) {
      value += amplitude * snoise(p * frequency);
      frequency *= 2.02;
      amplitude *= 0.52;
      p += vec3(17.0, 11.0, 5.0);
    }

    return value;
  }

  void main() {
    vec2 uv = vUv;
    vec2 aspect = vec2(u_resolution.x / max(u_resolution.y, 1.0), 1.0);
    vec2 p = (uv - 0.5) * aspect;

    float t = u_time * 0.035;
    float drift = fbm(vec3(p * 1.15 + vec2(t * 0.22, -t * 0.15), t));
    float curl = fbm(vec3(p * 2.1 + drift * 0.35, t * 1.35 + 6.0));
    float vapor = fbm(vec3(p * 3.0 + curl * 0.22, t * 1.8 + 13.0));

    float cloud = smoothstep(0.04, 0.78, drift * 0.48 + curl * 0.34 + vapor * 0.18 + 0.36);
    float vignette = smoothstep(0.92, 0.08, length(p * vec2(0.82, 1.08)));
    float edgeGlow = pow(max(cloud, 0.0), 2.2) * vignette;

    vec3 deepSpace = vec3(0.008, 0.008, 0.020);
    vec3 ghostPurple = vec3(0.35, 0.25, 0.65);
    vec3 dimViolet = vec3(0.55, 0.15, 0.75);
    vec3 cyanTech = vec3(0.05, 0.45, 0.55);

    vec3 color = deepSpace;
    float baseGlow = smoothstep(0.2, 0.8, vapor * 0.5 + 0.2) * vignette;
    color += ghostPurple * cloud * 0.45;
    color += dimViolet * edgeGlow * 0.28;
    color += cyanTech * baseGlow * 0.25;
    color += vec3(0.03, 0.05, 0.10) * pow(vignette, 3.0) * 0.05;

    gl_FragColor = vec4(color, 1.0);
  }
`

const resizeSmoke = () => {
  if (!smokeRenderer || !smokeMaterial) return

  const width = window.innerWidth
  const height = window.innerHeight
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)

  smokeRenderer.setPixelRatio(pixelRatio)
  smokeRenderer.setSize(width, height, false)
  smokeMaterial.uniforms.u_resolution.value.set(width * pixelRatio, height * pixelRatio)
}

const renderSmoke = () => {
  if (!smokeRenderer || !smokeScene || !smokeCamera || !smokeMaterial) return

  smokeMaterial.uniforms.u_time.value = (performance.now() - smokeStartTime) * 0.001
  smokeRenderer.render(smokeScene, smokeCamera)
  smokeFrameId = requestAnimationFrame(renderSmoke)
}

const initSmoke = () => {
  if (!smokeCanvas.value || smokeRenderer) return

  smokeRenderer = new THREE.WebGLRenderer({
    canvas: smokeCanvas.value,
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance'
  })
  smokeRenderer.setClearColor(0x020205, 1)

  smokeScene = new THREE.Scene()
  smokeCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
  smokeGeometry = new THREE.PlaneGeometry(2, 2)
  smokeMaterial = new THREE.ShaderMaterial({
    vertexShader: smokeVertexShader,
    fragmentShader: smokeFragmentShader,
    depthWrite: false,
    depthTest: false,
    uniforms: {
      u_time: { value: 0 },
      u_resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) }
    }
  })

  smokeScene.add(new THREE.Mesh(smokeGeometry, smokeMaterial))
  smokeStartTime = performance.now()
  resizeSmoke()
  window.addEventListener('resize', resizeSmoke, { passive: true })
  renderSmoke()
}

const destroySmoke = () => {
  if (smokeFrameId) {
    cancelAnimationFrame(smokeFrameId)
    smokeFrameId = null
  }

  window.removeEventListener('resize', resizeSmoke)

  if (smokeGeometry) {
    smokeGeometry.dispose()
    smokeGeometry = null
  }

  if (smokeMaterial) {
    smokeMaterial.dispose()
    smokeMaterial = null
  }

  if (smokeRenderer) {
    smokeRenderer.dispose()
    smokeRenderer.forceContextLoss?.()
    smokeRenderer = null
  }

  smokeScene = null
  smokeCamera = null
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const handleParallax = (e) => {
  mouseX.value = (e.clientX / window.innerWidth - 0.5) * 20
  mouseY.value = (e.clientY / window.innerHeight - 0.5) * 20
}

// 轮播状态
const currentSlide = ref(0)
let timer = null
// 视频DOM引用
const videoRefs = ref([])
// 视频实际时长：video1=8s, video2=8s, video3=5s, 图层3=6s
// 每个视频总时长减去1秒过渡时间，实现完美淡出
const slideDurations = [7000, 7000, 4000, 6000]

const startTimer = () => {
  // 清除旧定时器
  if (timer) {
    clearTimeout(timer)
  }
  // 启动新定时器
  timer = setTimeout(nextSlide, slideDurations[currentSlide.value])
}

const setSlide = (index) => {
  // 立即切换，不等待过渡
  currentSlide.value = index
  // 重置视频播放进度
  if (index < 3 && videoRefs.value[index]) {
    videoRefs.value[index].currentTime = 0
    videoRefs.value[index].play()
  }
  startTimer()
}

const nextSlide = () => {
  currentSlide.value = (currentSlide.value + 1) % 4
  // 重置视频播放进度
  if (currentSlide.value < 3 && videoRefs.value[currentSlide.value]) {
    videoRefs.value[currentSlide.value].currentTime = 0
    videoRefs.value[currentSlide.value].play()
  }
  startTimer()
}

// 系统初始化控制台动画
const playConsoleAnimation = async () => {
  if (window.__EGG_LOGGED__) return
  window.__EGG_LOGGED__ = true

  console.clear()

  const messages = [
    { text: '>> System Initializing...', style: 'color: #9ca3af; font-size: 14px; font-family: monospace;', delay: 0 },
    { text: '>> Model: DeepSeek-V3 Active [OK]', style: 'color: #22c55e; font-size: 14px; font-family: monospace; font-weight: bold;', delay: 500 },
    { text: '>> Identity Verified: Moyingjun', style: 'color: #a855f7; font-size: 14px; font-family: monospace; font-weight: bold;', delay: 500 },
    { text: '%c ✨ AI Career Navigator | Designed & Developed by Moyingjun @ 广东水利电力职业技术学院 ✨ ', style: 'background: linear-gradient(90deg, #a855f7, #6366f1, #06b6d4, #a855f7); background-size: 200% auto; color: #fff; font-size: 14px; font-weight: bold; padding: 8px 16px; border-radius: 4px; animation: gradient 2s linear infinite; font-family: monospace;', delay: 800 }
  ]

  for (const msg of messages) {
    await new Promise(resolve => setTimeout(resolve, msg.delay))
    console.log(msg.text, msg.style)
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleParallax, { passive: true })
  initSmoke()
  startTimer()
  playConsoleAnimation()
})

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', handleParallax)
  if (timer) clearTimeout(timer)
  destroySmoke()
})
</script>

<template>
  <!-- 最外层容器 -->
  <div class="min-h-screen relative z-0 overflow-hidden bg-[#020205]">
    <!-- 科技网格背景 -->
    <canvas ref="smokeCanvas" class="smoke-canvas absolute inset-0 z-[-4] pointer-events-none"></canvas>

    <div
      class="absolute inset-0 z-[-3] pointer-events-none mix-blend-screen overflow-hidden animate-orb-breathe"
      :style="{ transform: `translate(${mouseX * -1.5}px, ${mouseY * -1.5}px)` }"
    >
      <div class="orb-wrapper-x orb-1-x"><div class="orb-inner-y orb-1-y bg-purple-600/40"></div></div>
      <div class="orb-wrapper-x orb-2-x"><div class="orb-inner-y orb-2-y bg-cyan-500/30"></div></div>
      <div class="orb-wrapper-x orb-3-x"><div class="orb-inner-y orb-3-y bg-fuchsia-600/30"></div></div>
    </div>

    <div
      class="absolute inset-0 z-[-2] pointer-events-none parallax-stars"
      :style="{ transform: `translate(${mouseX * -0.5}px, ${mouseY * -0.5}px)` }"
    >
      <div class="meteor meteor-1"></div>
      <div class="meteor meteor-2"></div>
      <div class="meteor meteor-3"></div>
      <div class="meteor meteor-4"></div>
    </div>

    <div class="absolute inset-0 z-[-1] pointer-events-none" style="background: radial-gradient(circle at center, transparent 30%, #020205 120%);"></div>

    <!-- 导航栏 -->
    <nav class="relative z-10 flex justify-between items-center py-4 px-4 md:py-6 md:px-8 max-w-7xl mx-auto">
      <div class="flex items-center gap-3 cursor-pointer" @click="goToDashboard">
        <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
          <span class="text-white font-bold text-sm">AI</span>
        </div>
        <span class="text-white font-semibold text-lg">AI 职业导航</span>
      </div>

      <div class="hidden md:flex items-center gap-8">
        <a href="#" class="text-gray-400 hover:text-white transition-colors duration-300">产品功能</a>
        <a href="#" class="text-gray-400 hover:text-white transition-colors duration-300">工作原理</a>
        <a href="#" class="text-gray-400 hover:text-white transition-colors duration-300">关于我们</a>
      </div>

      <div class="flex items-center gap-4">
        <button class="text-gray-300 hover:text-white transition-colors duration-300 px-4 py-2">
          登录
        </button>
        <button 
          @click="goToDashboard"
          class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-2 rounded-full font-medium hover:shadow-lg hover:shadow-purple-500/40 transition-all duration-300"
        >
          免费开始
        </button>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="relative z-10 max-w-7xl mx-auto px-4 md:px-8 min-h-[calc(100vh-120px)] flex flex-col justify-center">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 md:gap-16 items-center">
        <!-- 左侧：标题与内容 -->
        <div class="text-left">
          <div class="mb-8">
            <h1 class="font-black tracking-tight text-3xl md:text-5xl lg:text-6xl leading-tight flex flex-col items-start mb-6 drop-shadow-[0_0_25px_rgba(168,85,247,0.4)]">
              <div class="text-white mb-2 overflow-hidden whitespace-nowrap animate-typewriter-1">重塑你的</div>
              <div class="flex items-center overflow-hidden whitespace-nowrap animate-typewriter-2 opacity-0">
                <span class="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400 drop-shadow-lg">
                  职业发展轨迹
                </span>
                <span class="text-4xl ml-2">✨</span>
                <span class="animate-cursor-blink text-purple-400 ml-3 font-light opacity-100">|</span>
              </div>
            </h1>
          </div>

          <p class="text-gray-400 text-lg md:text-xl leading-relaxed mb-6 md:mb-10 max-w-lg animate-blur-in-up animation-delay-300">
            AI 驱动的简历诊断与面试模拟，让你的每一次投递都充满底气，助力你在职场中脱颖而出。
          </p>

          <div class="flex flex-col md:flex-row gap-4 mb-6 md:mb-12 animate-blur-in-up animation-delay-400">
            <button 
              @click="goToDashboard"
              class="bg-gradient-to-r from-cyan-500 to-purple-600 text-white px-6 py-3 md:px-10 md:py-4 rounded-xl font-semibold text-base md:text-lg border border-white/20 shadow-[0_0_40px_rgba(34,211,238,0.4)] hover:shadow-[0_0_60px_rgba(168,85,247,0.6)] transition-all duration-300 hover:-translate-y-0.5"
            >
              免费开始使用
            </button>
            <button class="bg-white/5 backdrop-blur-xl border border-white/10 text-gray-300 px-6 py-3 md:px-10 md:py-4 rounded-xl font-semibold text-base md:text-lg hover:bg-white/10 transition-all duration-300 hover:-translate-y-0.5">
              查看演示
            </button>
          </div>

          <!-- 信任背书区域 -->
          <div class="mt-12">
            <p class="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-4">TRUSTED BY</p>
            <div class="flex flex-wrap items-center gap-4 md:gap-6 text-sm text-gray-500 font-medium">
              <span>Google</span>
              <span>Microsoft</span>
              <span>Tencent</span>
              <span>Amazon</span>
              <span>Meta</span>
            </div>
          </div>
        </div>

        <!-- 右侧：经典科技设备框 -->
        <div class="relative w-full min-h-[300px] md:min-h-[500px] lg:min-h-[650px] animate-fade-in-right animation-delay-500">
          <!-- 主设备外壳 -->
          <div class="absolute inset-0 z-10 animate-float" style="transform: perspective(1000px) rotateY(-5deg);">
            <div class="relative w-full h-full flex flex-col bg-[#0a0f1a]/60 backdrop-blur-2xl rounded-3xl border border-cyan-400/30 shadow-[0_0_80px_rgba(34,211,238,0.15),inset_0_0_30px_rgba(168,85,247,0.25)] overflow-hidden">
              <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-gradient-to-br from-cyan-500/15 via-purple-500/15 to-transparent blur-[80px] z-[-1] pointer-events-none"></div>
              <div class="absolute top-0 left-0 w-10 h-10 border-t-2 border-l-2 border-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)] rounded-tl-3xl z-20 pointer-events-none"></div>
              <div class="absolute top-0 right-0 w-10 h-10 border-t-2 border-r-2 border-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)] rounded-tr-3xl z-20 pointer-events-none"></div>
              <div class="absolute bottom-0 left-0 w-10 h-10 border-b-2 border-l-2 border-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)] rounded-bl-3xl z-20 pointer-events-none"></div>
              <div class="absolute bottom-0 right-0 w-10 h-10 border-b-2 border-r-2 border-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)] rounded-br-3xl z-20 pointer-events-none"></div>
              <!-- 顶部边框（带摄像头和切换按钮） -->
              <div class="h-10 bg-white/[0.02] border-b border-white/[0.05] flex items-center justify-between px-6">
                <div class="flex items-center">
                  <div class="flex items-center gap-1 mr-4">
                    <span class="w-0.5 h-0.5 bg-cyan-400/80 shadow-[0_0_8px_rgba(34,211,238,0.8)] animate-terminal-dot"></span>
                    <span class="w-0.5 h-0.5 bg-purple-400/80 shadow-[0_0_8px_rgba(192,132,252,0.8)] animate-terminal-dot animation-delay-300"></span>
                    <span class="w-0.5 h-0.5 bg-cyan-300/70 shadow-[0_0_8px_rgba(103,232,249,0.7)] animate-terminal-dot animation-delay-500"></span>
                  </div>
                </div>
                <!-- 加大的标签指示器 -->
                <div class="flex items-center gap-3">
                  <button 
                    v-for="(item, index) in 4" 
                    :key="index"
                    @click="setSlide(index)"
                    class="rounded-full transition-all duration-200 hover:scale-110 cursor-pointer"
                    :class="currentSlide === index 
                      ? 'w-8 h-2 bg-purple-500 shadow-sm shadow-purple-500/30 cursor-default' 
                      : 'w-2 h-2 bg-white/30 hover:bg-white/50' 
                    "
                  ></button>
                </div>
                <div class="w-8"></div>
              </div>
              
              <!-- 中间屏幕区（16:9比例） -->
              <div class="flex-1 relative overflow-hidden" style="aspect-ratio: 16/9;">
                <div class="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-transparent via-cyan-300 to-transparent shadow-[0_0_20px_rgba(34,211,238,1)] z-40 animate-hologram-scan pointer-events-none"></div>
                <!-- 4图层丝滑轮播 -->
                <div class="absolute inset-0 w-full h-full">
                  <!-- 图层0：AI 大脑 -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 0 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <video :ref="el => videoRefs[0] = el" src="/video1.mp4" autoplay loop muted playsinline class="w-full h-full object-cover"></video>
                  </div>

                  <!-- 图层1：神经核心 -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 1 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <video :ref="el => videoRefs[1] = el" src="/video2.mp4" autoplay loop muted playsinline class="w-full h-full object-cover"></video>
                  </div>

                  <!-- 图层2：数据光缆 -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 2 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <video :ref="el => videoRefs[2] = el" src="/video3.mp4" autoplay loop muted playsinline class="w-full h-full object-cover"></video>
                  </div>

                  <!-- 图层3：现有内容（产品演示视频区 + 毛玻璃卡片） -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 3 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <div class="w-full h-full bg-gradient-to-br from-purple-900/60 via-indigo-900/60 to-black flex items-center justify-center">
                      <!-- 紫色渐变占位 -->
                      <div class="text-center p-4 md:p-8 animate-pulse">
                        <div class="w-20 h-20 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-500/30 animate-pulse">
                          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 10 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <p class="text-white font-semibold text-lg">产品演示视频区</p>
                        <p class="text-gray-400 text-sm mt-2">demo.mp4 即将上线</p>
                      </div>
                    </div>

                    <!-- 环绕卫星卡片1：简历评分 -->
                    <div class="glass-card hidden md:block absolute bottom-6 left-6 z-30 w-44 md:w-60 p-4 rounded-2xl bg-[#0a0a15]/50 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 hover:border-purple-400/40 hover:shadow-[inset_0_1px_1px_rgba(255,255,255,0.1),0_0_40px_rgba(168,85,247,0.3)] hover:-translate-y-2 animate-float-1">
                      <div class="flex items-center gap-3 mb-3">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg">
                          <span class="text-white font-bold text-lg">95</span>
                        </div>
                        <div>
                          <p class="text-white font-semibold text-sm mb-1">简历评分</p>
                          <p class="text-gray-400 text-xs">超越90%候选人</p>
                        </div>
                      </div>
                      <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div class="w-[95%] h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"></div>
                      </div>
                    </div>

                    <!-- 环绕卫星卡片2：面试通过率 -->
                    <div class="glass-card hidden md:block absolute top-6 right-6 z-30 w-44 md:w-60 p-4 rounded-2xl bg-[#0a0a15]/50 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 hover:border-cyan-400/40 hover:shadow-[inset_0_1px_1px_rgba(255,255,255,0.1),0_0_40px_rgba(34,211,238,0.3)] hover:-translate-y-2 animate-float-2">
                      <div class="flex items-center gap-3 mb-2">
                        <span class="text-green-400 font-bold text-xl">+42%</span>
                      </div>
                      <p class="text-white font-semibold text-sm mb-1">面试通过率</p>
                      <p class="text-gray-400 text-xs">AI模拟面试大幅提升通过率</p>
                    </div>

                    <!-- 环绕卫星卡片3：AI助手 -->
                    <div class="glass-card hidden md:block absolute bottom-6 right-6 z-30 w-44 md:w-60 p-4 rounded-2xl bg-[#0a0a15]/50 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 hover:border-pink-400/40 hover:shadow-[inset_0_1px_1px_rgba(255,255,255,0.1),0_0_40px_rgba(236,72,153,0.3)] hover:-translate-y-2 animate-float-3 flex flex-col items-start">
                      <div class="flex items-center gap-3 mb-3 w-full">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
                          <span class="text-white font-bold text-lg">AI</span>
                        </div>
                        <div>
                          <p class="text-white font-semibold text-sm mb-1">AI 助手</p>
                          <p class="text-gray-400 text-xs">已为您生成 5 条高频面试题...</p>
                        </div>
                      </div>
                      <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div class="w-[80%] h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 底部边框（带下吧和Home键） -->
              <div class="h-10 bg-white/[0.02] border-t border-white/[0.05] flex items-center justify-center">
                <div class="flex items-center gap-1.5 opacity-80">
                  <span class="h-1 w-8 rounded-full bg-cyan-500/30 shadow-[0_0_8px_rgba(34,211,238,0.25)]"></span>
                  <span class="h-1 w-3 rounded-full bg-cyan-500/30 shadow-[0_0_8px_rgba(34,211,238,0.25)]"></span>
                  <span class="h-1 w-6 rounded-full bg-cyan-500/30 shadow-[0_0_8px_rgba(34,211,238,0.25)]"></span>
                  <span class="h-1 w-2 rounded-full bg-purple-500/30 shadow-[0_0_8px_rgba(168,85,247,0.25)]"></span>
                </div>
              </div>
            </div>
            <div class="absolute -bottom-16 left-1/2 -translate-x-1/2 w-[80%] h-16 flex flex-col items-center pointer-events-none z-0">
              <div class="w-full h-[2px] bg-cyan-300 shadow-[0_0_30px_rgba(34,211,238,1)] rounded-[100%]"></div>
              <div class="w-[70%] h-full bg-gradient-to-t from-cyan-400/40 to-transparent blur-xl"></div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 底部 Footer -->
    <footer class="relative z-10 py-8 text-center text-xs text-gray-600">
      © 2026 Designed & Developed by Moyingjun 广东水利电力职业技术学院
    </footer>

    <div class="absolute inset-0 z-[1] pointer-events-none opacity-[0.03] mix-blend-overlay" style="background-image: url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E');"></div>
  </div>
</template>

<style scoped>
.glass-card {
  transition: all 0.3s ease;
}

.smoke-canvas {
  width: 100%;
  height: 100%;
  display: block;
  background: #020205;
}

.orb-wrapper-x {
  position: absolute;
  top: 0;
  left: 0;
  width: var(--orb-size);
  height: var(--orb-size);
  will-change: transform;
}

.orb-inner-y {
  position: absolute;
  inset: 0;
  width: var(--orb-size);
  height: var(--orb-size);
  border-radius: 9999px;
  filter: blur(var(--orb-blur));
  will-change: transform;
}

.orb-1-x {
  --orb-size: 600px;
  --orb-blur: 120px;
  animation: dvd-x-1 13s linear infinite alternate;
}

.orb-1-y {
  animation: dvd-y-1 17s linear infinite alternate;
}

.orb-2-x {
  --orb-size: 500px;
  --orb-blur: 120px;
  animation: dvd-x-2 15s linear infinite alternate-reverse;
}

.orb-2-y {
  animation: dvd-y-2 19s linear infinite alternate;
}

.orb-3-x {
  --orb-size: 700px;
  --orb-blur: 150px;
  animation: dvd-x-3 21s linear infinite alternate;
}

.orb-3-y {
  animation: dvd-y-3 16s linear infinite alternate-reverse;
}

.parallax-stars {
  opacity: 0.4;
  mix-blend-mode: screen;
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.82) 0 1px, transparent 1.4px),
    radial-gradient(circle, rgba(191, 219, 254, 0.72) 0 1.2px, transparent 1.7px),
    radial-gradient(circle, rgba(232, 121, 249, 0.62) 0 1.5px, transparent 2px),
    radial-gradient(circle, rgba(255, 255, 255, 0.55) 0 0.8px, transparent 1.2px);
  background-position: 18px 22px, 78px 112px, 142px 64px, 210px 178px;
  background-size: 180px 220px, 260px 300px, 340px 380px, 120px 160px;
  animation: star-twinkle 6s ease-in-out infinite;
}

.meteor {
  position: absolute;
  width: 240px;
  height: 1px;
  border-radius: 9999px;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(34,211,238,0.2) 60%, rgba(255,255,255,1) 100%);
  box-shadow: 0 0 14px rgba(125, 211, 252, 0.75), 0 0 32px rgba(168, 85, 247, 0.25);
  transform: rotate(-28deg) translate3d(0, 0, 0);
  opacity: 0;
  will-change: transform, opacity;
}

.meteor::before {
  content: '';
  position: absolute;
  right: -2px;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 0 15px 3px rgba(34,211,238,0.8);
  transform: translateY(-50%);
}

.meteor-1 {
  top: 14%;
  left: -18%;
  animation: meteor-shoot 7.5s ease-in-out infinite;
}

.meteor-2 {
  top: 36%;
  left: -24%;
  width: 190px;
  animation: meteor-shoot 10s ease-in-out 2.2s infinite;
}

.meteor-3 {
  top: 62%;
  left: -20%;
  width: 280px;
  animation: meteor-shoot 12s ease-in-out 4.8s infinite;
}

.meteor-4 {
  top: 24%;
  left: -26%;
  width: 165px;
  animation: meteor-shoot 9s ease-in-out 6.2s infinite;
}

.animate-orb-breathe {
  animation: orb-breathe 8s ease-in-out infinite;
  transform-origin: center;
  will-change: transform, scale, filter, opacity;
}

@keyframes orb-breathe {
  0%, 100% { scale: 1; filter: hue-rotate(0deg); opacity: 0.8; }
  50% { scale: 1.1; filter: hue-rotate(15deg); opacity: 1; }
}

@keyframes dvd-x-1 {
  0% { transform: translate3d(-180px, 0, 0); }
  100% { transform: translate3d(calc(100vw - 420px), 0, 0); }
}

@keyframes dvd-y-1 {
  0% { transform: translate3d(0, -170px, 0); }
  100% { transform: translate3d(0, calc(100vh - 430px), 0); }
}

@keyframes dvd-x-2 {
  0% { transform: translate3d(-120px, 0, 0); }
  100% { transform: translate3d(calc(100vw - 380px), 0, 0); }
}

@keyframes dvd-y-2 {
  0% { transform: translate3d(0, 10vh, 0); }
  100% { transform: translate3d(0, calc(100vh - 360px), 0); }
}

@keyframes dvd-x-3 {
  0% { transform: translate3d(-240px, 0, 0); }
  100% { transform: translate3d(calc(100vw - 460px), 0, 0); }
}

@keyframes dvd-y-3 {
  0% { transform: translate3d(0, -220px, 0); }
  100% { transform: translate3d(0, calc(100vh - 480px), 0); }
}

@keyframes star-twinkle {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

@keyframes meteor-shoot {
  0%, 72% {
    opacity: 0;
    transform: rotate(-28deg) translate3d(0, 0, 0);
  }
  76% {
    opacity: 1;
  }
  90% {
    opacity: 0.9;
  }
  100% {
    opacity: 0;
    transform: rotate(-28deg) translate3d(145vw, 78vh, 0);
  }
}

/* 电影级模糊显现入场动画 */
/* 修复后的全息扫描线动画 */
@keyframes hologram-scan {
  0% { top: 0%; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

.animate-hologram-scan {
  animation: hologram-scan 10s linear infinite;
}

@keyframes terminal-dot-pulse {
  0%, 100% { opacity: 0.25; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.6); }
}

.animate-terminal-dot {
  animation: terminal-dot-pulse 1.6s ease-in-out infinite;
}

@keyframes blurInUp {
  from { opacity: 0; transform: translateY(30px); filter: blur(10px); }
  to { opacity: 1; transform: translateY(0); filter: blur(0); }
}

.animate-blur-in-up {
  animation: blurInUp 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

/* 两段式多行打字机 */
@keyframes typing {
  from { max-width: 0; }
  to { max-width: 100%; }
}

@keyframes showNextLine {
  to { opacity: 1; }
}

@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.animate-typewriter-1 {
  display: inline-block;
  max-width: 0;
  /* 1.2s 敲完第一行 */
  animation: typing 1.2s steps(4) forwards;
}

.animate-typewriter-2 {
  display: inline-flex;
  max-width: 0;
  /* 延迟 1.2s 等第一行敲完，再用 1.8s 敲第二行 */
  animation: showNextLine 0.1s 1.2s forwards, typing 1.8s steps(7) 1.2s forwards;
}

.animate-cursor-blink {
  animation: cursorBlink 1s step-end infinite;
}

/* 丝滑入场动画关键帧 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(40px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 入场动画类 */
.animate-fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

.animate-fade-in-right {
  animation: fadeInRight 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

/* 动画延迟工具类 */
.animation-delay-300 { animation-delay: 0.3s; }
.animation-delay-400 { animation-delay: 0.4s; }
.animation-delay-500 { animation-delay: 0.5s; }

@keyframes float {
  0%, 100% { transform: translateY(0) perspective(1000px) rotateY(-5deg); }
  50% { transform: translateY(-15px) perspective(1000px) rotateY(-5deg); }
}

@keyframes gradient-flow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.animate-float { 
  animation: float 6s ease-in-out infinite; 
}
.animate-float-1 { animation: float 6s ease-in-out infinite; }
.animate-float-2 { animation: float 7s ease-in-out infinite; animation-delay: -2s; }
.animate-float-3 { animation: float 8s ease-in-out infinite; animation-delay: -4s; }

.animate-text-glow {
  background-size: 200% auto;
  animation: gradient-flow 4s linear infinite;
}

/* 粒子动画 */
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.5); }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
