<script setup>
/**
 * Toast 渲染容器。挂在 App.vue 根部一次，全站共用。
 *
 * 无障碍要点：
 *   - 容器 aria-live="polite"：普通提示排队念，不打断用户
 *   - 错误项 role="alert"：自带 assertive，会立刻打断 —— 这是有意的，
 *     答案提交失败而用户没听到，他会以为已经提交了
 */
import { useToast } from '@/composables/useToast'

defineOptions({ name: 'AppToast' })

const { toasts, toast } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast">
        <div
          v-for="item in toasts"
          :key="item.id"
          class="toast"
          :class="`toast--${item.type}`"
          :role="item.type === 'error' ? 'alert' : 'status'"
        >
          <div class="toast__body">
            <p class="toast__message">{{ item.message }}</p>
            <p v-if="item.detail" class="toast__detail">{{ item.detail }}</p>
          </div>
          <button class="toast__close" type="button" aria-label="关闭提示" @click="toast.dismiss(item.id)">
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path
                d="M6 6l12 12M18 6L6 18"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: var(--space-5);
  /* 避开 iPhone 的底部手势条 */
  bottom: calc(var(--space-5) + env(safe-area-inset-bottom, 0px));
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: min(92vw, 380px);
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--muted);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  /* 容器整体 pointer-events:none，避免遮挡下面的按钮；
     单条 toast 再开回来，这样关闭按钮可点 */
  pointer-events: auto;
}

.toast--info {
  border-left-color: var(--primary);
}

.toast--success {
  border-left-color: var(--success);
}

.toast--error {
  border-left-color: var(--danger);
}

.toast__body {
  flex: 1;
  min-width: 0;
}

.toast__message {
  font-size: var(--text-sm);
  line-height: 1.5;
}

.toast__detail {
  margin-top: var(--space-1);
  color: var(--muted);
  font-family: 'Consolas', monospace;
  font-size: var(--text-2xs);
  word-break: break-all;
}

.toast__close {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--faint);
}

.toast__close:hover {
  background: var(--surface-2);
  color: var(--ink);
}

/* 进场从右侧滑入，退场淡出 */
.toast-enter-active,
.toast-leave-active {
  transition:
    transform var(--dur-base) var(--ease),
    opacity var(--dur-base) var(--ease);
}

.toast-enter-from,
.toast-leave-to {
  transform: translateX(12px);
  opacity: 0;
}

@media (max-width: 640px) {
  .toast-stack {
    right: var(--space-3);
    left: var(--space-3);
    width: auto;
  }
}
</style>
