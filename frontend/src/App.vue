<script setup>
/**
 * 应用外壳：侧栏 + 顶栏 + 路由出口 + 移动端底部标签。
 *
 * 三种形态：
 *   - 桌面（≥900px）：固定侧栏，主区左偏移
 *   - 移动（<900px）：隐藏侧栏，底部 4 个标签
 *   - 专注模式（路由 meta.focus，如练习页/结果页）：
 *     全部导航隐藏，只留内容 —— 做题时侧栏上的错词角标会分心
 */
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import AppToast from '@/components/AppToast.vue'
import { MOBILE_TABS, NAV_ITEMS, PRACTICE_META, findNavItem } from '@/router/navigation'
import { useLearnerStore } from '@/stores/learner'

const route = useRoute()
const learner = useLearnerStore()

const isFocus = computed(() => Boolean(route.meta?.focus))

const pageMeta = computed(() => {
  const nav = findNavItem(route.name)
  if (nav) return { en: nav.en, label: nav.label }
  const extra = PRACTICE_META[route.name]
  if (extra) return { en: extra.en, label: extra.label }
  return { en: 'WORD PRACTICE', label: '词练' }
})

onMounted(() => {
  // 顶栏与侧栏的角标要显示"错词 N 个"。
  // 这里不 await、不弹错误：外壳的渲染不该被一次辅助请求卡住，
  // 后端没起来时用户仍然能看到完整的导航结构（只是角标是 0）。
  learner.loadProfile().catch(() => {})
})
</script>

<template>
  <div class="shell" :class="{ 'shell--focus': isFocus }">
    <aside v-if="!isFocus" class="sidebar">
      <RouterLink to="/" class="brand" aria-label="返回学习首页">
        <span class="brand__mark" aria-hidden="true">词</span>
        <span class="brand__copy">
          <strong>词练</strong>
          <small>JUNIOR ENGLISH</small>
        </span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
        <RouterLink
          v-for="item in NAV_ITEMS"
          :key="item.name"
          :to="item.path"
          class="nav__item"
          active-class="nav__item--active"
        >
          <span class="nav__index" aria-hidden="true">{{ item.index }}</span>
          <span>{{ item.label }}</span>
          <span v-if="item.name === 'wrongbook' && learner.wrongCount" class="nav__badge">
            {{ learner.wrongCount }}
          </span>
        </RouterLink>
      </nav>

      <div class="sidebar__foot">
        <p class="sidebar__caption">当前学习者</p>
        <strong>{{ learner.displayName }}</strong>
        <span>人教版 · 七年级上下册</span>
      </div>
    </aside>

    <div class="main">
      <header v-if="!isFocus" class="topbar">
        <div class="topbar__heading">
          <p class="topbar__eyebrow">{{ pageMeta.en }}</p>
          <h1 class="topbar__title">{{ pageMeta.label }}</h1>
        </div>
        <RouterLink to="/config" class="topbar__cta">开始默写</RouterLink>
      </header>

      <main class="view">
        <RouterView v-slot="{ Component }">
          <Transition name="view" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <nav v-if="!isFocus" class="tabs" aria-label="底部导航">
      <RouterLink
        v-for="item in MOBILE_TABS"
        :key="item.name"
        :to="item.path"
        class="tabs__item"
        active-class="tabs__item--active"
      >
        <span class="tabs__index" aria-hidden="true">{{ item.index }}</span>
        <span class="tabs__label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <AppToast />
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

/* ── 侧栏 ─────────────────────────────────── */
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: var(--z-sidebar);
  display: flex;
  flex-direction: column;
  width: var(--sidebar-w);
  padding: var(--space-6) var(--space-5) var(--space-5);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-2) var(--space-6);
}

.brand__mark {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: var(--primary);
  color: var(--on-primary);
  font-family: var(--font-display);
  font-size: var(--text-lg);
}

.brand__copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand__copy strong {
  font-size: var(--text-lg);
  letter-spacing: 0.04em;
}

.brand__copy small {
  margin-top: var(--space-1);
  color: var(--muted);
  font-size: var(--text-2xs);
  letter-spacing: 0.18em;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.nav__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: var(--tap-min);
  padding: 0 var(--space-3);
  border-radius: 9px;
  color: var(--muted);
  transition:
    background var(--dur-base) var(--ease),
    color var(--dur-base) var(--ease);
}

.nav__item:hover {
  background: rgba(255, 253, 246, 0.7);
  color: var(--ink);
}

.nav__item--active {
  background: var(--surface);
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.nav__item--active .nav__index {
  color: var(--primary);
}

.nav__index {
  width: 20px;
  color: var(--faint);
  font-family: 'Consolas', monospace;
  font-size: var(--text-2xs);
  letter-spacing: 0.04em;
}

.nav__badge {
  min-width: 20px;
  margin-left: auto;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: var(--text-xs);
  text-align: center;
}

.sidebar__foot {
  margin-top: auto;
  padding: var(--space-4) var(--space-2) 0;
  border-top: 1px solid var(--border);
}

.sidebar__caption {
  color: var(--faint);
  font-size: var(--text-2xs);
  letter-spacing: 0.12em;
}

.sidebar__foot strong {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
}

.sidebar__foot span {
  color: var(--muted);
  font-size: var(--text-2xs);
}

/* ── 主区 ─────────────────────────────────── */
.main {
  flex: 1;
  min-width: 0;
  width: calc(100% - var(--sidebar-w));
  margin-left: var(--sidebar-w);
  padding: 0 var(--space-6) var(--space-8);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  min-height: 102px;
  border-bottom: 1px solid var(--border);
}

.topbar__eyebrow {
  color: var(--faint);
  font-size: var(--text-2xs);
  letter-spacing: 0.18em;
}

.topbar__title {
  margin-top: var(--space-1);
  font-size: var(--text-2xl);
}

.topbar__cta {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  min-height: var(--tap-min);
  padding: 0 var(--space-5);
  border-radius: var(--radius-pill);
  background: var(--primary);
  color: var(--on-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  transition: background var(--dur-base) var(--ease);
}

.topbar__cta:hover {
  background: var(--primary-dark);
}

.view {
  padding-top: var(--space-6);
}

/* ── 专注模式（练习/结果）─────────────────── */
.shell--focus .main {
  width: 100%;
  margin-left: 0;
  padding: 0 var(--space-5) var(--space-7);
}

/* ── 移动端底部标签 ───────────────────────── */
.tabs {
  display: none;
}

@media (max-width: 900px) {
  .sidebar {
    display: none;
  }

  .main {
    width: 100%;
    margin-left: 0;
    padding: 0 var(--space-4) calc(72px + env(safe-area-inset-bottom, 0px));
  }

  .topbar {
    min-height: 76px;
  }

  /* 移动端藏掉顶栏 CTA：底部标签已经有"分类默写"，
     首页卡片里也有主按钮，顶栏再来一个就是三个入口抢同一件事，
     而且会把标题挤到换行。 */
  .topbar__cta {
    display: none;
  }

  .topbar__title {
    font-size: var(--text-xl);
  }

  .tabs {
    position: fixed;
    inset: auto 0 0 0;
    z-index: var(--z-sidebar);
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    background: var(--surface);
    border-top: 1px solid var(--border);
  }

  .tabs__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    min-height: 56px;
    color: var(--muted);
  }

  .tabs__item--active {
    color: var(--primary);
  }

  .tabs__index {
    font-family: 'Consolas', monospace;
    font-size: var(--text-2xs);
    opacity: 0.7;
  }

  .tabs__label {
    font-size: var(--text-xs);
  }
}

/* ── 路由切换动画 ─────────────────────────── */
.view-enter-active,
.view-leave-active {
  transition:
    opacity var(--dur-base) var(--ease),
    transform var(--dur-base) var(--ease);
}

.view-enter-from,
.view-leave-to {
  transform: translateY(6px);
  opacity: 0;
}
</style>
