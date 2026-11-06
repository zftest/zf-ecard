<script setup>
/**
 * 标签胶囊。
 *
 * 有两种语义，**不能混用**，混用是筛选器最常见的无障碍错误：
 *   - 可多选筛选 → selectable，渲染成 role="checkbox" 的 button
 *   - 只读状态标记 → 渲染成 span（"已掌握""错 3 次"这类）
 *
 * 为什么不统一用 button：一个不能点的东西做成 button，
 * 读屏会念"按钮"，键盘能 Tab 到它，用户按下去没反应 —— 徒增噪音。
 */
import { computed } from 'vue'

defineOptions({ name: 'AppChip' })

const props = defineProps({
  selectable: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
  tone: {
    type: String,
    default: 'neutral',
    validator: (v) => ['neutral', 'primary', 'success', 'danger', 'warning'].includes(v),
  },
  size: { type: String, default: 'md', validator: (v) => ['md', 'sm'].includes(v) },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:selected', 'click'])

const tag = computed(() => (props.selectable ? 'button' : 'span'))

function onClick(event) {
  if (!props.selectable || props.disabled) return
  emit('update:selected', !props.selected)
  emit('click', event)
}
</script>

<template>
  <component
    :is="tag"
    :type="props.selectable ? 'button' : undefined"
    :class="[
      'chip',
      `chip--${props.tone}`,
      `chip--${props.size}`,
      { 'chip--selectable': props.selectable, 'chip--selected': props.selected },
    ]"
    :role="props.selectable ? 'checkbox' : undefined"
    :aria-checked="props.selectable ? props.selected : undefined"
    :aria-disabled="props.selectable && props.disabled ? 'true' : undefined"
    :disabled="props.selectable ? props.disabled : undefined"
    @click="onClick"
  >
    <slot />
  </component>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  font-size: var(--text-sm);
  line-height: 1;
  white-space: nowrap;
}

.chip--md {
  /* 36 + 4 + 4 = 44，命中区刚好达标；34 就凑不出来了 */
  min-height: 36px;
  padding: 0 var(--space-3);
}

.chip--sm {
  min-height: 22px;
  padding: 0 var(--space-2);
  font-size: var(--text-xs);
}

/* ── 只读态（span）───────────────────── */
.chip--neutral {
  background: var(--surface-2);
  color: var(--muted);
}

.chip--primary {
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.chip--success {
  background: var(--success-soft);
  color: var(--success);
}

.chip--danger {
  background: var(--danger-soft);
  color: var(--danger);
}

.chip--warning {
  background: var(--warning-soft);
  color: var(--warning);
}

/* ── 可选中态（button）────────────────── */
.chip--selectable {
  position: relative;
  background: var(--surface);
  border-color: var(--border);
  color: var(--muted);
  cursor: pointer;
  transition:
    background var(--dur-base) var(--ease),
    border-color var(--dur-base) var(--ease),
    color var(--dur-base) var(--ease);
}

.chip--selectable:hover:not(:disabled) {
  border-color: var(--border-strong);
  color: var(--ink);
}

/* 选中用"实心 + 白字"而不是加粗：
   加粗会让宽度跳动，整排标签跟着位移，点第二个时手指对不上 */
.chip--selectable.chip--selected {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--on-primary);
}

.chip--selectable:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

/* 视觉 36px 的胶囊在平板上偏小，撑到 44px 命中区（同 AppButton 的做法）。

   扩展量必须和 chip 行间距对齐：相邻两行之间的 gap 是 --space-2 (8px)，
   上下各扩 4px 刚好填满、不重叠。如果扩 5px，两行会重叠 2px ——
   点上一行的下半部分会触发下一行的 chip，这种错点极难复现、极难归因。 */
.chip--md.chip--selectable::after {
  content: '';
  position: absolute;
  inset: -4px -2px;
  border-radius: inherit;
}
</style>
