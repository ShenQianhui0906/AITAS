<template>
  <div class="section-title">
    <div class="section-title-left">
      <h3>{{ title }}</h3>
      <p v-if="subtitle || subline">{{ subtitle || subline }}</p>
    </div>
    <div v-if="$slots.actions" class="section-title-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  subline: { type: String, default: '' },
})
</script>
