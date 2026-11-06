<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="SESSION RESULT"
    title="练习结果"
    summary="一组练习结束后的汇总。核心不是分数，而是「接下来该练哪几个词」。"
    :points="[
      '四项指标：题量 / 正确数 / 正确率 / 首答正确率（首答才是真实掌握度）',
      '错词列表：词形、释义、你写的答案、下次复习时间',
      '「只练本次错词」直接建一个 wrongbook 范围的新会话',
      '没有错词时给正反馈，但明确说明「单次全对不等于永久掌握」',
      '结果页数据来自 finish 接口，幂等 —— 刷新不会重新计算',
    ]"
    :apis="[
      'POST /api/v1/practice/sessions/{id}/finish',
      'POST /api/v1/practice/sessions',
    ]"
  />
</template>
