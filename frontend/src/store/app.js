import { defineStore } from 'pinia'
import {
  classesApi, coursewaresApi, evaluationsApi, discussionsApi,
  messagesApi, aiApi, ragApi, dashboardApi, usersApi,
} from '../api'

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const useAppStore = defineStore('app', {
  state: () => ({
    // Navigation
    route: 'overview',

    // Toast / status
    status: '',
    statusType: '',
    statusTimer: null,

    // Dialog
    dialog: null,

    // Sheet
    sheet: null,

    // AI Drawer (student courseware page)
    aiDrawerOpen: false,

    // Data
    coursewares: [],
    dashboard: null,
    evaluations: [],
    discussions: [],
    classes: [],
    availableClasses: [],
    currentClassId: Number(localStorage.getItem('ai_tutor_current_class') || 0) || null,
    users: [],
    conversations: [],

    // Courseware focus
    activeCoursewareId: null,
    editingCoursewareId: null,
    editingManagedUserId: null,

    // Messages
    activeConversationId: null,
    threadMessages: [],
    messageSyncEnabled: false,
    messageSyncLoop: null,
    messageSyncAbortController: null,
    messageEventCursor: 0,

    // AI Q&A
    qaMessages: [],
    qaLoading: false,
    qaDraft: '',

    // RAG
    ragMessages: [],
    ragLoading: false,
    ragDraft: '',
    ragIndexStatus: null,

    // Discussions
    activeDiscussionId: null,
  }),

  getters: {
    routeMap: () => ({
      admin: [
        { id: 'overview', label: '总览' },
        { id: 'users', label: '用户' },
        { id: 'classes', label: '班级' },
        { id: 'coursewares', label: '课件' },
      ],
      teacher: [
        { id: 'overview', label: '总览' },
        { id: 'classes', label: '班级' },
        { id: 'coursewares', label: '课件' },
        { id: 'rag', label: '知识库' },
        { id: 'evaluations', label: '反馈' },
        { id: 'discussions', label: '讨论' },
        { id: 'messages', label: '私信' },
      ],
      student: [
        { id: 'overview', label: '总览' },
        { id: 'classes', label: '班级' },
        { id: 'coursewares', label: '课件' },
        { id: 'rag', label: '知识库' },
        { id: 'survey', label: '反馈' },
        { id: 'discussions', label: '讨论' },
        { id: 'messages', label: '私信' },
      ],
    }),

    currentClass(state) {
      return state.classes.find((c) => c.id === state.currentClassId) || state.classes[0] || null
    },

    currentCourseware(state) {
      return state.coursewares.find((c) => c.id === state.activeCoursewareId) || state.coursewares[0] || null
    },
  },

  actions: {
    setStatus(message = '', type = '') {
      if (this.statusTimer) {
        clearTimeout(this.statusTimer)
        this.statusTimer = null
      }
      this.status = message
      this.statusType = type
      if (message) {
        this.statusTimer = setTimeout(() => {
          this.status = ''
          this.statusType = ''
        }, type === 'error' ? 4200 : 2600)
      }
    },

    // Dialog
    setDialog(config) {
      this.dialog = config
    },
    clearDialog() {
      this.dialog = null
    },

    // Sheet
    closeSheet() {
      this.sheet = null
      this.editingManagedUserId = null
      this.editingCoursewareId = null
    },

    // Classes
    persistCurrentClass() {
      if (this.currentClassId) {
        localStorage.setItem('ai_tutor_current_class', String(this.currentClassId))
      } else {
        localStorage.removeItem('ai_tutor_current_class')
      }
    },

    async loadClasses() {
      const data = await classesApi.list()
      this.classes = data.classes
      if (!this.classes.find((c) => c.id === this.currentClassId)) {
        this.currentClassId = this.classes[0]?.id || null
        this.persistCurrentClass()
      }
    },

    // Messages
    stopMessagePolling() {
      this.messageSyncEnabled = false
      if (this.messageSyncAbortController) {
        this.messageSyncAbortController.abort()
        this.messageSyncAbortController = null
      }
    },

    async runMessageSyncLoop() {
      const router = (await import('../router')).default
      while (this.messageSyncEnabled && router.currentRoute?.value?.name === 'messages') {
        const controller = new AbortController()
        this.messageSyncAbortController = controller
        try {
          const data = await messagesApi.events({ cursor: this.messageEventCursor, _signal: controller.signal })
          if (!this.messageSyncEnabled || router.currentRoute?.value?.name !== 'messages') break
          if (typeof data.cursor === 'number') this.messageEventCursor = data.cursor
          if (data.changed) await this.syncMessagesSilently()
        } catch (error) {
          if (!this.messageSyncEnabled || error.name === 'AbortError') break
          await sleep(1200)
        } finally {
          if (this.messageSyncAbortController === controller) {
            this.messageSyncAbortController = null
          }
        }
      }
      this.messageSyncLoop = null
    },

    ensureMessagePolling() {
      if (this.messageSyncLoop) return
      this.messageSyncEnabled = true
      this.messageSyncLoop = this.runMessageSyncLoop()
    },

    async syncMessagesSilently() {
      const router = (await import('../router')).default
      if (router.currentRoute?.value?.name !== 'messages' || !this.currentClassId) return
      const [contactsData, conversationsData] = await Promise.all([
        messagesApi.contacts({ class_id: this.currentClassId }),
        messagesApi.conversations(),
      ])
      this.users = contactsData.contacts
      this.conversations = conversationsData.conversations
      const visibleUsers = this.conversations.map((c) => c.user)
      if (!visibleUsers.find((u) => u.id === this.activeConversationId)) {
        this.activeConversationId = visibleUsers[0]?.id || null
      }
      const target = this.conversations.find((c) => c.user.id === this.activeConversationId)?.user || this.users[0] || null
      if (target) {
        const threadData = await messagesApi.thread(target.id)
        this.threadMessages = threadData.messages
      } else {
        this.threadMessages = []
      }
    },

    // AI Q&A
    async loadAiMessages(coursewareId) {
      const data = await aiApi.messages({ courseware_id: coursewareId })
      this.qaMessages = data.messages
    },
  },
})
