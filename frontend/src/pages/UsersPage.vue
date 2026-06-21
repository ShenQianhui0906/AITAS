<template>
  <LoadingSpinner v-if="loading" />

  <section v-else class="admin-split-layout admin-users-layout">
    <aside class="admin-side-stack">
      <article class="surface section-shell admin-context-card">
        <SectionTitle title="账号总览" />
        <div class="admin-stat-grid">
          <MetricCard :value="teacherCount" label="教师账号" tone="blue" />
          <MetricCard :value="studentCount" label="学生账号" tone="green" />
          <MetricCard :value="managedUsers.length" label="管理总数" tone="amber" />
        </div>
        <div class="admin-note-stack">
          <div class="focus-item compact">
            <strong>管理员账号受保护</strong>
            <span>系统保留的管理员账号不会出现在可编辑列表中，避免误删或误改。</span>
          </div>
          <div class="focus-item compact">
            <strong>学生学号唯一</strong>
            <span>学生账号要求唯一学号，教师账号不会显示该字段。</span>
          </div>
        </div>
        <div class="button-row">
          <button class="primary-btn" @click="openCreateSheet">新建账号</button>
        </div>
      </article>
    </aside>

    <section class="surface section-shell admin-main-panel">
      <div class="section-toolbar">
        <SectionTitle title="账号列表" />
      </div>
      <div class="list-stack separated-list teacher-scroll-list">
        <EmptyState v-if="!managedUsers.length" message="当前没有可管理的教师或学生账号" />
        <article v-for="u in managedUsers" :key="u.id" class="list-row entity-row">
          <div class="row-main">
            <div class="card-line">
              <strong>{{ u.display_name }}</strong>
              <span class="soft-badge">{{ roleLabel(u.role) }}</span>
            </div>
            <span>{{ u.username }}{{ u.student_number ? ` · 学号 ${u.student_number}` : '' }}</span>
            <small>创建于 {{ u.created_at }}</small>
          </div>
          <div class="row-actions">
            <button class="secondary-btn slim-btn" @click="openEditSheet(u)">编辑</button>
            <button class="danger-btn slim-btn" @click="confirmDelete(u)">删除</button>
          </div>
        </article>
      </div>
    </section>

    <!-- Sheet -->
    <SheetPanel
      v-if="showSheet"
      :eyebrow="editing ? '编辑账号' : '新增账号'"
      :title="editing ? editing.display_name : '创建教师或学生账号'"
      :description="editing ? '更新基础信息、角色与登录密码。' : '创建后用户即可使用自己的身份进入系统。'"
      @close="closeSheet"
    >
      <form class="form-grid" @submit.prevent="handleSubmit">
        <div class="field split-field">
          <div class="field">
            <label for="mu-display-name">姓名</label>
            <input id="mu-display-name" v-model="form.display_name" required />
          </div>
          <div class="field">
            <label for="mu-username">用户名</label>
            <input id="mu-username" v-model="form.username" required />
          </div>
        </div>
        <div class="field split-field">
          <div class="field">
            <label for="mu-role">角色</label>
            <select id="mu-role" v-model="form.role">
              <option value="teacher">教师</option>
              <option value="student">学生</option>
            </select>
          </div>
          <div class="field">
            <label for="mu-password">{{ editing ? '重置密码' : '登录密码' }}</label>
            <input
              id="mu-password"
              v-model="form.password"
              type="password"
              :placeholder="editing ? '留空则保持原密码' : '输入登录密码'"
              :required="!editing"
            />
          </div>
        </div>
        <div class="field" :class="{ hidden: form.role !== 'student' }">
          <label for="mu-student-number">学号</label>
          <input id="mu-student-number" v-model="form.student_number" placeholder="输入学号" />
        </div>
        <div class="button-row sheet-actions">
          <button class="primary-btn" type="submit">{{ editing ? '保存账号' : '创建账号' }}</button>
          <button class="ghost-btn" type="button" @click="closeSheet">取消</button>
        </div>
      </form>
    </SheetPanel>
  </section>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { usersApi } from '../api'
import { roleLabel } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import MetricCard from '../components/MetricCard.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import SheetPanel from '../components/SheetPanel.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const showSheet = ref(false)
const editing = ref(null)

const managedUsers = ref([])
const teacherCount = computed(() => managedUsers.value.filter((u) => u.role === 'teacher').length)
const studentCount = computed(() => managedUsers.value.filter((u) => u.role === 'student').length)

const form = reactive({ display_name: '', username: '', role: 'student', password: '', student_number: '' })

async function load() {
  loading.value = true
  try {
    const data = await usersApi.list()
    app.users = data.users
    managedUsers.value = data.users.filter((u) => u.role !== 'admin')
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

function openCreateSheet() {
  editing.value = null
  Object.assign(form, { display_name: '', username: '', role: 'student', password: '', student_number: '' })
  showSheet.value = true
}

function openEditSheet(user) {
  editing.value = user
  Object.assign(form, {
    display_name: user.display_name,
    username: user.username,
    role: user.role,
    password: '',
    student_number: user.student_number || '',
  })
  showSheet.value = true
}

function closeSheet() {
  showSheet.value = false
  editing.value = null
}

async function handleSubmit() {
  try {
    if (editing.value) {
      await usersApi.update(editing.value.id, { ...form })
      app.setStatus('账号信息已更新。')
    } else {
      await usersApi.create({ ...form })
      app.setStatus('账号已创建。')
    }
    closeSheet()
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function confirmDelete(user) {
  const confirmed = await new Promise((resolve) => {
    app.setDialog({
      eyebrow: '用户管理',
      title: '删除该账号？',
      description: `${user.display_name} 相关的班级归属、课件或沟通记录可能会一并清理，请确认后继续。`,
      confirmText: '确认删除',
      confirmClass: 'danger-btn',
    })
    window._aitasSetDialogResolver(resolve)
  })
  if (!confirmed) return
  try {
    await usersApi.delete(user.id)
    app.editingManagedUserId = null
    await app.loadClasses()
    app.setStatus('账号已删除。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

onMounted(load)
</script>
