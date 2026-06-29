<template>
  <div v-if="visible" class="dialog-overlay" @click.self="cancel">
    <div class="dialog-card" :class="internalConfig.tone || ''">
      <div class="dialog-head">
        <div>
          <span class="eyebrow">{{ internalConfig.eyebrow || '操作确认' }}</span>
          <h3>{{ internalConfig.title }}</h3>
        </div>
        <button class="toast-close" type="button" @click="cancel">&times;</button>
      </div>
      <p>{{ internalConfig.description }}</p>
      <div class="button-row">
        <button class="ghost-btn" type="button" @click="cancel">
          {{ internalConfig.cancelText || '取消' }}
        </button>
        <button
          :class="internalConfig.confirmClass || 'primary-btn'"
          type="button"
          @click="confirm"
        >
          {{ internalConfig.confirmText || '确认' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  config: { type: Object, default: null },
})
const emit = defineEmits(['confirm', 'cancel'])

const visible = ref(false)
const internalConfig = reactive({
  title: '',
  description: '',
  tone: '',
  eyebrow: '操作确认',
  cancelText: '取消',
  confirmText: '确认',
  confirmClass: 'primary-btn',
})

let _resolve = null

function confirm() {
  visible.value = false
  if (_resolve) { _resolve(true); _resolve = null }
  emit('confirm')
}

function cancel() {
  visible.value = false
  if (_resolve) { _resolve(false); _resolve = null }
  emit('cancel')
}

function show(titleOrMessage, opts = {}) {
  Object.assign(internalConfig, {
    title: opts.title || titleOrMessage,
    description: opts.description || (opts.title ? titleOrMessage : ''),
    tone: opts.tone || '',
    eyebrow: opts.eyebrow || '操作确认',
    cancelText: opts.cancelText || '取消',
    confirmText: opts.confirmText || '确认',
    confirmClass: opts.confirmClass || 'primary-btn',
  })
  visible.value = true
  return new Promise((resolve) => {
    _resolve = resolve
  })
}

// 兼容 App.vue 的 props 驱动模式
watch(() => props.config, (cfg) => {
  if (cfg) {
    Object.assign(internalConfig, {
      title: cfg.title || '',
      description: cfg.description || '',
      tone: cfg.tone || '',
      eyebrow: cfg.eyebrow || '操作确认',
      cancelText: cfg.cancelText || '取消',
      confirmText: cfg.confirmText || '确认',
      confirmClass: cfg.confirmClass || 'primary-btn',
    })
    visible.value = true
  } else {
    visible.value = false
  }
}, { immediate: true })

defineExpose({ show, confirm: show })
</script>
