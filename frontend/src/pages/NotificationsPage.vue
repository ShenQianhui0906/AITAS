<template>
  <div class="page-root">
    <SectionTitle title="通知中心" subtitle="系统通知与提醒">
      <template #actions>
        <div class="notif-toolbar">
          <button v-if="unreadTotal > 0" class="btn-primary btn-sm" @click="markAllRead">全部已读</button>
        </div>
      </template>
    </SectionTitle>

    <div v-if="notifications.length === 0 && !loading" class="empty-wrap">
      <EmptyState icon="notif" message="暂无通知" />
    </div>

    <div v-else class="notif-list">
      <div
        v-for="n in notifications"
        :key="n.id"
        class="notif-row"
        :class="{ unread: !n.is_read }"
        @click="openNotif(n)"
      >
        <div class="notif-dot" :class="n.is_read ? 'gray' : 'blue'"></div>
        <div class="notif-body">
          <strong>{{ n.title }}</strong>
          <p>{{ n.body }}</p>
        </div>
        <span class="notif-time">{{ fmtTime(n.created_at) }}</span>
      </div>
    </div>

    <LoadingSpinner v-if="loading" />
    <ToastNotification ref="toast" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../store/app'
import { notificationApi } from '../api'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import ToastNotification from '../components/ToastNotification.vue'

const app = useAppStore()
const router = useRouter()
const notifications = ref([])
const loading = ref(false)
const toast = ref(null)

const unreadTotal = computed(() => app.unreadNotificationCount)

onMounted(load)

watch(() => app.unreadNotificationCount, (count, previousCount) => {
  if (count > previousCount) load(false)
})

async function load(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const res = await notificationApi.list({ limit: 50 })
    notifications.value = res.notifications || []
  } catch (e) {
    console.error('load notifications error', e)
  } finally {
    if (showLoading) loading.value = false
    app.refreshUnreadCount()
  }
}

async function openNotif(n) {
  if (!n.is_read) {
    try {
      await notificationApi.markRead(n.id)
      n.is_read = 1
      app.refreshUnreadCount()
    } catch { /* ignore */ }
  }
  // 使用 ref_type + ref_id 导航到对应页面
  const routeMap = {
    'quiz': { name: 'quizzes', param: 'quiz_id' },
    'assignment': { name: 'assignments', param: 'aid' },
    'rag': { name: 'rag', param: 'class_id' },
    'message': { name: 'messages', param: 'cid' },
    'courseware': { name: 'coursewares', param: 'courseware_id' },
    'feedback': { name: 'evaluations', param: 'courseware_id' },
  }
  const route = routeMap[n.ref_type]
  if (route && n.ref_id) {
    router.push({ name: route.name, query: { [route.param]: n.ref_id } })
  }
}

async function markAllRead() {
  try {
    await notificationApi.markAllRead()
    notifications.value.forEach(n => { n.is_read = 1 })
    app.refreshUnreadCount()
    toast.value?.show('已全部标记为已读', 'ok')
  } catch (e) {
    toast.value?.show('操作失败', 'error')
  }
}

function fmtTime(d) {
  if (!d) return ''
  const dt = new Date(d)
  const now = new Date()
  const diff = now - dt
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return dt.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>
