<script setup>
/**
 * 进度条。
 *
 * 用具名 role="progressbar" + aria-valuenow，而不是画一个 div 标个宽度：
 * 读屏用户靠 aria 值知道"做了 3/20"，纯视觉的进度条对他完全不可见。
 */
import { computed } from 'vue'

defineOptions({ name: 'AppProgressBar' })

const props = defineProps({
  value: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  tone: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'success', 'danger'].includes(v),
  },
  size: { type: String, default: 'md', validator: (v) => ['sm', 'md'].includes(v) },
  /** 不确定进度（比如还在解析文件）时不显示百分比 */
  indeterminate: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

const percent = computed(() => {
  if (props.max <= 0) return 0
  const ratio = (props.value / props.max) * 100
  return Math.min(100, Math.max(0, Math.round(ratio)))
})

const style = computed(() => ({ width: `${percent.value}%` }))
</script>

<template>
  <div class="bar-wrap">
    <div
      v-if="props.label"
      class="bar-meta"
    >
      <span>{{ props.label }}</span>
      <span v-if="!props.indeterminate" class="tabular">{{ props.value }} / {{ props.max }}</span>
    </div>

    <div
      class="bar"
      :class="[`bar--${props.size}`, { 'bar--indeterminate': props.indeterminate }]"
      role="progressbar"
      :aria-valuenow="props.indeterminate ? undefined : props.value"
      :aria-valuemin="props.indeterminate ? undefined : 0"
      :aria-valuemax="props.indeterminate ? undefined : props.max"
      :aria-label="props.label || undefined"
    >
      <span class="bar__fill" :class="`bar__fill--${props.tone}`" :style="style" />
    </div>
  </div>
</template>

<style scoped>
.bar-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}

.bar-meta {
  display: flex;
  justify-content: space-between;
  color: var(--muted);
  font-size: var(--text-xs);
}

.bar {
  position: relative;
  overflow: hidden;
  width: 100%;
  background: var(--surface-3);
  border-radius: var(--radius-pill);
}

.bar--sm {
  height: 4px;
}

.bar--md {
  height: 8px;
}

.bar__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  transition: width var(--dur-slow) var(--ease);
}

.bar__fill--primary {
  background: var(--primary);
}

.bar__fill--success {
  background: var(--success);
}

.bar__fill--danger {
  background: var(--danger);
}

/* 宽度从 0 跳到 100% 再回 0，表示"不知道还要多久" */
.bar--indeterminate .bar__fill {
  width: 40% !important;
  animation: bar-slide 1.2s ease-in-out infinite;
}

@keyframes bar-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(260%);
  }
}
</style>
