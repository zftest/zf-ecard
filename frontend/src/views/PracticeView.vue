<script setup>
import PageStub from '@/components/PageStub.vue'
</script>

<template>
  <PageStub
    eyebrow="DICTATION SESSION"
    title="默写作答"
    summary="专注模式（侧栏与导航全部隐藏）。一次只做一件事：看题干、写答案、看反馈。"
    :points="[
      '顶部：题号 / 题型 / 首答正确数 / 进度条',
      '题干区按题型切换：中文释义、音标、播放按钮（听音写词）、英文词形（英译汉）',
      '提交后显示逐字符 diff：写对的字、写错的字、多写的字分别标色',
      '答错不阻止进入下一题，但会明确显示正确答案与距离（近失时给提示）',
      '首字母提示：点击后才计入 hint_used，影响首答统计但不直接判错',
      'Enter 提交、提交后再按 Enter 进入下一题；最后一题自动收尾',
    ]"
    :apis="[
      'POST /api/v1/practice/sessions/{id}/answers',
      'POST /api/v1/practice/sessions/{id}/finish',
      'GET /api/v1/audio/{word_id}',
    ]"
  />
</template>
