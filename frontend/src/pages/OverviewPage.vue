<template>
  <LoadingSpinner v-if="loading" />

  <!-- Admin Overview -->
  <section v-else-if="auth.role === 'admin'" class="overview-shell admin-overview-shell">
    <article class="surface hero-panel overview-lead">
      <div class="hero-copy">
        <span class="eyebrow">Platform Control</span>
        <h3>把用户、班级与教学资源收束到一个干净的管理视图里。</h3>
        <p>保留必要信息密度，减少装饰干扰，让平台治理、日常维护和后续功能扩展都落在统一的工作台节奏里。</p>
        <div class="button-row">
          <button class="primary-btn" @click="$router.push({ name: 'users' })">管理用户</button>
          <button class="ghost-btn" @click="$router.push({ name: 'classes' })">管理班级</button>
        </div>
      </div>
      <div class="hero-side">
        <MetricCard :value="dash?.stats?.teachers" label="教师账号" tone="blue" />
        <MetricCard :value="dash?.stats?.students" label="学生账号" tone="green" />
        <MetricCard :value="dash?.stats?.classes" label="班级总数" tone="amber" />
        <MetricCard :value="dash?.stats?.coursewares" label="课件总数" tone="red" />
      </div>
    </article>
  </section>

  <!-- Teacher/Student Overview -->
  <template v-else>
    <div v-if="!app.currentClassId && auth.role === 'teacher'" class="surface empty-surface">
      <SectionTitle title="暂无班级" />
      <p class="empty-copy">先创建班级或加入班级后再开始使用系统。</p>
      <div class="button-row">
        <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
      </div>
    </div>

    <section v-else class="overview-shell learning-overview-shell" :class="auth.role === 'teacher' ? 'teacher-overview-shell' : 'student-overview-shell'">
      <!-- ===== TEACHER ===== -->
      <template v-if="auth.role === 'teacher'">
        <article class="surface hero-panel overview-lead">
          <div class="hero-copy">
            <span class="eyebrow">Teaching Desk</span>
            <h3>{{ app.currentClass?.name || '当前班级' }}</h3>
            <p>课件、反馈、讨论和消息</p>
            <div class="button-row">
              <button class="primary-btn" @click="$router.push({ name: 'coursewares' })">管理课件</button>
              <button class="ghost-btn" @click="$router.push({ name: 'messages' })">查看消息</button>
            </div>
          </div>
          <div class="hero-side">
            <MetricCard :value="dash?.stats?.coursewares" label="课件总数" tone="blue" />
            <MetricCard :value="dash?.stats?.evaluations" label="反馈总数" tone="green" />
            <MetricCard :value="dash?.stats?.discussions" label="讨论主题" tone="amber" />
            <MetricCard :value="dash?.stats?.unread_messages" label="未读消息" tone="red" />
          </div>
        </article>
      </template>

      <!-- ===== STUDENT: Global AI Agent Entry ===== -->
      <template v-else>
        <GlobalAiEntry ref="agentEntry" />
      </template>
    </section>
  </template>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { dashboardApi } from '../api'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import MetricCard from '../components/MetricCard.vue'
import SectionTitle from '../components/SectionTitle.vue'
import GlobalAiEntry from '../components/GlobalAiEntry.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const dash = ref(null)

async function load() {
  loading.value = true
  try {
    if (!app.currentClassId && auth.role !== 'admin') {
      dash.value = { stats: {} }
    } else {
      const params = auth.role !== 'admin' ? { class_id: app.currentClassId } : {}
      dash.value = await dashboardApi.get(params)
    }
  } catch {
    dash.value = { stats: {} }
  }
  loading.value = false
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
