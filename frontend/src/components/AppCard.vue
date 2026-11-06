<script setup>
/**
 * 卡片：页面的信息容器。
 *
 * 只用 slot 组合，不预设内部结构 —— 这个项目里卡片装过单词列表、
 * 统计数字、练习题干、导入校对表格，强行统一内部布局会让每种都用不上。
 */
defineOptions({ name: 'AppCard' })

const props = defineProps({
  title: { type: String, default: '' },
  /** 卡片左上角的英文小标签，如 WORD LIBRARY。原型里的视觉锚点 */
  eyebrow: { type: String, default: '' },
  tone: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'muted', 'primary'].includes(v),
  },
  padding: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'compact', 'none'].includes(v),
  },
  /**
   * 标题的层级。默认 h3：卡片通常挂在已经有 h1/h2 的页面里。
   * 但占位页、独立面板这类"卡片就是页面主体"的场景要传 2，
   * 否则标题会从 h1 直接跳到 h3，读屏用户按标题跳转时层级是断的。
   */
  headingLevel: { type: Number, default: 3 },
})
</script>

<template>
  <section class="card" :class="[`card--${props.tone}`, `card--pad-${props.padding}`]">
    <header v-if="props.title || props.eyebrow || $slots.header || $slots.actions" class="card__head">
      <slot name="header">
        <div class="card__heading">
          <p v-if="props.eyebrow" class="card__eyebrow">{{ props.eyebrow }}</p>
          <component :is="`h${props.headingLevel}`" v-if="props.title" class="card__title">
            {{ props.title }}
          </component>
        </div>
      </slot>
      <div v-if="$slots.actions" class="card__actions"><slot name="actions" /></div>
    </header>

    <div class="card__body"><slot /></div>

    <footer v-if="$slots.footer" class="card__foot"><slot name="footer" /></footer>
  </section>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  /* 不加 overflow:hidden —— 卡片里的下拉、气泡会被裁掉。
     圆角靠子元素的 border-radius 各自处理。 */
}

.card--muted {
  background: var(--surface-2);
  box-shadow: none;
}

.card--primary {
  background: var(--primary-soft);
  border-color: #cfd9f2;
  box-shadow: none;
}

.card--pad-default {
  padding: var(--space-5);
}

.card--pad-compact {
  padding: var(--space-4);
}

.card--pad-none {
  padding: 0;
}

.card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.card__heading {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.card__eyebrow {
  color: var(--faint);
  font-size: var(--text-2xs);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.card__title {
  font-size: var(--text-lg);
}

/* 当卡片就是页面主体时（headingLevel=2），标题要撑得起页面 */
h2.card__title {
  font-size: var(--text-2xl);
}

.card__actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--space-2);
}

.card__body {
  flex: 1;
  min-width: 0;
}

.card__foot {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}
</style>
