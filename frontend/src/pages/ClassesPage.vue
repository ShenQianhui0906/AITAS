<template>
  <LoadingSpinner v-if="loading" />

  <!-- ==================== ADMIN ==================== -->
  <section v-else-if="auth.role === 'admin'" class="admin-split-layout admin-class-layout">
    <aside class="admin-side-stack">
      <article class="surface section-shell admin-context-card admin-class-switcher">
        <div class="section-toolbar">
          <SectionTitle title="全部班级" />
          <div class="button-row">
            <button class="primary-btn" @click="openCreateSheet">新建班级</button>
            <button v-if="app.currentClass" class="secondary-btn" @click="openEditSheet">编辑当前班级</button>
            <button v-if="app.currentClass" class="danger-btn" @click="confirmDeleteClass">删除当前班级</button>
          </div>
        </div>
        <div class="class-card-rail teacher-class-rail">
          <EmptyState v-if="!app.classes.length" message="还没有班级" />
          <article
            v-for="c in app.classes"
            :key="c.id"
            class="class-tile"
            :class="{ active: c.id === app.currentClass?.id }"
          >
            <div class="row-main class-tile-main">
              <div class="card-line">
                <strong>{{ c.name }}</strong>
                <span v-if="c.pending_request_count" class="request-pill pending">{{ c.pending_request_count }} 条待审</span>
              </div>
              <span>{{ c.teacher_name }} · {{ c.student_count }} 名学生</span>
              <small>{{ c.description || '暂无班级说明' }}</small>
            </div>
            <div class="row-actions">
              <button class="secondary-btn slim-btn" @click="switchClass(c.id)">
                {{ c.id === app.currentClass?.id ? '当前班级' : '切换' }}
              </button>
            </div>
          </article>
        </div>
      </article>
    </aside>

    <section class="admin-main-stack">
      <ClassDetailAdmin
        :current-class="app.currentClass"
        :members-data="membersData"
        @approve="handleApprove"
        @reject="handleReject"
        @remove="handleRemoveMember"
        @add="handleAddMember"
      />
    </section>

    <SheetPanel
      v-if="sheetMode === 'create'"
      eyebrow="新建班级"
      title="创建新的教学班级"
      description="创建班级并指定授课教师。"
      @close="closeSheet"
    >
      <ClassForm :mode="'create'" :teacher-options="teacherOptions" @submit="handleCreateClass" @cancel="closeSheet" />
    </SheetPanel>
    <SheetPanel
      v-if="sheetMode === 'edit' && app.currentClass"
      eyebrow="编辑班级"
      :title="app.currentClass.name"
      description="更新班级名称、说明及授课教师配置。"
      @close="closeSheet"
    >
      <ClassForm :mode="'edit'" :current-class="app.currentClass" :teacher-options="teacherOptions" @submit="handleUpdateClass" @cancel="closeSheet" />
    </SheetPanel>
  </section>

  <!-- ==================== TEACHER ==================== -->
  <section v-else-if="auth.role === 'teacher'" class="teacher-class-layout">
    <aside class="teacher-class-sidebar">
      <article class="surface section-shell teacher-class-panel teacher-class-switcher">
        <SectionTitle title="我的班级" />
        <div class="button-row">
          <button class="primary-btn" @click="openCreateSheet">新建班级</button>
          <button v-if="app.currentClass" class="secondary-btn" @click="openEditSheet">编辑当前班级</button>
        </div>
        <div class="class-card-rail teacher-class-rail">
          <EmptyState v-if="!app.classes.length" message="你还没有创建任何班级" />
          <article
            v-for="c in app.classes"
            :key="c.id"
            class="class-tile"
            :class="{ active: c.id === app.currentClass?.id }"
          >
            <div class="row-main class-tile-main">
              <div class="card-line">
                <strong>{{ c.name }}</strong>
                <span v-if="c.pending_request_count" class="request-pill pending">{{ c.pending_request_count }} 条待审</span>
              </div>
              <span>{{ c.teacher_name }} · {{ c.student_count }} 名学生</span>
              <small>{{ c.description || '暂无班级说明' }}</small>
            </div>
            <div class="row-actions">
              <button class="secondary-btn slim-btn" @click="switchClass(c.id)">
                {{ c.id === app.currentClass?.id ? '当前班级' : '切换' }}
              </button>
            </div>
          </article>
        </div>
      </article>
    </aside>

    <section class="teacher-class-main">
      <ClassDetailAdmin
        :current-class="app.currentClass"
        :members-data="membersData"
        @approve="handleApprove"
        @reject="handleReject"
        @remove="handleRemoveMember"
        @add="handleAddMember"
      />
    </section>

    <SheetPanel
      v-if="sheetMode === 'create'"
      eyebrow="新建班级"
      title="创建新的教学班级"
      description="创建班级后即可上传课件并管理学生。"
      @close="closeSheet"
    >
      <ClassForm :mode="'create'" :teacher-options="[]" @submit="handleCreateClass" @cancel="closeSheet" />
    </SheetPanel>
    <SheetPanel
      v-if="sheetMode === 'edit' && app.currentClass"
      eyebrow="编辑班级"
      :title="app.currentClass.name"
      description="更新班级名称、说明及授课信息。"
      @close="closeSheet"
    >
      <ClassForm :mode="'edit'" :current-class="app.currentClass" :teacher-options="[]" @submit="handleUpdateClass" @cancel="closeSheet" />
    </SheetPanel>
  </section>

  <!-- ==================== STUDENT ==================== -->
  <section v-else class="student-class-layout">
    <section class="surface section-shell">
      <SectionTitle title="已加入班级" />
      <div class="class-card-rail">
        <EmptyState v-if="!app.classes.length" message="你还没有加入任何班级" />
        <article v-for="c in app.classes" :key="c.id" class="class-tile" :class="{ active: c.id === app.currentClass?.id }">
          <div class="row-main">
            <strong>{{ c.name }}</strong>
            <span>{{ c.teacher_name }} · {{ c.student_count }} 名学生</span>
          </div>
          <div class="row-actions">
            <button class="secondary-btn slim-btn" @click="switchClass(c.id)">切换</button>
            <button class="danger-btn slim-btn" @click="handleLeave(c.id)">退出</button>
          </div>
        </article>
      </div>
    </section>
    <section class="surface section-shell">
      <SectionTitle title="可申请班级" />
      <div class="class-card-rail">
        <EmptyState v-if="!availableClasses.length" message="当前没有可加入的新班级" />
        <article
          v-for="c in availableClasses"
          :key="c.id"
          class="class-tile class-tile-inline class-apply-tile"
        >
          <div class="row-main class-tile-main">
            <strong>{{ c.name }}</strong>
            <span>{{ c.teacher_name }} · {{ c.student_count }} 名学生</span>
          </div>
          <div class="class-tile-side">
            <div class="status-meta class-status-meta">
              <span class="request-pill" :class="c.join_request_status || 'open'">
                {{ joinRequestLabel(c.join_request_status) }}
              </span>
              <small v-if="c.join_requested_at">
                {{ c.join_request_status === 'rejected' ? '最近拒绝' : '申请提交' }} {{ c.join_requested_at }}
              </small>
              <small v-else>提交申请后由教师审核</small>
            </div>
            <div class="row-actions">
              <button
                class="slim-btn"
                :class="c.join_request_status === 'rejected' ? 'secondary-btn' : 'primary-btn'"
                :disabled="c.join_request_status === 'pending'"
                @click="handleJoin(c.id)"
              >
                {{ c.join_request_status === 'pending' ? '审核中' : c.join_request_status === 'rejected' ? '重新申请' : '申请加入' }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { classesApi, usersApi } from '../api'
import { joinRequestLabel } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import MetricCard from '../components/MetricCard.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import SheetPanel from '../components/SheetPanel.vue'
import ClassDetailAdmin from '../components/ClassDetailAdmin.vue'
import ClassForm from '../components/ClassForm.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const sheetMode = ref(null)
const membersData = ref(null)
const availableClasses = ref([])
const teacherOptions = ref([])

async function load() {
  loading.value = true
  try {
    await app.loadClasses()
    if (app.currentClass) {
      membersData.value = await classesApi.members(app.currentClass.id)
    }
    if (auth.role === 'student') {
      const data = await classesApi.available()
      availableClasses.value = data.classes
    }
    if (auth.role === 'admin') {
      const data = await usersApi.list()
      teacherOptions.value = data.users.filter((u) => u.role === 'teacher')
    }
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

function openCreateSheet() { sheetMode.value = 'create' }
function openEditSheet() { sheetMode.value = 'edit' }
function closeSheet() { sheetMode.value = null }

async function switchClass(id) {
  app.currentClassId = Number(id)
  app.persistCurrentClass()
  sheetMode.value = null
  await load()
}

async function handleCreateClass(form) {
  try {
    app.setStatus('创建班级中...')
    await classesApi.create({
      name: form.name,
      description: form.description,
      teacher_id: auth.role === 'admin' ? form.teacher_id : undefined,
    })
    await app.loadClasses()
    app.currentClassId = app.classes[0]?.id || app.currentClassId
    app.persistCurrentClass()
    closeSheet()
    app.setStatus('班级已创建。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function handleUpdateClass(form) {
  try {
    app.setStatus('保存中...')
    await classesApi.update(app.currentClass.id, {
      name: form.name,
      description: form.description,
      teacher_id: auth.role === 'admin' ? form.teacher_id : undefined,
    })
    await app.loadClasses()
    closeSheet()
    app.setStatus('班级信息已更新。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function confirmDeleteClass() {
  const confirmed = await new Promise((resolve) => {
    app.setDialog({
      eyebrow: '班级管理',
      title: '删除当前班级？',
      description: '删除后该班级下的课件、反馈与讨论数据会一并移除。',
      confirmText: '确认删除',
      confirmClass: 'danger-btn',
    })
    window._aitasSetDialogResolver(resolve)
  })
  if (!confirmed) return
  try {
    await classesApi.delete(app.currentClass.id)
    app.currentClassId = null
    app.persistCurrentClass()
    app.setStatus('班级已删除。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function handleApprove(id) {
  try {
    await classesApi.approveRequest(id)
    app.setStatus('已通过入班申请。')
    await load()
  } catch (error) { app.setStatus(error.message, 'error') }
}

async function handleReject(id) {
  try {
    await classesApi.rejectRequest(id)
    app.setStatus('已拒绝入班申请。')
    await load()
  } catch (error) { app.setStatus(error.message, 'error') }
}

async function handleRemoveMember(memberId) {
  try {
    await classesApi.removeMember(app.currentClass.id, memberId)
    app.setStatus('成员已移除。')
    await load()
  } catch (error) { app.setStatus(error.message, 'error') }
}

async function handleAddMember(studentId) {
  try {
    await classesApi.addMember(app.currentClass.id, studentId)
    app.setStatus('学生已加入班级。')
    await load()
  } catch (error) { app.setStatus(error.message, 'error') }
}

async function handleJoin(classId) {
  try {
    await classesApi.join({ class_id: classId })
    app.setStatus('申请已提交，等待教师审核。')
    await load()
  } catch (error) { app.setStatus(error.message, 'error') }
}

async function handleLeave(classId) {
  try {
    await classesApi.removeMember(classId, auth.user.id)
    if (app.currentClassId === Number(classId)) {
      app.currentClassId = null
      app.persistCurrentClass()
    }
    app.setStatus('已退出班级。')
    await load()
  } catch (error) { app.setStatus(error.message, 'error') }
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
