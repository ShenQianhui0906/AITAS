<template>
  <article class="message-bubble" :class="isMine ? 'mine' : 'other'">
    <div class="chat-message-meta">
      <strong>{{ isMine ? '我' : otherUserName }}</strong>
      <time>{{ displayTime }}</time>
    </div>
    <p class="direct-message-body">{{ message.body }}</p>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
  currentUserId: { type: Number, default: null },
  otherUserName: { type: String, default: '对方' },
})

const isMine = computed(() => props.message.sender_id === props.currentUserId)
const displayTime = computed(() => {
  if (!props.message.created_at) return '刚刚'
  const date = new Date(props.message.created_at.replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return props.message.created_at
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
})
</script>
