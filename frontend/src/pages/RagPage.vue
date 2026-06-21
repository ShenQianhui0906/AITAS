<template>
  <LoadingSpinner v-if="loading" />

  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle title="暂无班级" />
    <p class="empty-copy">先在班级页创建或加入班级，再使用知识库。</p>
    <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
  </div>

  <section v-else class="rag-layout">
    <div class="rag-left-shell">
      <article class="surface section-shell rag-index-card">
        <SectionTitle title="知识库状态" />
        <div class="rag-status-block">
          <div class="rag-status-chip">
            <span :class="['rag-status-dot', app.ragIndexStatus === 'ready' ? 'online' : 'offline']"></span>
            <strong>{{ app.ragIndexStatus === 'ready' ? '已索引' : '未索引' }}</strong>
          </div>
          <p class="rag-status-desc">
            {{ app.ragIndexStatus === 'ready' ? '知识库就绪，可以开始提问。' : '请教师先构建知识库索引以启用问答功能。' }}
          </p>
        </div>
        <template v-if="auth.role === 'teacher' || auth.role === 'admin'">
          <div class="button-row">
            <button class="primary-btn" @click="buildIndex">构建索引</button>
            <button class="secondary-btn" @click="buildIndex">刷新索引</button>
          </div>
        </template>
      </article>
    </div>

    <div class="rag-right-shell">
      <article class="surface section-shell rag-chat-panel">
        <div class="rag-chat-header">
          <div>
            <span class="eyebrow">知识库问答</span>
            <h4>基于课件知识回答</h4>
          </div>
          <span class="soft-badge">GLM 在线</span>
        </div>
        <div class="ai-assistant-toolbar">
          <div class="suggestion-row">
            <button
              v-for="s in ragSuggestions"
              :key="s"
              class="suggestion-chip"
              @click="setRagDraft(s)"
            >{{ s }}</button>
          </div>
          <p class="ai-panel-note">回答基于班级课件知识库生成，可用于学习辅导。</p>
        </div>
        <div class="chat-stream" ref="ragStream">
          <AiOnboarding v-if="!app.ragMessages.length" />
          <RagChatBubble v-for="(m, i) in app.ragMessages" :key="i" :message="m" />
          <article v-if="app.ragLoading" class="chat-entry assistant-entry loading-bubble">
            <div class="chat-message-meta assistant-meta">
              <span class="chat-role-pill assistant">AI 助教</span>
              <time>生成中</time>
            </div>
            <div class="ai-rich-text"><p>正在检索课件知识并生成回答...</p></div>
          </article>
        </div>
        <div class="prompt-shell assistant-prompt-shell">
          <form class="form-grid chat-composer" @submit.prevent="handleRagQa">
            <div class="field prompt-field">
              <label for="rag-question">问题内容</label>
              <textarea id="rag-question" v-model="app.ragDraft" placeholder="输入你的问题"></textarea>
            </div>
            <div class="button-row prompt-actions">
              <button class="ghost-btn" type="button" @click="clearRag">清空记录</button>
              <button class="primary-btn send-btn" type="submit" :disabled="app.ragLoading">
                {{ app.ragLoading ? '生成中...' : '发送问题' }}
              </button>
            </div>
          </form>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { ragApi } from '../api'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import AiOnboarding from '../components/AiOnboarding.vue'
import RagChatBubble from '../components/RagChatBubble.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const ragStream = ref(null)

const ragSuggestions = [
  '请总结课程的核心知识点。',
  '这门课的重点章节有哪些？',
  '根据课件内容，有什么学习建议？',
]

async function load() {
  loading.value = true
  try {
    const data = await ragApi.status({ class_id: app.currentClassId })
    app.ragIndexStatus = data.status || 'not_built'
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

async function buildIndex() {
  try {
    app.setStatus('正在构建知识库索引...')
    const data = await ragApi.build({ class_id: app.currentClassId })
    app.ragIndexStatus = data.status || 'ready'
    app.setStatus('知识库索引已构建。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

function setRagDraft(text) {
  app.ragDraft = text
  nextTick(() => {
    const ta = document.getElementById('rag-question')
    if (ta) ta.focus()
  })
}

async function handleRagQa() {
  const question = app.ragDraft.trim()
  if (!question) return
  try {
    app.ragLoading = true
    app.ragDraft = ''
    const data = await ragApi.ask({ class_id: app.currentClassId, question })
    app.ragLoading = false
    app.ragMessages = data.messages || []
    nextTick(() => {
      if (ragStream.value) ragStream.value.scrollTop = ragStream.value.scrollHeight
    })
  } catch (error) {
    app.ragLoading = false
    app.ragDraft = question
    app.setStatus(error.message, 'error')
  }
}

async function clearRag() {
  try {
    await ragApi.clear({ class_id: app.currentClassId })
    app.ragMessages = []
    app.ragDraft = ''
    app.setStatus('问答记录已清空。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
