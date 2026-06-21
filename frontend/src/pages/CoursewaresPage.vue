<template>
  <LoadingSpinner v-if="loading" />

  <!-- ==================== NO CLASS ==================== -->
  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle :title="auth.role === 'admin' ? '暂无班级' : '暂无班级'" />
    <p class="empty-copy">
      {{ auth.role === 'admin' ? '先在班级页创建班级，再维护课件资源。' : '先在班级页创建或加入班级，再管理课件。' }}
    </p>
    <div class="button-row">
      <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
    </div>
  </div>

  <!-- ==================== ADMIN ==================== -->
  <section v-else-if="auth.role === 'admin'" class="admin-split-layout admin-courseware-layout">
    <aside class="admin-side-stack">
      <article class="surface section-shell admin-context-card">
        <SectionTitle title="课件总览" />
        <div class="admin-stat-grid">
          <MetricCard :value="app.coursewares.length" label="已发布课件" tone="blue" />
          <MetricCard :value="app.currentClass?.name || '-'" label="当前班级" tone="green" />
          <MetricCard :value="app.classes.length" label="班级总数" tone="amber" />
        </div>
        <div class="button-row">
          <button class="primary-btn" @click="openCreateSheet">上传课件</button>
        </div>
      </article>
    </aside>
    <section class="surface section-shell admin-main-panel">
      <div class="section-toolbar">
        <SectionTitle title="班级课件" />
      </div>
      <div class="list-stack separated-list teacher-scroll-list">
        <EmptyState v-if="!app.coursewares.length" message="还没有课件" />
        <CoursewareRow
          v-for="c in app.coursewares"
          :key="c.id"
          :courseware="c"
          :active="c.id === editingCoursewareId"
          @edit="startEdit(c)"
          @delete="confirmDelete(c)"
        />
      </div>
    </section>

    <CoursewareSheet
      v-if="showSheet"
      :editing="editingCourseware"
      @close="closeSheet"
      @submit="handleSubmit"
    />
  </section>

  <!-- ==================== TEACHER ==================== -->
  <section v-else-if="auth.role === 'teacher'" class="teacher-courseware-layout">
    <aside class="teacher-courseware-sidebar">
      <div class="course-sidebar-head course-page-head teacher-courseware-head">
        <span class="eyebrow">教师端</span>
        <h2>课件管理</h2>
        <p>班级课件</p>
        <div class="workspace-summary compact-summary">
          <span class="soft-badge">教师</span>
          <strong>{{ app.currentClass?.name || '当前班级' }}</strong>
        </div>
      </div>
      <article class="surface section-shell teacher-courseware-summary">
        <div class="teacher-courseware-stats">
          <article class="teacher-mini-stat">
            <span>已发布课件</span>
            <strong>{{ app.coursewares.length }}</strong>
          </article>
          <article class="teacher-mini-stat">
            <span>当前班级</span>
            <strong>{{ app.currentClass?.name || '-' }}</strong>
          </article>
        </div>
        <div class="button-row">
          <button class="primary-btn" @click="openCreateSheet">上传课件</button>
        </div>
      </article>
    </aside>
    <section class="surface section-shell teacher-courseware-panel">
      <div class="section-toolbar">
        <SectionTitle title="课件列表" />
      </div>
      <div class="list-stack separated-list teacher-scroll-list teacher-courseware-list">
        <EmptyState v-if="!app.coursewares.length" message="当前班级还没有课件" />
        <CoursewareRow
          v-for="c in app.coursewares"
          :key="c.id"
          :courseware="c"
          :active="c.id === editingCoursewareId"
          @edit="startEdit(c)"
          @delete="confirmDelete(c)"
        />
      </div>
    </section>

    <CoursewareSheet
      v-if="showSheet"
      :editing="editingCourseware"
      @close="closeSheet"
      @submit="handleSubmit"
    />
  </section>

  <!-- ==================== STUDENT ==================== -->
  <section v-else class="course-shell course-learning-layout">
    <section class="course-sidebar-stack">
      <div class="course-sidebar-head course-page-head">
        <span class="eyebrow">学生端</span>
        <h2>课件学习</h2>
        <p>课件阅读与问答</p>
        <div class="workspace-summary compact-summary">
          <span class="soft-badge">学生</span>
          <strong>{{ app.currentClass?.name || '当前班级' }}</strong>
        </div>
      </div>
      <aside class="surface section-shell library-sidebar course-sidebar">
        <div class="course-sidebar-title">
          <strong>课件目录</strong>
          <span>左侧浏览当前班级课件</span>
        </div>
        <div class="list-stack separated-list library-sidebar-list">
          <EmptyState v-if="!app.coursewares.length" message="暂无可查看课件" />
          <button
            v-for="(c, idx) in app.coursewares"
            :key="c.id"
            class="library-list-item"
            :class="{ active: c.id === app.activeCoursewareId }"
            @click="selectCourseware(c)"
          >
            <span class="library-list-index">{{ String(idx + 1).padStart(2, '0') }}</span>
            <span class="library-list-copy">
              <strong>{{ displayCoursewareTitle(c.title) }}</strong>
            </span>
          </button>
        </div>
      </aside>
    </section>

    <!-- Reading + AI Drawer -->
    <section v-if="app.currentCourseware" class="course-reading-stage">
      <article class="reader-panel panel-card">
        <div class="preview-shell">
          <div class="preview-toolbar">
            <span class="preview-label">沉浸阅读区</span>
            <div class="preview-toolbar-actions">
              <a class="ghost-btn slim-btn" :href="app.currentCourseware.viewer_url" target="_blank" rel="noreferrer">新窗口打开</a>
              <button class="primary-btn slim-btn" @click="app.aiDrawerOpen = !app.aiDrawerOpen">
                {{ app.aiDrawerOpen ? '收起 AI 助教' : '✨ 唤醒 AI 助教' }}
              </button>
            </div>
          </div>
          <iframe
            class="courseware-frame"
            :src="app.currentCourseware.viewer_url"
            :title="displayCoursewareTitle(app.currentCourseware.title)"
          ></iframe>
        </div>
        <div class="course-pagination-shell">
          <span class="course-pagination-label">切换课件</span>
          <div class="course-pagination">
            <button
              v-for="(c, idx) in app.coursewares"
              :key="c.id"
              class="course-page-btn"
              :class="{ active: c.id === app.currentCourseware?.id }"
              @click="selectCourseware(c)"
            >
              <span class="page-index">{{ idx + 1 }}</span>
              <span class="page-copy">{{ displayCoursewareTitle(c.title) }}</span>
            </button>
          </div>
        </div>
      </article>

      <button
        class="ai-fab"
        :class="{ hidden: app.aiDrawerOpen }"
        @click="app.aiDrawerOpen = true"
      >✨ 唤醒 AI 助教</button>

      <!-- AI Drawer -->
      <template v-if="app.aiDrawerOpen">
        <div class="ai-drawer-backdrop" @click="app.aiDrawerOpen = false"></div>
        <aside class="assistant-drawer open">
          <div class="assistant-drawer-head">
            <div>
              <span class="eyebrow">AI Tutor</span>
              <h4>围绕当前课件即时提问</h4>
            </div>
            <div class="button-row">
              <span class="soft-badge">GLM 在线</span>
              <button class="toast-close" type="button" @click="app.aiDrawerOpen = false">&times;</button>
            </div>
          </div>
          <div class="ai-assistant-toolbar">
            <div class="suggestion-row">
              <button
                v-for="s in aiSuggestions"
                :key="s"
                class="suggestion-chip"
                @click="setAiDraft(s)"
              >{{ s.replace('请', '').replace('这份课件的', '').replace('。', '') }}</button>
            </div>
            <p class="ai-panel-note">回答会优先结合当前课件内容生成，并自动保留本课件下的问答记录。</p>
          </div>
          <div class="chat-stream" id="ai-chat-stream" ref="aiStream">
            <AiOnboarding v-if="!app.qaMessages.length" />
            <ChatBubble v-for="(m, i) in app.qaMessages" :key="i" :message="m" />
            <article v-if="app.qaLoading" class="chat-entry assistant-entry loading-bubble">
              <div class="chat-message-meta assistant-meta">
                <span class="chat-role-pill assistant">AI 助教</span>
                <time>生成中</time>
              </div>
              <div class="ai-rich-text"><p>正在整理课件内容并生成回答，请稍候...</p></div>
            </article>
          </div>
          <div class="prompt-shell assistant-prompt-shell">
            <form class="form-grid chat-composer" @submit.prevent="handleAiQa">
              <div class="field prompt-field">
                <label for="qa-question">问题内容</label>
                <textarea id="qa-question" v-model="app.qaDraft" placeholder="输入你的问题"></textarea>
              </div>
              <div class="button-row prompt-actions">
                <button class="ghost-btn" type="button" @click="clearAiMessages">清空记录</button>
                <button class="primary-btn send-btn" type="submit" :disabled="app.qaLoading">
                  {{ app.qaLoading ? '生成中...' : '发送问题' }}
                </button>
              </div>
            </form>
          </div>
        </aside>
      </template>
    </section>

    <article v-else class="course-empty-panel panel-card">
      <EmptyState message="选择一份课件后查看详情" />
    </article>
  </section>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { coursewaresApi, aiApi } from '../api'
import { displayCoursewareTitle } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import MetricCard from '../components/MetricCard.vue'
import SheetPanel from '../components/SheetPanel.vue'
import ChatBubble from '../components/ChatBubble.vue'
import AiOnboarding from '../components/AiOnboarding.vue'
import CoursewareRow from '../components/CoursewareRow.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const showSheet = ref(false)
const editingCoursewareId = ref(null)
const aiStream = ref(null)

const editingCourseware = computed(() => app.coursewares.find((c) => c.id === editingCoursewareId.value) || null)

const aiSuggestions = [
  '请总结这份课件的核心内容。',
  '请梳理这份课件的知识结构。',
  '请给出这份课件的学习建议。',
]

async function load() {
  loading.value = true
  try {
    const data = await coursewaresApi.list({ class_id: app.currentClassId })
    app.coursewares = data.coursewares
    if (!app.coursewares.find((c) => c.id === app.activeCoursewareId)) {
      app.activeCoursewareId = app.coursewares[0]?.id || null
    }
    if (auth.role === 'student' && app.currentCourseware) {
      await app.loadAiMessages(app.currentCourseware.id)
    }
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

function openCreateSheet() {
  editingCoursewareId.value = null
  showSheet.value = true
}

function startEdit(c) {
  editingCoursewareId.value = c.id
  showSheet.value = true
}

function closeSheet() {
  showSheet.value = false
  editingCoursewareId.value = null
}

async function handleSubmit(formData) {
  try {
    if (editingCoursewareId.value) {
      app.setStatus('保存中...')
      await coursewaresApi.update(editingCoursewareId.value, formData)
      app.setStatus('课件信息已更新。')
    } else {
      app.setStatus('课件上传中...')
      const fd = new FormData()
      fd.set('class_id', String(app.currentClassId))
      if (formData instanceof FormData) {
        for (const [k, v] of formData.entries()) fd.set(k, v)
      } else {
        Object.entries(formData).forEach(([k, v]) => fd.set(k, v))
      }
      await coursewaresApi.create(fd)
      app.setStatus('课件上传成功。')
    }
    closeSheet()
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function confirmDelete(c) {
  const confirmed = await new Promise((resolve) => {
    app.setDialog({
      eyebrow: '课件操作',
      title: '删除当前课件？',
      description: '删除后该班级下的学生将无法继续查看这份课件，相关反馈记录会一并失效。',
      confirmText: '确认删除',
      confirmClass: 'danger-btn',
    })
    window._aitasSetDialogResolver(resolve)
  })
  if (!confirmed) return
  try {
    await coursewaresApi.delete(c.id)
    editingCoursewareId.value = null
    app.setStatus('课件已删除。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function selectCourseware(c) {
  app.activeCoursewareId = c.id
  app.aiDrawerOpen = false
  await load()
}

function setAiDraft(text) {
  app.qaDraft = text
  nextTick(() => {
    const ta = document.getElementById('qa-question')
    if (ta) ta.focus()
  })
}

async function handleAiQa() {
  const question = app.qaDraft.trim()
  if (!question || !app.currentCourseware) return
  try {
    app.qaLoading = true
    app.qaDraft = ''
    const data = await aiApi.ask({ courseware_id: app.currentCourseware.id, question })
    app.qaLoading = false
    app.qaMessages = data.messages || []
    nextTick(() => {
      if (aiStream.value) aiStream.value.scrollTop = aiStream.value.scrollHeight
    })
  } catch (error) {
    app.qaLoading = false
    app.qaDraft = question
    app.setStatus(error.message, 'error')
  }
}

async function clearAiMessages() {
  if (!app.currentCourseware) return
  try {
    await aiApi.clear({ courseware_id: app.currentCourseware.id })
    app.qaMessages = []
    app.qaDraft = ''
    app.setStatus('问答记录已清空。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
