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
    <div v-if="!app.currentClassId" class="surface empty-surface">
      <SectionTitle title="暂无班级" />
      <p class="empty-copy">先创建班级或加入班级后再开始使用系统。</p>
      <div class="button-row">
        <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
      </div>
    </div>

    <section v-else class="overview-shell learning-overview-shell" :class="auth.role === 'teacher' ? 'teacher-overview-shell' : 'student-overview-shell'">
      <!-- ===== TEACHER ===== -->
      <template v-if="auth.role === 'teacher'">
        <article class="surface teacher-dashboard-panel">
          <header class="teacher-dashboard-header">
            <div class="teacher-dashboard-intro">
              <span class="eyebrow">Teaching Desk</span>
              <h3>{{ app.currentClass?.name || '当前班级' }}</h3>
              <p>课件、反馈、讨论和消息</p>
              <div class="button-row">
                <button class="primary-btn" @click="$router.push({ name: 'coursewares' })">管理课件</button>
                <button class="ghost-btn" @click="$router.push({ name: 'messages' })">查看消息</button>
              </div>
            </div>
            <div class="teacher-metric-grid">
              <MetricCard :value="dash?.stats?.coursewares" label="课件总数" tone="blue" icon="coursewares" />
              <MetricCard :value="dash?.stats?.evaluations" label="反馈总数" tone="green" icon="evaluations" />
              <MetricCard :value="dash?.stats?.assignments" label="作业数量" tone="amber" icon="assignments" />
              <MetricCard :value="dash?.stats?.quizzes" label="测验数量" tone="purple" icon="quizzes" />
              <MetricCard :value="dash?.stats?.unread_messages" label="未读消息" tone="red" icon="messages" />
            </div>
          </header>

          <section class="teacher-analytics-section">
            <div class="teacher-analytics-title">
              <div>
                <span class="eyebrow">Class Insights</span>
                <h4>课程与学生数据</h4>
              </div>
              <span>数据随当前班级实时更新</span>
            </div>

            <div class="teacher-analytics-grid">
              <article class="teacher-chart-card assignment-progress-card">
                <div class="teacher-chart-head">
                  <div>
                    <strong>作业完成概览</strong>
                    <span>{{ assignmentProgress.assignment_count }} 项作业 · {{ assignmentProgress.student_count }} 名学生</span>
                  </div>
                  <span class="chart-soft-badge">批改率 {{ assignmentProgress.grading_rate }}%</span>
                </div>
                <div class="assignment-progress-body">
                  <div
                    class="assignment-progress-donut"
                    :style="{ '--assignment-angle': `${assignmentProgress.completion_rate * 3.6}deg` }"
                  >
                    <div>
                      <strong>{{ assignmentProgress.completion_rate }}%</strong>
                      <span>提交率</span>
                    </div>
                  </div>
                  <div class="assignment-progress-legend">
                    <div><i class="submitted"></i><span>已提交</span><strong>{{ assignmentProgress.submitted_count }}</strong></div>
                    <div><i class="graded"></i><span>已批改</span><strong>{{ assignmentProgress.graded_count }}</strong></div>
                    <div><i class="pending"></i><span>待提交</span><strong>{{ assignmentProgress.pending_count }}</strong></div>
                  </div>
                </div>
              </article>

              <article class="teacher-chart-card student-progress-card">
                <div class="teacher-chart-head">
                  <div>
                    <strong>学生作业进度</strong>
                    <span>选择学生查看详细进度</span>
                  </div>
                </div>
                <div v-if="studentProgress.length" class="student-progress-dropdown">
                  <select
                    v-model.number="selectedStudentId"
                    class="student-select"
                  >
                    <option :value="0">-- 默认视图 --</option>
                    <option
                      v-for="student in studentProgress"
                      :key="student.id"
                      :value="student.id"
                    >
                      {{ student.display_name }}（{{ student.student_number }}）
                    </option>
                  </select>
                  <div v-if="selectedStudent" class="student-progress-detail">
                    <div class="student-progress-row">
                      <div class="student-progress-copy">
                        <strong>{{ selectedStudent.display_name }}</strong>
                        <span>
                          {{ selectedStudent.submitted_count }}/{{ selectedStudent.assignment_count }} 已提交
                          <template v-if="selectedStudent.average_score !== null"> · 均分 {{ selectedStudent.average_score }}</template>
                        </span>
                      </div>
                      <div class="teacher-progress-track">
                        <span :style="{ width: `${selectedStudent.completion_rate}%` }"></span>
                      </div>
                      <strong class="student-progress-rate">{{ selectedStudent.completion_rate }}%</strong>
                    </div>
                    <div class="student-progress-extra">
                      <div class="progress-stat">
                        <span>已提交</span>
                        <strong>{{ selectedStudent.submitted_count }}</strong>
                      </div>
                      <div class="progress-stat">
                        <span>已批改</span>
                        <strong>{{ selectedStudent.graded_count }}</strong>
                      </div>
                      <div class="progress-stat">
                        <span>完成率</span>
                        <strong>{{ selectedStudent.completion_rate }}%</strong>
                      </div>
                      <div v-if="selectedStudent.average_score !== null" class="progress-stat">
                        <span>均分</span>
                        <strong>{{ selectedStudent.average_score }}</strong>
                      </div>
                    </div>
                  </div>
                  <div v-else class="student-progress-default-list">
                    <div v-for="student in defaultStudents" :key="student.id" class="student-progress-row">
                      <div class="student-progress-copy">
                        <strong>{{ student.display_name }}</strong>
                        <span>
                          {{ student.submitted_count }}/{{ student.assignment_count }} 已提交
                          <template v-if="student.average_score !== null"> · 均分 {{ student.average_score }}</template>
                        </span>
                      </div>
                      <div class="teacher-progress-track">
                        <span :style="{ width: `${student.completion_rate}%` }"></span>
                      </div>
                      <strong class="student-progress-rate">{{ student.completion_rate }}%</strong>
                    </div>
                  </div>
                </div>
                <p v-else class="teacher-chart-empty">当前班级暂无学生数据</p>
              </article>

              <div v-if="knowledgeGaps.length || quizAvgScore != null || activityTrend.length" class="quiz-activity-row">
                <article v-if="knowledgeGaps.length" class="teacher-chart-card knowledge-gaps-card">
                  <div class="teacher-chart-head">
                    <div>
                      <strong>知识薄弱点</strong>
                      <span>学生高频错误知识点 Top {{ knowledgeGaps.length }}</span>
                    </div>
                  </div>
                  <div class="knowledge-gaps-list">
                    <div v-for="(gap, i) in knowledgeGaps" :key="i" class="gap-row">
                      <span class="gap-index">#{{ i + 1 }}</span>
                      <div class="gap-body">
                        <p class="gap-question">{{ gap.question }}</p>
                        <p class="gap-detail">正确：{{ gap.expected }} | 常见错误：{{ gap.common_mistake }} · {{ gap.frequency }} 次</p>
                      </div>
                    </div>
                  </div>
                </article>
                <article v-if="quizAvgScore != null" class="teacher-chart-card quiz-score-card">
                  <div class="teacher-chart-head">
                    <div>
                      <strong>测验均分</strong>
                      <span>班级所有测验的平均得分</span>
                    </div>
                    <span class="chart-soft-badge">{{ quizAvgScore }} 分</span>
                  </div>
                  <div class="quiz-score-bar-wrap">
                    <div class="quiz-score-fill" :style="{ width: `${Math.min(quizAvgScore * 10, 100)}%` }"></div>
                  </div>
                </article>

                <article v-if="activityTrend.length" class="teacher-chart-card activity-trend-card">
                  <div class="teacher-chart-head">
                    <div>
                      <strong>近期活动趋势</strong>
                      <span>最近 14 天</span>
                    </div>
                  </div>
                  <div class="activity-trend-chart">
                    <div v-for="(day, i) in activityTrend" :key="i" class="trend-bar-col">
                      <div class="trend-stack">
                        <div class="trend-bar trend-assign" :style="{ height: `${day.assignments * 18}px` }" :title="'作业 ' + day.assignments"></div>
                        <div class="trend-bar trend-quiz" :style="{ height: `${day.quizzes * 18}px` }" :title="'测验 ' + day.quizzes"></div>
                        <div class="trend-bar trend-sub" :style="{ height: `${day.submissions * 12}px` }" :title="'提交 ' + day.submissions"></div>
                      </div>
                      <span class="trend-date">{{ day.date.slice(5) }}</span>
                    </div>
                  </div>
                  <div class="trend-legend">
                    <span><i class="trend-assign"></i> 作业</span>
                    <span><i class="trend-quiz"></i> 测验</span>
                    <span><i class="trend-sub"></i> 提交</span>
                  </div>
                </article>
              </div>

              <article class="teacher-chart-card feedback-chart-card">
                <div class="teacher-chart-head">
                  <div>
                    <strong>课件反馈画像</strong>
                    <span>基于 {{ feedbackInsights.response_count }} 条反馈，满分 5 分</span>
                  </div>
                </div>
                <div class="feedback-dimension-grid">
                  <div v-for="dimension in feedbackInsights.dimensions" :key="dimension.key" class="feedback-dimension-item">
                    <div><span>{{ dimension.label }}</span><strong>{{ dimension.value.toFixed(1) }}</strong></div>
                    <div class="teacher-progress-track feedback-track">
                      <span :style="{ width: `${dimension.value * 20}%` }"></span>
                    </div>
                  </div>
                </div>
              </article>
            </div>
          </section>
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
import { computed, ref, onMounted, watch } from 'vue'
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

const assignmentProgress = computed(() => dash.value?.insights?.assignment_progress || {
  assignment_count: 0,
  student_count: 0,
  submitted_count: 0,
  graded_count: 0,
  pending_count: 0,
  completion_rate: 0,
  grading_rate: 0,
})
const studentProgress = computed(() => dash.value?.insights?.student_progress || [])
const selectedStudentId = ref(0)
const selectedStudent = computed(() => {
  if (!selectedStudentId.value) return null
  return studentProgress.value.find(s => s.id === selectedStudentId.value) || null
})
const defaultStudents = computed(() => studentProgress.value.slice(0, 3))
const feedbackInsights = computed(() => dash.value?.insights?.feedback || {
  response_count: 0,
  dimensions: [
    { key: 'helpfulness', label: '内容帮助度', value: 0 },
    { key: 'usability', label: '课件易用性', value: 0 },
    { key: 'suitability', label: '难度适配度', value: 0 },
    { key: 'practicality', label: '实践价值', value: 0 },
  ],
})
const quizAvgScore = computed(() => dash.value?.insights?.quiz_avg_score ?? null)
const knowledgeGaps = computed(() => (dash.value?.insights?.knowledge_gaps || []).slice(0, 3))
const activityTrend = computed(() => dash.value?.insights?.activity_trend || [])

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
