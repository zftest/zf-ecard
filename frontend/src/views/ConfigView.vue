<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="DICTATION SETUP"
    title="分类默写"
    summary="选题型、选范围、定题量与顺序，然后开始一组练习。这一页决定「练什么」，练习页只负责「怎么答」。"
    :points="[
      '四种题型：汉译英 / 听音写词 / 英译汉 / 音标写词，各带一句区别说明',
      '四种范围：指定单元 / 主题 / 错词本 / 全部词库',
      '题量 5-50、顺序（随机/顺序/薄弱优先）、是否允许首字母提示',
      '实时显示该范围可出的题数；不足时提前告知，而不是开始后才发现只有 6 题',
      '开始按钮建会话成功后跳转 /practice，失败就地提示',
    ]"
    :apis="['POST /api/v1/practice/sessions']"
  />
</template>
