<template>
  <LoadingSpinner v-if="loading" />

  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle title="暂无班级" />
    <p class="empty-copy">先在班级页创建或加入班级，再使用班内消息。</p>
    <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
  </div>

  <section v-else class="messages-layout">
    <!-- Contacts Panel -->
    <aside class="contacts-panel card-messages-sidebar">
      <div class="card-messages-sidebar-header">
        <h3>班内成员</h3>
      </div>
      <ul class="contacts-list">
        <EmptyState v-if="!contacts.length" message="暂无成员" />
        <li
          v-for="c in contacts"
          :key="c.id"
          class="contacts-item"
          :class="{ active: c.id === activeUserId }"
          role="button"
          tabindex="0"
          @click="startConversation(c)"
          @keydown.enter="startConversation(c)"
        >
          <div class="contacts-avatar">{{ c.initial }}</div>
          <div class="contacts-copy">
            <strong>{{ c.display_name }}</strong>
            <span class="soft-label">{{ roleLabel(c.role) }}</span>
          </div>
        </li>
      </ul>
    </aside>

    <!-- Conversations -->
    <aside class="conversations-panel card-conversations-sidebar" :class="{ 'no-conversation': !app.conversations.length }">
      <div class="card-conversations-header message-sidebar-header-with-recipients">
        <h3>会话</h3>
      </div>
      <ul class="contacts-list conversations-list">
        <EmptyState v-if="!app.conversations.length" message="尚未开始任何会话" />
        <li
          v-for="conv in app.conversations"
          :key="conv.id"
          class="contacts-item"
          :class="{ active: conv.id === app.activeConversationId }"
          role="button"
          tabindex="0"
          @click="openConversation(conv)"
          @keydown.enter="openConversation(conv)"
        >
          <div class="contacts-avatar">{{ conv.with_user_initial }}</div>
          <div class="contacts-copy">
            <strong>{{ conv.with_user_name }}</strong>
          </div>
        </li>
      </ul>
    </aside>

    <!-- Chat Area -->
    <section v-if="app.activeConversationId" class="chat-area messages-chat-window">
      <div class="chat-stream messages-chat-stream" ref="chatStream">
        <EmptyState v-if="!app.threadMessages.length" message="暂无消息记录" />
        <DirectMessageBubble
          v-for="(m, i) in app.threadMessages"
          :key="m.id || i"
          :message="m"
          :current-user-id="auth.user?.id"
          :other-user-name="activeConversation?.with_user_name || '对方'"
        />
      </div>
      <div class="prompt-shell messages-composer-shell">
        <form class="form-grid chat-composer" @submit.prevent="handleSend">
          <div class="field prompt-field">
            <label for="msg-body">消息内容</label>
            <textarea id="msg-body" v-model="draft" placeholder="输入你的消息"></textarea>
          </div>
          <div class="button-row prompt-actions">
            <button class="secondary-btn" type="button" @click="stopMessagePolling">停止同步</button>
            <button class="primary-btn send-btn" type="submit" :disabled="sending || !draft.trim()">
              {{ sending ? '发送中…' : '发送消息' }}
            </button>
          </div>
        </form>
        <small class="soft-label">消息通过长轮询自动同步</small>
      </div>
    </section>

    <article v-else class="empty-state-wrap no-conversation-panel surface">
      <EmptyState message="选择一个会话开始聊天" />
    </article>
  </section>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { messagesApi } from '../api'
import { roleLabel } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import DirectMessageBubble from '../components/DirectMessageBubble.vue'

const auth = useAuthStore()
const app = useAppStore()
const route = useRoute()
const loading = ref(true)
const sending = ref(false)
const contacts = ref([])
const activeUserId = ref(null)
const draft = ref('')
const chatStream = ref(null)
const activeConversation = computed(() => (
  app.conversations.find((conversation) => conversation.id === app.activeConversationId) || null
))

function contactList(users) {
  return (users || []).filter((u) => u.id !== auth.user?.id).map((u) => ({
    ...u,
    initial: (u.display_name || u.username || '?')[0].toUpperCase(),
  }))
}

async function load() {
  loading.value = true
  if (!app.currentClassId) {
    contacts.value = []
    app.conversations = []
    app.activeConversationId = null
    app.threadMessages = []
    loading.value = false
    return
  }
  try {
    const [usersData, convsData] = await Promise.all([
      messagesApi.contacts({ class_id: app.currentClassId }),
      messagesApi.conversations({ class_id: app.currentClassId }),
    ])
    contacts.value = contactList(usersData.contacts)
    app.setStatus('')
    app.conversations = convsData.conversations || []
    const requestedConversationId = Number(route.query.cid || 0) || null
    const nextConversationId = requestedConversationId || app.activeConversationId
    const active = app.conversations.find((conversation) => conversation.id === nextConversationId)
    if (active) {
      app.activeConversationId = active.id
      activeUserId.value = active.other_user?.id || null
      const threadData = await messagesApi.thread(active.id)
      app.threadMessages = threadData.messages || []
      scrollToBottom()
    } else {
      app.activeConversationId = null
      activeUserId.value = null
      app.threadMessages = []
    }
    app.ensureMessagePolling()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

async function startConversation(user) {
  activeUserId.value = user.id
  try {
    const data = await messagesApi.addConversation({ user_id: user.id })
    // Backend returns { thread_id, other_user, messages: [] }
    const conv = {
      id: data.thread_id,
      other_user: data.other_user,
      with_user_name: data.other_user?.display_name || user.display_name,
      with_user_initial: (data.other_user?.display_name || user.display_name || '?')[0].toUpperCase(),
      last_message: null,
      unread_count: 0,
    }
    if (!app.conversations.find((c) => c.id === conv.id)) {
      app.conversations.push(conv)
    }
    app.activeConversationId = conv.id
    await app.syncMessagesSilently()
    app.ensureMessagePolling()
    scrollToBottom()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function openConversation(conv) {
  app.activeConversationId = conv.id
  activeUserId.value = conv.other_user?.id || null
  await app.syncMessagesSilently()
  app.ensureMessagePolling()
  scrollToBottom()
}

async function handleSend() {
  const text = draft.value.trim()
  if (!text || !app.activeConversationId || sending.value) return
  const conv = app.conversations.find(c => c.id === app.activeConversationId)
  const receiverId = conv?.other_user?.id
  if (!receiverId) return
  sending.value = true
  try {
    draft.value = ''
    const data = await messagesApi.send({ receiver_id: receiverId, body: text })
    if (data.sent_message && data.thread_id === app.activeConversationId) {
      const alreadyShown = app.threadMessages.some((message) => message.id === data.sent_message.id)
      if (!alreadyShown) app.threadMessages.push(data.sent_message)
    }
    scrollToBottom()
    await app.syncMessagesSilently()
    scrollToBottom()
  } catch (error) {
    draft.value = text
    app.setStatus(error.message, 'error')
  } finally {
    sending.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatStream.value) chatStream.value.scrollTop = chatStream.value.scrollHeight
  })
}

const stopMessagePolling = () => app.stopMessagePolling()

onMounted(load)
watch(() => app.currentClassId, load)
onUnmounted(() => app.stopMessagePolling())
</script>
