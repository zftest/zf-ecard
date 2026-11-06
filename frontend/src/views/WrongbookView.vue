<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="MISTAKE NOTEBOOK"
    title="错词复习"
    summary="一行 = 一个词 × 一个技能。同一个词在拼写和听音上都错过时会占两行 —— 这不是重复，是两种能力都弱。"
    :points="[
      '顶部三项角标：错词总数 / 今日待复习 / 本周新掌握',
      '按技能分组展示，每组显示该技能累计错次',
      '排序切换：到期优先（默认）/ 错误次数 / 最近出错',
      '每行操作：标为已掌握、重置重练、直接练这个词',
      '「重练全部错词」= 用 wrongbook 范围建会话，未到期的也可以练',
      '空状态区分「没有错词」与「筛选后为空」两种情况',
    ]"
    :apis="[
      'GET /api/v1/learners/{id}/wrongbook',
      'PATCH /api/v1/learners/{id}/wrongbook/{word_id}',
      'POST /api/v1/practice/sessions',
    ]"
  />
</template>
