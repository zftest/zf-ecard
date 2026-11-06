<script setup>
/**
 * 页面占位（B6 阶段用，B7 逐个替换成真实页面）。
 *
 * 不做成一句"敬请期待"，而是把这一页**要实现什么、依赖哪些接口**
 * 直接写在界面上 —— B7 开工时对着它就能拆任务，不用回去翻 PRD。
 */
import { RouterLink } from 'vue-router'

import AppButton from '@/components/AppButton.vue'
import AppCard from '@/components/AppCard.vue'

defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  summary: { type: String, default: '' },
  /** 待实现的功能点 */
  points: { type: Array, default: () => [] },
  /** 依赖的接口，如 'GET /api/v1/words' */
  apis: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="stub">
    <AppCard :eyebrow="eyebrow" :title="title" :heading-level="2">
      <p v-if="summary" class="stub__summary">{{ summary }}</p>

      <div v-if="points.length" class="stub__block">
        <p class="stub__label">这一页要做的事</p>
        <ol class="stub__list">
          <li v-for="(point, i) in points" :key="i">
            <span class="stub__num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
            <span>{{ point }}</span>
          </li>
        </ol>
      </div>

      <div v-if="apis.length" class="stub__block">
        <p class="stub__label">依赖接口</p>
        <ul class="stub__apis">
          <li v-for="apiPath in apis" :key="apiPath"><code>{{ apiPath }}</code></li>
        </ul>
      </div>

      <template #footer>
        <div class="stub__foot">
          <span class="stub__status">B7 实现</span>
          <RouterLink to="/"><AppButton variant="text" size="sm">回学习首页</AppButton></RouterLink>
        </div>
      </template>
    </AppCard>
  </div>
</template>

<style scoped>
.stub {
  max-width: 760px;
}

.stub__summary {
  margin-bottom: var(--space-5);
  color: var(--muted);
}

.stub__block + .stub__block {
  margin-top: var(--space-5);
}

.stub__label {
  margin-bottom: var(--space-3);
  color: var(--faint);
  font-size: var(--text-2xs);
  letter-spacing: 0.16em;
}

.stub__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.stub__list li {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.stub__num {
  flex-shrink: 0;
  color: var(--faint);
  font-family: 'Consolas', monospace;
  font-size: var(--text-xs);
}

.stub__apis {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.stub__apis code {
  display: inline-block;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--muted);
  font-family: 'Consolas', monospace;
  font-size: var(--text-xs);
}

.stub__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stub__status {
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--warning-soft);
  color: var(--warning);
  font-size: var(--text-2xs);
  letter-spacing: 0.08em;
}
</style>
