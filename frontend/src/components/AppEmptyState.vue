<script setup>
/**
 * 空状态。
 *
 * 空白页是最容易被忽略、也最伤人的界面：
 * 孩子打开错词本一片空白，他不知道是"没有错词"还是"加载失败"。
 * 所以空状态必须写清楚**为什么空**以及**下一步做什么**。
 */
defineOptions({ name: 'AppEmptyState' })

const props = defineProps({
  /** 图标位置的短标记，如 ✓ / 0 / PDF */
  mark: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div class="empty" :class="{ 'empty--compact': props.compact }">
    <span v-if="props.mark" class="empty__mark" aria-hidden="true">{{ props.mark }}</span>
    <h3 class="empty__title">{{ props.title }}</h3>
    <p v-if="props.description" class="empty__desc">{{ props.description }}</p>
    <div v-if="$slots.default" class="empty__actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-5);
  text-align: center;
}

.empty--compact {
  padding: var(--space-6) var(--space-4);
}

.empty__mark {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: var(--space-2);
  border-radius: 50%;
  background: var(--surface-2);
  color: var(--muted);
  font-family: var(--font-display);
  font-size: var(--text-lg);
}

.empty__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-medium);
}

.empty__desc {
  max-width: 34em;
  color: var(--muted);
  font-size: var(--text-sm);
}

.empty__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
}
</style>
