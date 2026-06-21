<template>
  <LoadingSpinner v-if="loading" />

  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle title="暂无班级" />
    <p class="empty-copy">先在班级页创建或加入班级，再参与讨论。</p>
    <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
  </div>

  <section v-else class="discussion-page-layout">
    <!-- Detail View -->
    <template v-if="activeDiscussion">
      <article class="surface section-shell discussion-detail-panel">
        <div class="discussion-detail-body">
          <aside class="discussion-body-card">
            <div class="discussion-side-top">
              <button class="ghost-btn slim-btn" @click="activeDiscussion = null">返回列表</button>
              <button class="secondary-btn slim-btn" @click="showSheet = true">发布主题</button>
            </div>
            <div class="discussion-side-meta">
              <span class="soft-badge">当前主题</span>
              <div class="discussion-side-title">{{ activeDiscussion.title }}</div>
              <div class="discussion-side-chip-row">
                <span class="soft-badge">{{ activeDiscussion.author_role === 'teacher' ? '教师' : '学生' }}</span>
                <strong>{{ activeDiscussion.author_name }}</strong>
              </div>
              <div class="discussion-side-stats">
                <time>{{ activeDiscussion.created_at }}</time>
                <span class="soft-badge">{{ activeDiscussion.replies?.length || 0 }} 条回复</span>
              </div>
            </div>
            <div class="discussion-body-block">
              <span class="discussion-body-kicker">主题内容</span>
              <div class="discussion-body-content">{{ activeDiscussion.body }}</div>
            </div>
          </aside>
          <section class="discussion-reply-shell">
            <div class="discussion-reply-toolbar-line">
              <SectionTitle title="主题回复" :subline="`${activeDiscussion.replies?.length || 0} 条回复`" />
            </div>
            <div class="reply-list discussion-reply-list">
              <div v-if="!activeDiscussion.replies?.length" class="subtle-text">暂无回复</div>
              <div v-for="r in activeDiscussion.replies" :key="r.id" class="reply-item discussion-reply-item">
                <div class="card-line">
                  <strong>{{ r.author_name }}</strong>
                  <span>{{ r.created_at || '' }}</span>
                </div>
                <span>{{ r.body }}</span>
              </div>
            </div>
            <form class="reply-form discussion-detail-form" @submit.prevent="handleReply">
              <input v-model="replyBody" placeholder="输入回复内容" />
              <button class="primary-btn" type="submit">发送回复</button>
            </form>
          </section>
        </div>
      </article>
    </template>

    <!-- List View -->
    <article v-else class="surface section-shell discussion-list-panel">
      <div class="section-toolbar">
        <SectionTitle title="讨论列表" />
        <div class="button-row">
          <button class="primary-btn" @click="showSheet = true">发布主题</button>
        </div>
      </div>
      <div class="list-stack separated-list discussion-topic-list teacher-scroll-list">
        <EmptyState v-if="!discussions.length" message="当前没有讨论内容" />
        <article
          v-for="d in discussions"
          :key="d.id"
          class="discussion-topic-card"
          role="button"
          tabindex="0"
          @click="activeDiscussion = d"
          @keydown.enter="activeDiscussion = d"
        >
          <div class="resource-head">
            <div>
              <h4>{{ d.title }}</h4>
              <span>{{ d.author_name }} · {{ d.author_role === 'teacher' ? '教师' : '学生' }}</span>
            </div>
            <time>{{ d.created_at }}</time>
          </div>
          <p>{{ truncateText(d.body, 140) }}</p>
          <div class="discussion-topic-foot">
            <span class="soft-badge">{{ d.replies?.length || 0 }} 条回复</span>
            <button class="secondary-btn slim-btn" @click.stop="activeDiscussion = d">查看主题</button>
          </div>
        </article>
      </div>
    </article>

    <SheetPanel
      v-if="showSheet"
      eyebrow="发布主题"
      title="创建新的讨论内容"
      description="发布后班级内师生都可以查看并继续回复。"
      @close="showSheet = false"
    >
      <form class="form-grid" @submit.prevent="handleCreate">
        <div class="field">
          <label for="disc-title">标题</label>
          <input id="disc-title" v-model="form.title" placeholder="输入标题" required />
        </div>
        <div class="field">
          <label for="disc-body">内容</label>
          <textarea id="disc-body" v-model="form.body" placeholder="输入讨论内容" required></textarea>
        </div>
        <div class="button-row sheet-actions">
          <button class="primary-btn" type="submit">发布主题</button>
          <button class="ghost-btn" type="button" @click="showSheet = false">取消</button>
        </div>
      </form>
    </SheetPanel>
  </section>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { discussionsApi } from '../api'
import { truncateText } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import SheetPanel from '../components/SheetPanel.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const showSheet = ref(false)
const discussions = ref([])
const activeDiscussion = ref(null)
const replyBody = ref('')

const form = reactive({ title: '', body: '' })

async function load() {
  loading.value = true
  try {
    const data = await discussionsApi.list({ class_id: app.currentClassId })
    discussions.value = data.discussions
    app.discussions = data.discussions
    if (!discussions.value.find((d) => d.id === app.activeDiscussionId)) {
      app.activeDiscussionId = null
    }
    activeDiscussion.value = discussions.value.find((d) => d.id === app.activeDiscussionId) || null
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

async function handleCreate() {
  try {
    app.setStatus('发布中...')
    await discussionsApi.create({ ...form, class_id: app.currentClassId })
    showSheet.value = false
    form.title = ''
    form.body = ''
    app.setStatus('主题已发布。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function handleReply() {
  if (!replyBody.value.trim() || !activeDiscussion.value) return
  try {
    await discussionsApi.reply(activeDiscussion.value.id, { body: replyBody.value.trim() })
    replyBody.value = ''
    app.setStatus('回复已发布。')
    const data = await discussionsApi.list({ class_id: app.currentClassId })
    discussions.value = data.discussions
    activeDiscussion.value = discussions.value.find((d) => d.id === activeDiscussion.value.id) || null
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
