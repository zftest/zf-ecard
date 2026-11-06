<script setup>
/**
 * 对话框。
 *
 * 用原生 <dialog> + showModal()，不自己实现遮罩层。原因是原生实现的
 * 三件事自己写都容易写错：
 *   1. 焦点陷阱（Tab 不会跑到背后的页面）
 *   2. 打开时把背景内容标记为 inert（读屏不会读到背后的按钮）
 *   3. 关闭后把焦点还给打开它的那个元素
 *
 * 代价是不支持 IE —— 本项目面向现代浏览器，可接受。
 */
import { onMounted, ref, useId, watch } from 'vue'

defineOptions({ name: 'AppDialog' })

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  size: { type: String, default: 'md', validator: (v) => ['sm', 'md'].includes(v) },
  closeOnBackdrop: { type: Boolean, default: true },
  closeOnEsc: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'close'])

const dialogRef = ref(null)
const titleId = `dlg-${useId()}`
const descId = `dlg-desc-${useId()}`

function syncOpen(open) {
  const el = dialogRef.value
  if (!el) return
  if (open && !el.open) {
    el.showModal()
  } else if (!open && el.open) {
    el.close()
  }
}

// flush: 'post' 保证 DOM 已经挂载/更新完再操作 dialog
watch(() => props.modelValue, syncOpen, { flush: 'post' })
onMounted(() => syncOpen(props.modelValue))

function close() {
  emit('update:modelValue', false)
  emit('close')
}

/** ESC：原生会先派发 cancel 事件，这里可以拦下来 */
function onCancel(event) {
  if (!props.closeOnEsc) {
    event.preventDefault()
    return
  }
  // 不 preventDefault，让浏览器关闭 dialog，close 事件里再同步 v-model；
  // 这样动画/焦点还原都走原生路径
}

/** 点遮罩关闭。点内容和点遮罩的区分依据：target 是不是 dialog 元素本身。 */
function onClick(event) {
  if (!props.closeOnBackdrop) return
  if (event.target !== dialogRef.value) return
  close()
}

/** 原生关闭（ESC / 表单 method=dialog）后同步回 v-model */
function onNativeClose() {
  if (props.modelValue) close()
}
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialogRef"
      class="dlg"
      :class="`dlg--${props.size}`"
      :aria-labelledby="props.title ? titleId : undefined"
      :aria-describedby="props.description ? descId : undefined"
      @cancel="onCancel"
      @close="onNativeClose"
      @click="onClick"
    >
      <div class="dlg__panel">
        <header v-if="props.title" class="dlg__head">
          <h2 :id="titleId" class="dlg__title">{{ props.title }}</h2>
          <button class="dlg__close" type="button" aria-label="关闭" @click="close">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                d="M6 6l12 12M18 6L6 18"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </header>

        <p v-if="props.description" :id="descId" class="dlg__desc">{{ props.description }}</p>

        <div class="dlg__body"><slot /></div>

        <footer v-if="$slots.footer" class="dlg__foot"><slot name="footer" /></footer>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.dlg {
  /* 清掉浏览器默认的 padding/border/max-width，全部自己控制 */
  padding: 0;
  border: 0;
  background: transparent;
  max-width: min(92vw, 560px);
  width: 100%;
  color: var(--ink);
}

.dlg--sm {
  max-width: min(92vw, 420px);
}

.dlg::backdrop {
  background: rgba(32, 36, 31, 0.42);
  backdrop-filter: blur(2px);
}

.dlg__panel {
  padding: var(--space-5);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.dlg__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}

.dlg__title {
  font-size: var(--text-xl);
}

.dlg__close {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  /* 图标视觉 18px，但按钮本身要达到 44px 才好点 */
  width: var(--tap-min);
  height: var(--tap-min);
  margin: calc(var(--space-2) * -1) calc(var(--space-2) * -1) 0 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--muted);
  transition: background var(--dur-fast) var(--ease);
}

.dlg__close:hover {
  background: var(--surface-2);
  color: var(--ink);
}

.dlg__desc {
  margin-bottom: var(--space-3);
  color: var(--muted);
  font-size: var(--text-sm);
}

.dlg__body {
  max-height: min(64vh, 520px);
  overflow-y: auto;
}

.dlg__foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-5);
}
</style>
