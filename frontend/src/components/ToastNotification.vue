<template>
  <div v-if="visible" class="toast-region">
    <div class="toast-card" :class="type || 'info'">
      <div class="toast-accent"></div>
      <div class="toast-copy">
        <strong>{{ type === 'error' ? '操作提示' : '系统提示' }}</strong>
        <span>{{ message }}</span>
      </div>
      <button class="toast-close" type="button" @click="dismiss">&times;</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  message: { type: String, default: '' },
  type: { type: String, default: '' },
})
const emit = defineEmits(['dismiss'])

const visible = ref(false)
let timer = null

function dismiss() {
  visible.value = false
  if (timer) { clearTimeout(timer); timer = null }
  emit('dismiss')
}

function show(msg, msgType = '') {
  if (timer) { clearTimeout(timer); timer = null }
  message.value = msg
  type.value = msgType || ''
  visible.value = true
  timer = setTimeout(() => {
    visible.value = false
  }, msgType === 'error' ? 4200 : 2600)
}

// 内部响应式副本，支持 prop 和 show() 双模式
const message = ref(props.message)
const type = ref(props.type)

watch(() => props.message, (v) => {
  if (v) { message.value = v; visible.value = true }
  else { visible.value = false }
})
watch(() => props.type, (v) => { type.value = v || '' })

defineExpose({ show, dismiss })
</script>
