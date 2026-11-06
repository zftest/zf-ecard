<script setup>
/**
 * 文本输入。
 *
 * 无障碍三件套是重点，缺一样读屏用户就不知道这个框是干什么的、哪里错了：
 *   1. <label for> 与 input 的 id 关联
 *   2. 错误时 aria-invalid="true"
 *   3. hint / error 用 aria-describedby 挂到 input 上
 */
import { computed, ref, useAttrs, useId } from 'vue'

defineOptions({ name: 'AppInput', inheritAttrs: false })

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  /** 常态提示，如"Enter 提交" */
  hint: { type: String, default: '' },
  /** 校验错误。非空即视为错误态，会替换掉 hint 的位置 */
  error: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  /** 练习页用 lg：输入框要成为视线的落点，15px 太小 */
  size: { type: String, default: 'md', validator: (v) => ['md', 'lg'].includes(v) },
  /**
   * 关闭浏览器自动更正。
   * 拼单词的场景下自动纠错是有害的：它会把孩子写错的词悄悄改对，
   * 于是判题永远正确，错词本永远不进词 —— 看起来"都学会了"。
   */
  spellcheck: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'enter', 'blur', 'focus'])

const attrs = useAttrs()
const inputRef = ref(null)

// useId 保证同页多个输入框的 id 不冲突。
// 不能用 `let seq = 0` 自增：script setup 的顶层代码每个实例都会执行一遍，
// seq 永远从 0 开始，多个输入框拿到同一个 id，label 就会指错人。
const uid = `in-${useId()}`
const inputId = computed(() => attrs.id || uid)
const hintId = computed(() => `${inputId.value}-hint`)
const errorId = computed(() => `${inputId.value}-error`)

const describedBy = computed(() => {
  if (props.error) return errorId.value
  if (props.hint) return hintId.value
  return undefined
})

function onInput(event) {
  emit('update:modelValue', event.target.value)
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.isComposing) {
    // isComposing：中文输入法选词时的回车不是"提交"，
    // 不判断这一下，打中文的用户每选一次词就被提交一次
    emit('enter', event)
  }
}

defineExpose({ focus: () => inputRef.value?.focus(), el: inputRef })
</script>

<template>
  <div class="field" :class="{ 'field--error': Boolean(props.error) }">
    <label v-if="props.label" class="field__label" :for="inputId">{{ props.label }}</label>

    <div class="field__control" :class="`field__control--${props.size}`">
      <input
        :id="inputId"
        ref="inputRef"
        v-bind="attrs"
        class="field__input"
        :type="props.type"
        :value="props.modelValue"
        :placeholder="props.placeholder"
        :disabled="props.disabled"
        :readonly="props.readonly"
        :spellcheck="props.spellcheck"
        :autocapitalize="'off'"
        :autocomplete="attrs.autocomplete || 'off'"
        :aria-invalid="props.error ? 'true' : undefined"
        :aria-describedby="describedBy"
        @input="onInput"
        @keydown="onKeydown"
        @blur="emit('blur', $event)"
        @focus="emit('focus', $event)"
      />
      <slot name="suffix" />
    </div>

    <p v-if="props.error" :id="errorId" class="field__message field__message--error" role="alert">
      {{ props.error }}
    </p>
    <p v-else-if="props.hint" :id="hintId" class="field__message">{{ props.hint }}</p>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field__label {
  color: var(--muted);
  font-size: var(--text-sm);
}

.field__control {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  transition: border-color var(--dur-base) var(--ease), box-shadow var(--dur-base) var(--ease);
}

.field__control--md {
  min-height: var(--tap-min);
}

.field__control--lg {
  min-height: 58px;
  padding: 0 var(--space-5);
}

.field__control:focus-within {
  border-color: var(--primary);
  /* 用 box-shadow 做内圈高亮而不是 outline：
     outline 会被圆角裁掉，看起来像方框套圆框 */
  box-shadow: 0 0 0 3px var(--primary-soft);
}

.field--error .field__control {
  border-color: var(--danger);
}

.field--error .field__control:focus-within {
  box-shadow: 0 0 0 3px var(--danger-soft);
}

.field__input {
  flex: 1;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  outline: none;
  font-size: var(--text-base);
}

.field__control--lg .field__input {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  letter-spacing: 0.01em;
}

.field__input::placeholder {
  color: var(--faint);
}

.field__message {
  color: var(--muted);
  font-size: var(--text-xs);
}

.field__message--error {
  color: var(--danger);
}
</style>
