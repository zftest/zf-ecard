<script setup>
/**
 * 按钮。
 *
 * 用原生 <button>，不自己造 div：键盘 Enter/Space、焦点管理、
 * 表单提交、屏幕阅读器的"按钮"角色全都是原生白送的。
 */
defineOptions({ name: 'AppButton' })

const props = defineProps({
  /** primary：页面主操作，一个区域只应有一个；text：低权重的"返回""跳过" */
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'ghost', 'text', 'danger'].includes(v),
  },
  /** sm 的视觉高度是 36px，但命中区会被伪元素扩到 44px（见样式说明） */
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['md', 'sm'].includes(v),
  },
  block: { type: Boolean, default: false },
  /** 加载中：同时禁用点击，防止连点提交两次答案 */
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
})
</script>

<template>
  <button
    :type="props.type"
    :class="[
      'btn',
      `btn--${props.variant}`,
      `btn--${props.size}`,
      { 'btn--block': props.block, 'btn--loading': props.loading },
    ]"
    :disabled="props.disabled || props.loading"
    :aria-busy="props.loading || undefined"
  >
    <span v-if="props.loading" class="btn__spinner" aria-hidden="true" />
    <span class="btn__label"><slot /></span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: var(--tap-min);
  padding: 0 var(--space-5);
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  line-height: 1;
  white-space: nowrap;
  transition:
    background var(--dur-base) var(--ease),
    border-color var(--dur-base) var(--ease),
    transform var(--dur-fast) var(--ease);
}

.btn:active:not(:disabled) {
  transform: translateY(1px);
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* 加载态保留不透明：按钮变灰会让人以为点坏了，
   真正需要的信号是"转圈 + 点不动" */
.btn--loading:disabled {
  opacity: 1;
  cursor: progress;
}

.btn__label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: btn-spin 640ms linear infinite;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── 变体 ─────────────────────────────── */
.btn--primary {
  background: var(--primary);
  color: var(--on-primary);
}

.btn--primary:hover:not(:disabled) {
  background: var(--primary-dark);
}

.btn--secondary {
  background: var(--surface);
  border-color: var(--border-strong);
  color: var(--ink);
}

.btn--secondary:hover:not(:disabled) {
  background: var(--surface-2);
}

.btn--ghost {
  background: transparent;
  border-color: var(--border);
  color: var(--muted);
}

.btn--ghost:hover:not(:disabled) {
  border-color: var(--border-strong);
  color: var(--ink);
}

.btn--text {
  min-height: var(--tap-min);
  padding: 0 var(--space-2);
  background: transparent;
  color: var(--primary);
  font-weight: var(--weight-normal);
}

.btn--text:hover:not(:disabled) {
  color: var(--primary-dark);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.btn--danger {
  background: var(--danger-soft);
  color: var(--danger);
}

.btn--danger:hover:not(:disabled) {
  background: #f2d9d3;
}

/* ── 尺寸 ─────────────────────────────── */
.btn--block {
  display: flex;
  width: 100%;
}

/*
  sm 用于表格行内、标签旁这类密集区域。
  视觉上 36px 才不臃肿，但 36px 在平板上很容易点空，
  所以用伪元素把可点击区域上下各撑 4px 到 44px ——
  视觉不变，命中区达标。伪元素属于 <button> 自身，
  点它和点按钮触发的是同一个 click。
*/
.btn--sm {
  position: relative;
  min-height: 36px;
  padding: 0 var(--space-4);
  font-size: var(--text-sm);
}

.btn--sm::after {
  content: '';
  position: absolute;
  inset: -4px 0;
  border-radius: inherit;
}
</style>
