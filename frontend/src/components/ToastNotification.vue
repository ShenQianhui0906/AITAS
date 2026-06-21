<template>
  <div class="toast-region">
    <div class="toast-card" :class="type || 'info'">
      <div class="toast-accent"></div>
      <div class="toast-copy">
        <strong>{{ type === 'error' ? '操作提示' : '系统提示' }}</strong>
        <span>{{ message }}</span>
      </div>
      <button class="toast-close" type="button" @click="$emit('dismiss')">&times;</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, required: true },
  type: { type: String, default: '' },
})
defineEmits(['dismiss'])
</script>
