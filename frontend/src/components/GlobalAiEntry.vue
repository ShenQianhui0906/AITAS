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
import { ref, computed, nextTick } from 'vue'
import { useAppStore } from '../store/app'
import { agentApi } from '../api'
import { renderRichText } from '../utils/markdown'

const app = useAppStore()

const draft = ref('')
const loading = ref(false)
const inputFocused = ref(false)
const streamEl = ref(null)
const inputEl = ref(null)

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
    const data = await agentApi.ask({ class_id: app.currentClassId, message: text, intent })
    app.agentMessages.push({
      role: 'assistant',
      content: data.reply || '抱歉，暂时无法回答。',
      intent: data.intent || intent,
      time: now(),
    })
  } catch {
    app.agentMessages.push({
      role: 'assistant',
      content: buildFallback(text, intent),
      intent,
      time: now(),
    })
    app.setStatus('后端接口尚未就绪，当前显示模拟回复。', 'error')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function buildFallback(q, intent) {
  const map = {
    qa:       `收到课程问答请求：「${q}」\n\n> ⚠️ 当前为模拟回复。后端就绪后 AI 将检索课件知识库为你精准解答。\n\n可先在「课件」页面查看相关章节内容。`,
    summary:  `收到课件总结请求：「${q}」\n\n> ⚠️ 当前为模拟回复。功能就绪后将自动提取课件全文并生成结构化摘要。`,
    exercise: `收到练习题请求：「${q}」\n\n> ⚠️ 当前为模拟回复。功能就绪后将基于课件内容自动生成题目。`,
    homework: `收到作业查询：「${q}」\n\n> ⚠️ 当前为模拟回复。功能就绪后可查询作业列表与截止日期。`,
    history:  `收到学习记录查询：「${q}」\n\n> ⚠️ 当前为模拟回复。功能就绪后将展示你的完整学习轨迹。`,
    advice:   `收到学习建议请求：「${q}」\n\n> ⚠️ 当前为模拟回复。功能就绪后 AI 将根据你的数据提供个性化建议。`,
  }
  return map[intent] || map.qa
}

defineExpose({ clear: () => { app.agentMessages = [] } })
</script>
