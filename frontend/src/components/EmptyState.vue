<template>
  <div class="empty-state">
    <div class="empty-illustration"></div>
    <div class="empty-copy">
      <strong>当前还没有内容</strong>
      <span>{{ message }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: '当前还没有内容' },
})
</script>
