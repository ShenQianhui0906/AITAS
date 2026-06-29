<template>
  <header class="workspace-header minimal-header">
    <div class="workspace-copy">
      <div class="eyebrow">{{ kicker }}</div>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <div v-if="showToolbar" class="overview-toolbar">
      <label class="overview-inline-switch">
        <span class="overview-toolbar-label">当前班级</span>
        <select
          :value="currentClassId"
          aria-label="当前班级"
          @change="$emit('switchClass', $event.target.value)"
        >
          <option
            v-for="c in classes"
            :key="c.id"
            :value="c.id"
            :selected="c.id === currentClassId"
          >
            {{ c.name }}
          </option>
        </select>
      </label>
      <button
        class="icon-btn overview-bell-btn overview-bell-card"
        type="button"
        aria-label="打开消息中心"
        title="打开消息中心"
        @click="$emit('openMessages')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5"></path>
          <path d="M9 17a3 3 0 0 0 6 0"></path>
        </svg>
        <span v-if="unreadTotal > 0" class="bell-badge">{{ unreadTotal > 99 ? '99+' : unreadTotal }}</span>
      </button>
    </div>
  </header>
  <div class="workspace-banner">
    <div class="workspace-summary">
      <span class="soft-badge">{{ roleLabel }}</span>
      <strong>{{ user?.display_name }}</strong>
      <span>{{ currentClass?.name || '未选择班级' }}</span>
    </div>
    <span v-if="user?.role === 'student' && user?.student_number" class="subtle-text">
      学号 {{ user.student_number }}
    </span>
    <span v-else class="subtle-text">{{ user?.username }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../store/app'

const appStore = useAppStore()
const unreadTotal = computed(() => appStore.unreadNotificationCount)

defineProps({
  kicker: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  user: { type: Object, default: null },
  roleLabel: { type: String, default: '' },
  currentClass: { type: Object, default: null },
  classes: { type: Array, default: () => [] },
  currentClassId: { type: [Number, String], default: null },
  showToolbar: { type: Boolean, default: false },
})
defineEmits(['switchClass', 'openMessages'])
</script>
