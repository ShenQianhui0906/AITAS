<template>
  <LoadingSpinner v-if="loading" />

  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle title="暂无班级" />
    <p class="empty-copy">先在班级页创建或加入班级，再查看反馈。</p>
    <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
  </div>

  <template v-else>
    <section class="stats-strip">
      <MetricCard :value="evaluations.length" label="反馈总数" tone="blue" />
      <MetricCard :value="avg('difficulty')" label="内容难度" tone="green" />
      <MetricCard :value="avg('readability')" label="可读性" tone="amber" />
      <MetricCard :value="avg('suitability')" label="适用性" tone="blue" />
      <MetricCard :value="avg('practicality')" label="实用性" tone="red" />
    </section>
    <section class="surface">
      <SectionTitle title="反馈记录" />
      <div class="list-stack">
        <EmptyState v-if="!evaluations.length" message="暂无反馈记录" />
        <div v-for="e in evaluations" :key="e.id" class="feedback-card">
          <div class="resource-head">
            <div>
              <h4>{{ displayCoursewareTitle(e.courseware_title) }}</h4>
              <span>{{ e.course_name }} · {{ e.student_name }}</span>
            </div>
            <time>{{ e.created_at }}</time>
          </div>
          <div class="score-row">
            <span>内容难度 {{ e.difficulty }}/5</span>
            <span>可读性 {{ e.readability }}/5</span>
            <span>适用性 {{ e.suitability }}/5</span>
            <span>实用性 {{ e.practicality }}/5</span>
          </div>
          <p>{{ e.suggestion || '未填写改进建议' }}</p>
        </div>
      </div>
    </section>
  </template>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { evaluationsApi, coursewaresApi } from '../api'
import { displayCoursewareTitle } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import MetricCard from '../components/MetricCard.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const evaluations = ref([])

function avg(field) {
  if (!evaluations.value.length) return '-'
  return (evaluations.value.reduce((s, e) => s + e[field], 0) / evaluations.value.length).toFixed(1)
}

async function load() {
  loading.value = true
  try {
    const [cwData, evData] = await Promise.all([
      coursewaresApi.list({ class_id: app.currentClassId }),
      evaluationsApi.list({ class_id: app.currentClassId }),
    ])
    app.coursewares = cwData.coursewares
    evaluations.value = evData.evaluations
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
  loading.value = false
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
