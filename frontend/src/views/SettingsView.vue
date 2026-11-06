<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="SETTINGS"
    title="学习设置"
    summary="发音口音、默认题型、每日目标、提示开关。MVP 阶段存本地，多设备同步放到有账号之后再谈。"
    :points="[
      '口音：英式 / 美式（影响默认播放哪一个，不影响已生成的音频文件）',
      '默认题型与默认题量：进入分类默写时预填',
      '每日目标 10 / 20 / 30 个词，影响首页进度与角标',
      '首字母提示默认开关',
      '数据与来源：词库来源、音频来源与许可说明（edge-tts 仅供个人学习）',
    ]"
    :apis="['GET /api/v1/learners/{id}', '本地 localStorage']"
  />
</template>
