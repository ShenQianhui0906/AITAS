<template>
  <div class="dialog-overlay">
    <div class="dialog-card" :class="config.tone || ''">
      <div class="dialog-head">
        <div>
          <span class="eyebrow">{{ config.eyebrow || '操作确认' }}</span>
          <h3>{{ config.title }}</h3>
        </div>
        <button class="toast-close" type="button" @click="$emit('cancel')">&times;</button>
      </div>
      <p>{{ config.description }}</p>
      <div class="button-row">
        <button class="ghost-btn" type="button" @click="$emit('cancel')">
          {{ config.cancelText || '取消' }}
        </button>
        <button
          :class="config.confirmClass || 'primary-btn'"
          type="button"
          @click="$emit('confirm')"
        >
          {{ config.confirmText || '确认' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  config: { type: Object, required: true },
})
defineEmits(['confirm', 'cancel'])
</script>
