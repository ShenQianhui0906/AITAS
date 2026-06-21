<template>
  <div id="floating-ui">
    <ToastNotification
      v-if="app.status"
      :message="app.status"
      :type="app.statusType"
      @dismiss="app.setStatus('')"
    />
    <DialogModal
      v-if="app.dialog"
      :config="app.dialog"
      @confirm="onDialogConfirm"
      @cancel="onDialogCancel"
    />
  </div>

  <div v-if="!auth.isLoggedIn" class="page-shell auth-shell">
    <AuthPage />
  </div>

  <div v-else class="page-shell app-shell" :class="workspaceClasses">
    <AppSidebar
      :routes="currentRoutes"
      :active-route="app.route"
      :user-initial="auth.userInitial"
      :display-name="auth.displayName"
      :role="auth.role"
      @navigate="onNavigate"
      @logout="onLogout"
    />

    <section class="workspace" :class="workspaceFocusClasses">
      <AppHeader
        v-if="!isImmersive"
        :kicker="pageMeta.kicker"
        :title="pageMeta.title"
        :description="pageMeta.description"
        :user="auth.user"
        :role-label="roleLabel(auth.role)"
        :current-class="app.currentClass"
        :classes="app.classes"
        :current-class-id="app.currentClassId"
        :show-toolbar="showOverviewToolbar"
        @switch-class="onSwitchClass"
        @open-messages="onOpenMessages"
      />
      <div id="content-area" class="workspace-content" :class="workspaceContentClasses">
        <router-view />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './store/auth'
import { useAppStore } from './store/app'
import ToastNotification from './components/ToastNotification.vue'
import DialogModal from './components/DialogModal.vue'
import AppSidebar from './components/AppSidebar.vue'
import AppHeader from './components/AppHeader.vue'
import AuthPage from './pages/AuthPage.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const app = useAppStore()

let dialogResolve = null

const pageMetaForRole = {
  admin: {
    overview: { kicker: '管理员', title: '平台总览', description: '平台管理中心' },
    users: { kicker: '管理员', title: '用户管理', description: '教师与学生账号' },
    classes: { kicker: '管理员', title: '班级管理', description: '班级与成员' },
    coursewares: { kicker: '管理员', title: '课件管理', description: '平台课件资源' },
  },
  teacher: {
    overview: { kicker: '教师端', title: '教学总览', description: '班级与教学状态' },
    classes: { kicker: '教师端', title: '班级管理', description: '班级与成员' },
    coursewares: { kicker: '教师端', title: '课件管理', description: '班级课件' },
    evaluations: { kicker: '教师端', title: '反馈分析', description: '课件反馈' },
    discussions: { kicker: '教师端', title: '讨论区', description: '主题交流' },
    rag: { kicker: '教师端', title: '知识库问答', description: '跨课件 RAG 智能问答' },
    messages: { kicker: '教师端', title: '消息中心', description: '会话与消息' },
  },
  student: {
    overview: { kicker: '学生端', title: '学习总览', description: '当前班级学习入口' },
    classes: { kicker: '学生端', title: '班级列表', description: '加入与切换班级' },
    coursewares: { kicker: '学生端', title: '课件学习', description: '课件阅读与问答' },
    survey: { kicker: '学生端', title: '使用反馈', description: '课件评价' },
    discussions: { kicker: '学生端', title: '讨论区', description: '课程讨论' },
    rag: { kicker: '学生端', title: '知识库问答', description: '跨课件 RAG 智能问答' },
    messages: { kicker: '学生端', title: '消息中心', description: '班级会话' },
  },
}

const currentRoutes = computed(() => app.routeMap[auth.role] || [])
const pageMeta = computed(() => pageMetaForRole[auth.role]?.[app.route] || { kicker: '', title: '', description: '' })
const isImmersive = computed(() => {
  const isCW = app.route === 'coursewares' && ['student', 'teacher'].includes(auth.role)
  const isMsg = app.route === 'messages'
  return isCW || isMsg
})
const isCoursewareFocus = computed(() => app.route === 'coursewares' && ['student', 'teacher'].includes(auth.role))
const isMessageFocus = computed(() => app.route === 'messages')
const isDiscussionFocus = computed(() => app.route === 'discussions')
const isOverviewFocus = computed(() => app.route === 'overview')
const showOverviewToolbar = computed(() => isOverviewFocus.value && auth.role !== 'admin')

const workspaceClasses = computed(() => ({
  'courseware-page-shell': isCoursewareFocus.value,
  'message-page-shell': isMessageFocus.value,
  'discussion-page-shell': isDiscussionFocus.value,
  'overview-page-shell': isOverviewFocus.value,
}))
const workspaceFocusClasses = computed(() => ({
  'courseware-focus-workspace': isCoursewareFocus.value,
  'message-focus-workspace': isMessageFocus.value,
  'discussion-focus-workspace': isDiscussionFocus.value,
  'overview-focus-workspace': isOverviewFocus.value,
}))
const workspaceContentClasses = computed(() => ({
  'message-workspace-content': isMessageFocus.value,
  'discussion-workspace-content': isDiscussionFocus.value,
  'overview-workspace-content': isOverviewFocus.value,
}))

function roleLabel(role) {
  if (role === 'admin') return '管理员'
  return role === 'teacher' ? '教师' : '学生'
}

function onDialogConfirm() {
  app.clearDialog()
  if (dialogResolve) { dialogResolve(true); dialogResolve = null }
}
function onDialogCancel() {
  app.clearDialog()
  if (dialogResolve) { dialogResolve(false); dialogResolve = null }
}
window._aitasDialogResolve = (v) => { if (dialogResolve) { dialogResolve(v); dialogResolve = null } }
window._aitasSetDialogResolver = (fn) => { dialogResolve = fn }

async function onNavigate(routeId) {
  app.closeSheet()
  app.aiDrawerOpen = false
  app.route = routeId
  app.setStatus('')
  await router.push({ name: routeId })
}

async function onLogout() {
  await auth.logout()
  app.stopMessagePolling()
  app.closeSheet()
  app.aiDrawerOpen = false
  app.route = 'overview'
  app.messageEventCursor = 0
  router.push({ name: 'overview' })
}

async function onSwitchClass(classId) {
  app.currentClassId = Number(classId) || null
  app.persistCurrentClass()
  await router.go(0)
}

function onOpenMessages() {
  app.route = 'messages'
  router.push({ name: 'messages' })
}

watch(() => route.name, (name) => {
  if (name && name !== 'messages') {
    app.stopMessagePolling()
  }
  app.route = name || 'overview'
  if (!['coursewares'].includes(name)) {
    app.aiDrawerOpen = false
  }
})

onMounted(async () => {
  await auth.bootstrap()
  if (auth.isLoggedIn) {
    app.route = route.name || 'overview'
    await app.loadClasses()
  }
})

onUnmounted(() => {
  app.stopMessagePolling()
})
</script>
