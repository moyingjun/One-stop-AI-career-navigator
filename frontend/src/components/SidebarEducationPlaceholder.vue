<script setup>
/**
 * 侧边栏「升学」disabled 占位项
 *
 * 职责：
 * - 在 Resume / Career / Interview 三页所共享的侧边栏区域中渲染同款占位
 * - 始终为禁用态，不响应点击与键盘激活
 * - 文案以组件内部常量写死，避免文案漂移
 * - 不向 Vue Router 注册任何新路由，不触发跳转
 *
 * Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 5.3, 5.4
 */
import { GraduationCap } from 'lucide-vue-next'

// 组件内部常量：文案写死，禁止从 props 传入
const PLACEHOLDER_LABEL = '升学'
const PLACEHOLDER_TEXT = '工程师正在玩命开发中，敬请期待！🚀'
</script>

<template>
  <div class="sidebar-education-placeholder">
    <div
      class="placeholder-item"
      role="button"
      aria-disabled="true"
      tabindex="-1"
      :title="PLACEHOLDER_TEXT"
      :aria-label="`${PLACEHOLDER_LABEL}：${PLACEHOLDER_TEXT}`"
      data-test="sidebar-education-placeholder"
      @click.prevent
    >
      <span class="placeholder-icon-wrap">
        <GraduationCap class="placeholder-icon" :size="18" aria-hidden="true" />
      </span>
      <span class="placeholder-label" data-test="sidebar-education-label">{{ PLACEHOLDER_LABEL }}</span>
      <span class="placeholder-badge">即将上线</span>

      <!-- 同区域内联 tooltip：hover 时通过 CSS 显示，与 title 属性双保险 -->
      <span
        class="placeholder-tooltip"
        role="tooltip"
        data-test="sidebar-education-tooltip"
      >
        {{ PLACEHOLDER_TEXT }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.sidebar-education-placeholder {
  width: 100%;
}

.placeholder-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border-radius: 12px;
  /* 暗黑赛博毛玻璃容器 */
  background: rgba(10, 10, 20, 0.55);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(16, 185, 129, 0.2);
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.08), 0 4px 30px rgba(0, 0, 0, 0.3);
  /* 禁用态视觉与交互 */
  opacity: 0.65;
  cursor: not-allowed;
  user-select: none;
  outline: none;
  transition: opacity 200ms ease-out, box-shadow 200ms ease-out;
}

.placeholder-item:hover {
  /* 悬停略微提亮，但仍保持禁用质感 */
  opacity: 0.8;
  box-shadow: 0 0 30px rgba(16, 185, 129, 0.15), 0 4px 30px rgba(0, 0, 0, 0.35);
}

.placeholder-item:focus,
.placeholder-item:focus-visible {
  outline: none;
}

.placeholder-icon-wrap {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.placeholder-icon {
  color: rgb(110, 231, 183); /* emerald-300 */
}

.placeholder-label {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: rgb(167, 243, 208); /* emerald-200 */
  letter-spacing: 0.02em;
}

.placeholder-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  color: rgb(110, 231, 183);
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 999px;
  white-space: nowrap;
}

/* 同区域内联 tooltip —— 默认不可见，hover 时滑入显现 */
.placeholder-tooltip {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 6px);
  z-index: 20;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.4;
  color: rgb(209, 250, 229); /* emerald-100 */
  background: rgba(6, 27, 22, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(16, 185, 129, 0.35);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), 0 0 20px rgba(16, 185, 129, 0.15);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transition: opacity 180ms ease-out, transform 180ms ease-out, visibility 180ms ease-out;
  pointer-events: none;
  white-space: normal;
  word-break: break-word;
}

.placeholder-item:hover .placeholder-tooltip,
.placeholder-item:focus-visible .placeholder-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

/* prefers-reduced-motion 无障碍降级 */
@media (prefers-reduced-motion: reduce) {
  .placeholder-item,
  .placeholder-tooltip {
    transition: none;
  }
}

/* 移动端：减小内边距 */
@media (max-width: 767px) {
  .placeholder-item {
    padding: 8px 12px;
    border-radius: 10px;
  }
  .placeholder-tooltip {
    font-size: 11px;
    padding: 6px 10px;
  }
}
</style>
