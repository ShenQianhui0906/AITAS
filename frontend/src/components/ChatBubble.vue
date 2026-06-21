<template>
  <article v-if="message.role === 'assistant'" class="chat-entry assistant-entry">
    <div class="chat-message-meta assistant-meta">
      <span class="chat-role-pill assistant">AI 助教</span>
      <time>{{ message.created_at || '刚刚生成' }}</time>
    </div>
    <div class="ai-rich-text" v-html="richContent"></div>
  </article>

  <article v-else class="chat-bubble user">
    <div class="chat-message-meta">
      <span class="chat-role-pill user">我的问题</span>
      <time>{{ message.created_at || '刚刚发送' }}</time>
    </div>
    <div class="user-rich-text"><p>{{ message.content }}</p></div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { renderRichText } from '../utils/markdown'

const props = defineProps({
  message: { type: Object, required: true },
})

const richContent = computed(() => props.message.role === 'assistant' ? renderRichText(props.message.content) : '')
</script>
