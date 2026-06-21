<template>
  <div class="sheet-shell">
    <div class="sheet-overlay" @click="$emit('close')"></div>
    <aside class="sheet-panel" :class="{ wide }">
      <div class="sheet-panel-head">
        <div>
          <span class="eyebrow">{{ eyebrow }}</span>
          <h3>{{ title }}</h3>
          <p v-if="description">{{ description }}</p>
        </div>
        <button class="toast-close" type="button" @click="$emit('close')">&times;</button>
      </div>
      <div class="sheet-panel-body">
        <slot />
      </div>
    </aside>
  </div>
</template>

<script setup>
defineProps({
  eyebrow: { type: String, default: '编辑面板' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  wide: { type: Boolean, default: false },
})
defineEmits(['close'])
</script>
