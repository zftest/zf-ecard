<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="IMPORT STUDIO"
    title="词库导入"
    summary="PDF / CSV 只生成可校对的草稿。校对、去重、确认之后才允许写入词库 —— 自动识别错一个字母，孩子就会背错一个词。"
    :points="[
      '拖拽或选择文件（PDF / CSV / JSON），显示大小与类型校验',
      '解析进度：用不确定进度条，因为解析是异步的，估不出百分比',
      '校对表格：每个字段带置信度，低置信度标黄要求人工确认',
      '重复词冲突：与现有词库对比，逐条选择「跳过 / 覆盖 / 新增义项」',
      '发布前预览：确认共新增多少词、多少义项、多少单元',
    ]"
    :apis="['P1 交付，MVP 阶段本页只做文件校验与提示']"
  />
</template>
