<template>
  <aside class="sidebar rail-shell" aria-label="主导航">
    <div class="rail-top">
      <button class="brand-mark rail-brand" type="button" title="AI 助教系统">
        <img class="rail-logo" src="../assets/cufe-logo.png" alt="CUFE" />
      </button>
      <nav class="nav-list slim-rail">
        <button
          v-for="item in routes"
          :key="item.id"
          class="nav-btn rail-btn"
          :class="{ active: activeRoute === item.id }"
          :title="item.label"
          :data-tooltip="item.label"
          :aria-label="item.label"
          type="button"
          @click="$emit('navigate', item.id)"
        >
          <span class="nav-indicator"></span>
          <span class="nav-icon" v-html="routeIcon(item.id)"></span>
          <span v-if="item.id === 'notifications' && unreadCount > 0" class="nav-badge">{{ unreadCount }}</span>
          <span class="sr-only">{{ item.label }}</span>
        </button>
      </nav>
    </div>
    <div class="rail-bottom">
      <div
        class="rail-profile"
        :title="`${displayName} · ${roleLabelText}`"
      >
        <span>{{ userInitial }}</span>
      </div>
      <button
        class="rail-logout"
        type="button"
        title="退出登录"
        aria-label="退出登录"
        @click="$emit('logout')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <path d="m16 17 5-5-5-5"></path>
          <path d="M21 12H9"></path>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../store/app'
import { navigationIcon } from '../utils/navigationIcons'

defineProps({
  routes: { type: Array, required: true },
  activeRoute: { type: String, required: true },
  userInitial: { type: String, default: 'U' },
  displayName: { type: String, default: '' },
  role: { type: String, default: '' },
})
defineEmits(['navigate', 'logout'])

const roleLabelText = {
  admin: '管理员',
  teacher: '教师',
  student: '学生',
}

function routeIcon(id) {
  return navigationIcon(id)
}

const store = useAppStore()
const unreadCount = computed(() => store.unreadNotificationCount)
</script>
