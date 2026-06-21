<template>
  <aside class="sidebar rail-shell" aria-label="主导航">
    <div class="rail-top">
      <button class="brand-mark rail-brand" type="button" title="AI 助教系统">
        <span>AI</span>
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

const icons = {
  overview: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12.5 12 4l9 8.5"></path><path d="M6.5 10.5V20h11V10.5"></path></svg>`,
  users: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"></path><circle cx="9.5" cy="7.5" r="3.5"></circle><path d="M21 21v-2a4 4 0 0 0-3-3.87"></path><path d="M15 4.13a3.5 3.5 0 0 1 0 6.74"></path></svg>`,
  classes: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7.5 12 3l9 4.5-9 4.5Z"></path><path d="M7 10.5v4.5c0 1.66 2.24 3 5 3s5-1.34 5-3v-4.5"></path></svg>`,
  coursewares: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"></path><path d="M14 3v5h5"></path><path d="M9 13h6"></path><path d="M9 17h6"></path></svg>`,
  evaluations: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20 5.5 23l1.5-7.5L2 10.8l7.8-.9L12 3l2.2 6.9 7.8.9-5 4.7 1.5 7.5Z"></path></svg>`,
  survey: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11h9"></path><path d="M9 16h9"></path><path d="M9 6h9"></path><path d="m5 6 .5.5L7 5"></path><path d="m5 11 .5.5L7 10"></path><path d="m5 16 .5.5L7 15"></path></svg>`,
  discussions: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v10H8l-4 4Z"></path></svg>`,
  messages: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v11H8l-4 4Z"></path></svg>`,
  rag: `<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v4c0 1.66 4.03 3 9 3s9-1.34 9-3V5"></path><path d="M3 9v4c0 1.66 4.03 3 9 3s9-1.34 9-3V9"></path><path d="M3 13v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"></path></svg>`,
}

function routeIcon(id) {
  return icons[id] || icons.overview
}
</script>
