<script setup>
/**
 * 学习首页。
 *
 * B6 阶段这一页的职责是**证明整条链路是通的**：
 * axios → Flask /api/v1 → SQLite，数据真的进了组件。
 * 所以它读的是真实接口，不是 mock。
 *
 * 视觉上遵循原型的"学习桌"气质：暖纸底、一个钴蓝主色、
 * 英文单词用衬线体。首页不放花哨图表 —— 孩子打开它只想知道
 * "今天写了几个、还差几个、现在该点哪个按钮"。
 */
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppButton from '@/components/AppButton.vue'
import AppCard from '@/components/AppCard.vue'
import AppChip from '@/components/AppChip.vue'
import AppProgressBar from '@/components/AppProgressBar.vue'
import { getHealth } from '@/api/system'
import { useLearnerStore } from '@/stores/learner'

const learner = useLearnerStore()

const health = ref(null)
const healthError = ref('')

/** 0.8023 → "80%"；null → "—"（还没答过题，正确率没有意义，不能显示 0%） */
function percent(value) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}

const distribution = [
  { key: 'learning', label: '学习中', tone: 'primary' },
  { key: 'reviewing', label: '复习中', tone: 'warning' },
  { key: 'mastered', label: '已掌握', tone: 'success' },
  { key: 'wrongbook', label: '错词本', tone: 'danger' },
]

onMounted(async () => {
  try {
    health.value = await getHealth()
  } catch (err) {
    healthError.value = err?.normalized?.message || '后端未连接'
  }
})
</script>

<template>
  <div class="dash">
    <!-- 后端不可用：给一句能看懂的话 + 一个可执行的动作，
         而不是让页面空在那里让人以为"没数据" -->
    <AppCard v-if="learner.error && !learner.profile" tone="muted">
      <div class="offline">
        <h2 class="offline__title">暂时连不上词库服务</h2>
        <p class="offline__desc">{{ learner.error }}</p>
        <AppButton :loading="learner.loading" @click="learner.refresh()">重试</AppButton>
      </div>
    </AppCard>

    <template v-else>
      <!-- 今日任务 -->
      <section class="hero">
        <div class="hero__main">
          <p class="hero__eyebrow">今日任务</p>
          <h2 class="hero__title">
            <template v-if="learner.todayDone">
              今天已经写了 <em>{{ learner.todayDone }}</em> 个词
            </template>
            <template v-else>今天还没有开始</template>
          </h2>
          <p class="hero__meta">
            目标 {{ learner.todayGoal }} 个 · 完成度 {{ percent(learner.goalRatio) }}
            <template v-if="learner.wrongCount">
              · 错词本里有 {{ learner.wrongCount }} 个词等着复习
            </template>
          </p>

          <AppProgressBar
            class="hero__progress"
            :value="learner.todayDone"
            :max="learner.todayGoal"
          />

          <div class="hero__actions">
            <RouterLink to="/config"><AppButton>开始默写</AppButton></RouterLink>
            <RouterLink to="/words"><AppButton variant="secondary">浏览词库</AppButton></RouterLink>
          </div>
        </div>

        <div class="hero__stats">
          <div class="stat">
            <strong class="tabular">{{ percent(learner.todayAccuracy) }}</strong>
            <span>今日正确率</span>
          </div>
          <div class="stat">
            <strong class="tabular">{{ learner.streakDays }}</strong>
            <span>连续练习天数</span>
          </div>
        </div>
      </section>

      <div class="grid">
        <!-- 学习分布 -->
        <AppCard eyebrow="PROGRESS" title="词汇掌握分布">
          <ul class="dist">
            <li v-for="item in distribution" :key="item.key" class="dist__row">
              <AppChip :tone="item.tone" size="sm">{{ item.label }}</AppChip>
              <span class="dist__value tabular">{{ learner.totals[item.key] ?? 0 }}</span>
            </li>
          </ul>
          <p class="dist__note">
            按「词」统计，不是按练习次数。一个词有多个义项也只算一个。
          </p>
        </AppCard>

        <!-- 快捷入口 -->
        <AppCard eyebrow="SHORTCUTS" title="接着做什么">
          <div class="links">
            <RouterLink to="/config" class="link">
              <span class="link__index" aria-hidden="true">01</span>
              <span class="link__body">
                <strong>分类默写</strong>
                <small>汉译英 / 听音写词 / 英译汉 / 音标写词</small>
              </span>
            </RouterLink>
            <RouterLink to="/wrongbook" class="link">
              <span class="link__index" aria-hidden="true">02</span>
              <span class="link__body">
                <strong>错词复习</strong>
                <small>按到期时间排序，先练最该练的</small>
              </span>
            </RouterLink>
            <RouterLink to="/words" class="link">
              <span class="link__index" aria-hidden="true">03</span>
              <span class="link__body">
                <strong>单词库</strong>
                <small>搜索、筛选、听发音、看义项</small>
              </span>
            </RouterLink>
          </div>
        </AppCard>
      </div>

      <!-- 工程自检：B6 的验收点，证明前端确实连到了后端 -->
      <AppCard eyebrow="SYSTEM" title="服务状态" padding="compact">
        <div class="health">
          <template v-if="health">
            <AppChip tone="success" size="sm">已连接</AppChip>
            <span class="health__item">版本 <b>{{ health.version }}</b></span>
            <span class="health__item">词库 <b class="tabular">{{ health.words_count }}</b> 个词</span>
            <span class="health__item">数据库 <b>{{ health.database }}</b></span>
          </template>
          <template v-else-if="healthError">
            <AppChip tone="danger" size="sm">未连接</AppChip>
            <span class="health__item">{{ healthError }}</span>
          </template>
          <template v-else>
            <AppChip size="sm">检查中</AppChip>
          </template>
        </div>
      </AppCard>
    </template>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: var(--content-max);
}

/* ── 今日任务 ─────────────────────────────── */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-6);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.hero__main {
  flex: 1;
  min-width: 0;
}

.hero__eyebrow {
  color: var(--faint);
  font-size: var(--text-2xs);
  letter-spacing: 0.18em;
}

.hero__title {
  margin-top: var(--space-2);
  font-size: var(--text-2xl);
  letter-spacing: -0.01em;
}

/* 数字用衬线体强调，和英文单词同一套字体 —— 视觉上把"数量"和"内容"归为一类 */
.hero__title em {
  font-family: var(--font-display);
  font-style: normal;
  font-size: 1.15em;
  color: var(--primary);
}

.hero__meta {
  margin-top: var(--space-2);
  color: var(--muted);
  font-size: var(--text-sm);
}

.hero__progress {
  margin-top: var(--space-4);
  max-width: 420px;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-5);
}

.hero__stats {
  display: flex;
  flex-shrink: 0;
  gap: var(--space-6);
  padding-left: var(--space-6);
  border-left: 1px solid var(--border);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat strong {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: var(--weight-normal);
  line-height: 1.1;
}

.stat span {
  color: var(--muted);
  font-size: var(--text-xs);
  white-space: nowrap;
}

/* ── 两列区 ───────────────────────────────── */
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
}

.dist {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.dist__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dist__value {
  font-family: var(--font-display);
  font-size: var(--text-xl);
}

.dist__note {
  margin-top: var(--space-4);
  color: var(--faint);
  font-size: var(--text-xs);
}

.links {
  display: flex;
  flex-direction: column;
}

.link {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  padding: var(--space-3) var(--space-2);
  border-radius: var(--radius-md);
  transition: background var(--dur-base) var(--ease);
}

.link:hover {
  background: var(--surface-2);
}

.link__index {
  flex-shrink: 0;
  padding-top: 2px;
  color: var(--faint);
  font-family: 'Consolas', monospace;
  font-size: var(--text-xs);
}

.link__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.link__body strong {
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
}

.link__body small {
  color: var(--muted);
  font-size: var(--text-xs);
}

/* ── 服务状态 ─────────────────────────────── */
.health {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4);
}

.health__item {
  color: var(--muted);
  font-size: var(--text-xs);
}

.health__item b {
  color: var(--ink);
  font-weight: var(--weight-medium);
}

/* ── 离线兜底 ─────────────────────────────── */
.offline {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
}

.offline__title {
  font-size: var(--text-xl);
}

.offline__desc {
  color: var(--muted);
  font-size: var(--text-sm);
}

@media (max-width: 900px) {
  .hero {
    flex-direction: column;
    align-items: stretch;
    padding: var(--space-5);
  }

  .hero__stats {
    padding-top: var(--space-5);
    padding-left: 0;
    border-top: 1px solid var(--border);
    border-left: 0;
  }

  .hero__title {
    font-size: var(--text-xl);
  }

  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
