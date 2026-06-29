<template>
  <article v-if="message.role === 'assistant'" class="chat-entry assistant-entry">
    <div class="chat-message-meta assistant-meta">
      <span class="chat-role-pill assistant">知识库 AI</span>
      <time>{{ message.created_at || '刚刚生成' }}</time>
    </div>
    <div class="ai-rich-text" v-html="richContent"></div>
    <div v-if="sources.length" class="rag-sources">
      <span class="rag-sources-label">消息来源：</span>
      <template v-for="s in sources" :key="sourceKey(s)">
        <a
          v-if="isCoursewareSource(s)"
          :href="s.viewer_url"
          target="_blank"
          class="rag-source-chip rag-source-link"
        >{{ sourceText(s) }}</a>
        <span
          v-else
          :class="['rag-source-chip', isModelSource(s) ? 'rag-source-note' : '']"
        >{{ sourceText(s) }}</span>
      </template>
    </div>
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

const MODEL_SOURCE_TEXT = '知识库中未记录相关问题，该回答为大模型生成'

const props = defineProps({
  message: { type: Object, required: true },
})

const sources = computed(() => {
  const raw = props.message.sources
  if (!raw) return props.message.role === 'assistant' ? [{ type: 'model_generated', label: MODEL_SOURCE_TEXT }] : []
  if (Array.isArray(raw)) return raw.length ? raw : [{ type: 'model_generated', label: MODEL_SOURCE_TEXT }]
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.length ? parsed : [{ type: 'model_generated', label: MODEL_SOURCE_TEXT }]
  } catch {
    return [{ type: 'model_generated', label: MODEL_SOURCE_TEXT }]
  }
})
const richContent = computed(() => props.message.role === 'assistant' ? renderRichText(props.message.content) : '')

function isCoursewareSource(source) {
  return typeof source === 'object' && source && source.viewer_url
}

function isModelSource(source) {
  return typeof source === 'object' && source?.type === 'model_generated'
}

function sourceText(source) {
  if (typeof source === 'string') return source
  if (!source || typeof source !== 'object') return MODEL_SOURCE_TEXT
  if (isModelSource(source)) return source.label || MODEL_SOURCE_TEXT
  if (source.course_name && source.title) return `${source.course_name} · ${source.title}`
  return source.title || source.course_name || source.label || MODEL_SOURCE_TEXT
}

function sourceKey(source) {
  if (typeof source === 'string') return source
  if (source?.courseware_id) return `courseware-${source.courseware_id}`
  return `${source?.type || 'source'}-${sourceText(source)}`
}
</script>
