<template>
  <section class="auth-stage">
    <div class="brand-tag">INTELLIGENT COURSE WORKSPACE</div>
    <h1>AI 助教系统</h1>
    <p>课程教学工作台</p>
  </section>
  <section class="auth-card">
    <div class="auth-card-head">
      <div>
        <span class="eyebrow">欢迎使用</span>
        <h2>{{ auth.authMode === 'login' ? '登录账号' : '创建账号' }}</h2>
      </div>
      <div class="tab-switch">
        <button :class="{ active: auth.authMode === 'login' }" @click="auth.setAuthMode('login')">登录</button>
        <button :class="{ active: auth.authMode === 'register' }" @click="auth.setAuthMode('register')">注册</button>
      </div>
    </div>

    <!-- Login Form -->
    <form v-if="auth.authMode === 'login'" class="form-grid auth-form" @submit.prevent="handleLogin">
      <div class="field">
        <label for="login-username">用户名</label>
        <input id="login-username" v-model="loginForm.username" placeholder="输入用户名" required />
      </div>
      <div class="field">
        <label for="login-password">密码</label>
        <input id="login-password" v-model="loginForm.password" type="password" placeholder="输入密码" required />
      </div>
      <button class="primary-btn block-btn" type="submit">进入系统</button>
    </form>

    <!-- Register Form -->
    <form v-else class="form-grid auth-form" @submit.prevent="handleRegister">
      <div class="field">
        <label for="reg-display-name">姓名</label>
        <input id="reg-display-name" v-model="regForm.display_name" placeholder="输入姓名" required />
      </div>
      <div class="field">
        <label for="reg-username">用户名</label>
        <input id="reg-username" v-model="regForm.username" placeholder="输入用户名" required />
      </div>
      <div class="field split-field">
        <div class="field">
          <label for="reg-role">角色</label>
          <select id="reg-role" v-model="regForm.role">
            <option value="student">学生</option>
            <option value="teacher">教师</option>
          </select>
        </div>
        <div class="field">
          <label for="reg-password">密码</label>
          <input id="reg-password" v-model="regForm.password" type="password" placeholder="输入密码" required />
        </div>
      </div>
      <div class="field" :class="{ hidden: regForm.role !== 'student' }">
        <label for="reg-student-number">学号</label>
        <input
          id="reg-student-number"
          v-model="regForm.student_number"
          placeholder="输入学号"
          :required="regForm.role === 'student'"
        />
      </div>
      <button class="primary-btn block-btn" type="submit">创建账号</button>
    </form>
  </section>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'

const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ display_name: '', username: '', role: 'student', password: '', student_number: '' })

async function handleLogin() {
  try {
    app.setStatus('登录中...')
    await auth.login(loginForm.username, loginForm.password)
    app.route = 'overview'
    app.messageEventCursor = 0
    app.editingManagedUserId = null
    app.setStatus('')
    await app.loadClasses()
    router.push({ name: 'overview' })
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function handleRegister() {
  try {
    app.setStatus('创建中...')
    await auth.register({ ...regForm })
    app.route = 'overview'
    app.messageEventCursor = 0
    app.editingManagedUserId = null
    app.setStatus('')
    await app.loadClasses()
    router.push({ name: 'overview' })
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}
</script>
