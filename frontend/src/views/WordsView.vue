<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="WORD LIBRARY"
    title="单词库"
    summary="按单元、主题、词性、掌握状态筛选，支持中英文混合搜索；单词详情里有全部义项与逐技能进度。"
    :points="[
      '顶部搜索框 + 单元/主题/词性/状态筛选，筛选结果可一键带入默写',
      '列表按单元或字母排序，显示音标、主释义、掌握状态、是否有音频',
      '点击单词打开详情：全部义项、例句、逐技能进度（拼写/听音/词义/音标）',
      '发音按钮：先试 uk 音频，404 时降级到设备语音并明确标注',
      '分页与「全部选中」用于「用所选词默写」',
    ]"
    :apis="[
      'GET /api/v1/units',
      'GET /api/v1/themes',
      'GET /api/v1/words',
      'GET /api/v1/words/{word_id}',
      'GET /api/v1/audio/{word_id}',
    ]"
  />
</template>
