<template>
  <div class="gai-shell">
    <!-- ===== Message Stream (scrollable) ===== -->
    <div class="gai-stream" ref="streamEl">
      <!-- Empty / welcome state -->
      <div v-if="!app.agentMessages.length" class="gai-welcome">
        <div class="gai-welcome-icon">✦</div>
        <h2 class="gai-welcome-title">Ask me anything about your courses...</h2>
        <p class="gai-welcome-sub">课程问答 · 课件总结 · 练习题生成 · 学习建议</p>
        <div class="gai-starters">
          <button
            v-for="s in starters"
            :key="s.text"
            class="gai-starter-btn"
            @click="fillAndFocus(s.text)"
          >
            <span class="gai-starter-icon">{{ s.icon }}</span>
            <span>{{ s.text }}</span>
          </button>
        </div>
      </div>

      <!-- Conversation -->
      <template v-else>
        <TransitionGroup name="gai-fade">
          <div
            v-for="(msg, idx) in app.agentMessages"
            :key="idx"
            class="gai-msg-row"
            :class="msg.role"
          >
            <!-- Assistant bubble -->
            <template v-if="msg.role === 'assistant'">
              <div class="gai-avatar ai-avatar">✦</div>
              <div class="gai-bubble ai-bubble">
                <div class="gai-bubble-meta">
                  <span class="gai-bubble-name">AI 助教</span>
                  <span v-if="msg.intent" class="gai-intent-pill">{{ intentLabel(msg.intent) }}</span>
                  <time>{{ msg.time }}</time>
                </div>
                <div class="gai-rich-text" v-html="renderRichText(msg.content)"></div>
                <div v-if="messageSources(msg).length" class="rag-sources">
                  <span class="rag-sources-label">消息来源：</span>
                  <template v-for="source in messageSources(msg)" :key="sourceKey(source)">
                    <a
                      v-if="isCoursewareSource(source)"
                      :href="source.viewer_url"
                      target="_blank"
                      class="rag-source-chip rag-source-link"
                    >{{ sourceText(source) }}</a>
                    <span
                      v-else
                      :class="['rag-source-chip', isModelSource(source) ? 'rag-source-note' : '']"
                    >{{ sourceText(source) }}</span>
                  </template>
                </div>
              </div>
            </template>

            <!-- User bubble -->
            <template v-else>
              <div class="gai-bubble user-bubble">
                <p>{{ msg.content }}</p>
              </div>
            </template>
          </div>
        </TransitionGroup>

        <!-- Thinking -->
        <div v-if="loading" class="gai-msg-row assistant">
          <div class="gai-avatar ai-avatar">✦</div>
          <div class="gai-bubble ai-bubble">
            <div class="gai-bubble-meta">
              <span class="gai-bubble-name">AI 助教</span>
              <span class="gai-intent-pill">{{ intentLabel(detectedIntent) }}</span>
            </div>
            <div class="gai-thinking">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ===== Sticky Input Bar ===== -->
    <div class="gai-input-bar">
      <div class="gai-input-toolbar">
        <button
          class="ghost-btn gai-clear-btn"
          type="button"
          :disabled="loading || clearing || !app.agentMessages.length"
          @click="clearMessages"
        >{{ clearing ? '清除中...' : '清除问答记录' }}</button>
      </div>

      <!-- Intent chips — shown only when typing -->
      <div v-if="draft.trim()" class="gai-chip-row">
        <button
          v-for="intent in intents"
          :key="intent.key"
          class="gai-chip"
          :class="{ active: detectedIntent === intent.key }"
          @click="fillAndFocus(intent.prompt)"
        >{{ intent.icon }} {{ intent.label }}</button>
      </div>

      <form class="gai-form" @submit.prevent="handleSend">
        <div class="gai-input-wrap" :class="{ focused: inputFocused }">
          <textarea
            ref="inputEl"
            v-model="draft"
            class="gai-input"
            placeholder="Ask me anything about your courses..."
            rows="1"
            @focus="inputFocused = true"
            @blur="inputFocused = false"
            @keydown.enter.exact.prevent="handleSend"
            @input="autoResize"
          ></textarea>
          <button
            class="gai-send"
            type="submit"
            :disabled="!draft.trim() || loading"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="19" x2="12" y2="5"/>
              <polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>
        <p class="gai-hint">Enter 发送 · Shift+Enter 换行</p>
      </form>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { useAppStore } from '../store/app'
import { agentApi } from '../api'
import { renderRichText } from '../utils/markdown'

const app = useAppStore()

const draft = ref('')
const loading = ref(false)
const clearing = ref(false)
const inputFocused = ref(false)
const streamEl = ref(null)
const inputEl = ref(null)
const MODEL_SOURCE_TEXT = '知识库中未记录相关问题，该回答为大模型生成'

const intents = [
  { key: 'qa',       icon: '📖', label: '课程问答',   prompt: '请讲解这门课的核心概念。' },
  { key: 'summary',  icon: '📝', label: '课件总结',   prompt: '请总结当前课件的主要内容。' },
  { key: 'exercise', icon: '✏️', label: '练习题',     prompt: '请根据课程内容出5道练习题。' },
  { key: 'homework', icon: '📋', label: '作业查询',   prompt: '最近有什么作业需要完成？' },
  { key: 'history',  icon: '🕐', label: '学习记录',   prompt: '回顾我之前的学习记录。' },
  { key: 'advice',   icon: '💡', label: '学习建议',   prompt: '给我这门课的个性化学习建议。' },
]
const intentMap = Object.fromEntries(intents.map(i => [i.key, i.label]))

const starters = [
  { icon: '📖', text: '帮我总结最近课件的核心知识点' },
  { icon: '✏️', text: '根据课程内容出5道选择练习题' },
  { icon: '💡', text: '给我这门课的个性化学习建议' },
  { icon: '🕐', text: '回顾我上次的学习记录' },
]

const detectedIntent = computed(() => {
  const q = draft.value.trim().toLowerCase()
  if (!q) return 'qa'
  if (/总结|概括|大纲|摘要|归纳/.test(q)) return 'summary'
  if (/练习|题目|习题|测试|出题|考题/.test(q)) return 'exercise'
  if (/作业|任务|提交|截止|deadline/.test(q)) return 'homework'
  if (/历史|记录|之前|上次|回顾|复习/.test(q)) return 'history'
  if (/建议|推荐|方法|计划|怎么学|如何学/.test(q)) return 'advice'
  return 'qa'
})

function intentLabel(key) { return intentMap[key] || '课程问答' }

function fillAndFocus(text) {
  draft.value = text
  nextTick(() => { inputEl.value?.focus(); autoResize() })
}

function autoResize() {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function messageTime(message) {
  if (!message.created_at) return message.time || now()
  const value = new Date(message.created_at.replace(' ', 'T'))
  if (Number.isNaN(value.getTime())) return message.created_at
  return value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function normalizeMessages(messages = []) {
  return messages.map(message => ({ ...message, time: messageTime(message) }))
}

function messageSources(message) {
  const raw = message?.sources
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function isCoursewareSource(source) {
  return typeof source === 'object' && source && source.viewer_url
}

function isModelSource(source) {
  return typeof source === 'object' && source?.type === 'model_generated'
}

function sourceText(source) {
  if (typeof source === 'string') return source
  if (!source || typeof source !== 'object') return MODEL_SOURCE_TEXT
  if (source.course_name && source.title) return `${source.course_name} · ${source.title}`
  return source.title || source.course_name || source.label || MODEL_SOURCE_TEXT
}

function sourceKey(source) {
  if (typeof source === 'string') return source
  if (source?.courseware_id) return `courseware-${source.courseware_id}`
  return `${source?.type || 'source'}-${sourceText(source)}`
}

function scrollToBottom() {
  nextTick(() => {
    if (streamEl.value) streamEl.value.scrollTop = streamEl.value.scrollHeight
  })
}

async function handleSend() {
  const text = draft.value.trim()
  if (!text || loading.value) return

  const intent = detectedIntent.value
  app.agentMessages.push({ role: 'user', content: text, time: now() })
  draft.value = ''
  nextTick(() => { autoResize(); scrollToBottom() })
  loading.value = true

  try {
    const data = await agentApi.ask({ class_id: app.currentClassId, message: text })
    app.agentMessages = normalizeMessages(data.messages || [])
  } catch (error) {
    app.agentMessages.push({
      role: 'assistant',
      content: `抱歉，这次没有生成回答。${error.message || '请稍后重试。'}`,
      intent,
      time: now(),
    })
    app.setStatus(error.message || '回答生成失败，请稍后重试。', 'error')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function loadMessages() {
  if (!app.currentClassId) {
    app.agentMessages = []
    return
  }
  try {
    const data = await agentApi.messages({ class_id: app.currentClassId })
    app.agentMessages = normalizeMessages(data.messages || [])
    scrollToBottom()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function clearMessages() {
  if (!app.currentClassId || clearing.value) return
  clearing.value = true
  try {
    await agentApi.clear({ class_id: app.currentClassId })
    app.agentMessages = []
    draft.value = ''
    app.setStatus('首页问答记录已清除。')
  } catch (error) {
    app.setStatus(error.message || '清除问答记录失败。', 'error')
  } finally {
    clearing.value = false
  }
}

watch(() => app.currentClassId, loadMessages, { immediate: true })

defineExpose({ clear: clearMessages })
</script>
