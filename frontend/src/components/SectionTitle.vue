<template>
  <div class="section-title">
    <h3>{{ title }}</h3>
    <p v-if="subline">{{ subline }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subline: { type: String, default: '' },
})
</script>
