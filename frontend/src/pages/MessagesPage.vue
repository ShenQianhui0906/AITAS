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
        <ChatBubble v-for="(m, i) in app.threadMessages" :key="m.id || i" :message="m" />
      </div>
      <div class="prompt-shell messages-composer-shell">
        <form class="form-grid chat-composer" @submit.prevent="handleSend">
          <div class="field prompt-field">
            <label for="msg-body">消息内容</label>
            <textarea id="msg-body" v-model="draft" placeholder="输入你的消息"></textarea>
          </div>
          <div class="button-row prompt-actions">
            <button class="secondary-btn" type="button" @click="stopMessagePolling">停止同步</button>
            <button class="primary-btn send-btn" type="submit">发送消息</button>
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
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { messagesApi } from '../api'
import { roleLabel } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import ChatBubble from '../components/ChatBubble.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const contacts = ref([])
const activeUserId = ref(null)
const draft = ref('')
const chatStream = ref(null)

function contactList(users) {
  return (users || []).filter((u) => u.id !== auth.user?.id).map((u) => ({
    ...u,
    initial: (u.display_name || u.username || '?')[0].toUpperCase(),
  }))
}

async function load() {
  loading.value = true
  try {
    const [usersData, convsData] = await Promise.all([
      messagesApi.contacts({ class_id: app.currentClassId }),
      messagesApi.conversations({ class_id: app.currentClassId }),
    ])
    contacts.value = contactList(usersData.users)
    app.setStatus('')
    app.conversations = convsData.conversations || []
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

async function startConversation(user) {
  activeUserId.value = user.id
  try {
    const data = await messagesApi.createConversation({ with_user_id: user.id, class_id: app.currentClassId })
    const conv = data.conversation
    if (!app.conversations.find((c) => c.id === conv.id)) {
      app.conversations.push(conv)
    }
    app.activeConversationId = conv.id
    await app.syncMessagesSilently(conv.id)
    app.ensureMessagePolling()
    scrollToBottom()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function openConversation(conv) {
  app.activeConversationId = conv.id
  await app.syncMessagesSilently(conv.id)
  app.ensureMessagePolling()
  scrollToBottom()
}

async function handleSend() {
  const text = draft.value.trim()
  if (!text || !app.activeConversationId) return
  try {
    draft.value = ''
    await messagesApi.send(app.activeConversationId, { body: text })
    await app.syncMessagesSilently(app.activeConversationId)
    scrollToBottom()
  } catch (error) {
    app.setStatus(error.message, 'error')
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
