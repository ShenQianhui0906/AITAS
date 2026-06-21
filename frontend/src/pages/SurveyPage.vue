<template>
  <LoadingSpinner v-if="loading" />

  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle title="暂无班级" />
    <p class="empty-copy">先在班级页创建或加入班级，再提交反馈。</p>
    <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
  </div>

  <template v-else>
    <section class="surface section-shell">
      <div class="section-toolbar">
        <SectionTitle title="我的反馈记录" />
        <div class="button-row">
          <button class="primary-btn" :disabled="!app.coursewares.length" @click="showSheet = true">提交反馈</button>
        </div>
      </div>
      <div class="list-stack separated-list">
        <EmptyState v-if="!evaluations.length" message="还没有提交反馈" />
        <article v-for="e in evaluations" :key="e.id" class="feedback-card">
          <div class="resource-head">
            <div>
              <h4>{{ displayCoursewareTitle(e.courseware_title) }}</h4>
              <span>{{ e.course_name }}</span>
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
        </article>
      </div>
    </section>

    <SheetPanel
      v-if="showSheet"
      eyebrow="提交反馈"
      title="围绕课件完成学习评价"
      description="每份课件限提交一次，建议在阅读完成后提交。"
      @close="showSheet = false"
    >
      <form class="form-grid" @submit.prevent="handleSubmit">
        <div class="field">
          <label for="ev-courseware">课件</label>
          <select id="ev-courseware" v-model="form.courseware_id" required>
            <option value="">请选择课件</option>
            <option v-for="c in app.coursewares" :key="c.id" :value="c.id">
              {{ c.course_name }} · {{ displayCoursewareTitle(c.title) }}
            </option>
          </select>
        </div>
        <div v-for="dim in dimensions" :key="dim.key" class="field">
          <label>{{ dim.label }}</label>
          <div class="rating-grid">
            <label v-for="n in 5" :key="n" class="rating-option">
              <input type="radio" :name="dim.key" :value="n" :checked="n === 3" v-model="form[dim.key]" />
              <span class="rating-chip">
                <strong>{{ n }}</strong>
                <small>分</small>
              </span>
            </label>
          </div>
        </div>
        <div class="field">
          <label for="ev-suggestion">改进建议</label>
          <textarea id="ev-suggestion" v-model="form.suggestion" placeholder="输入你的建议"></textarea>
        </div>
        <div class="button-row sheet-actions">
          <button class="primary-btn" type="submit">提交反馈</button>
          <button class="ghost-btn" type="button" @click="showSheet = false">取消</button>
        </div>
      </form>
    </SheetPanel>
  </template>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { evaluationsApi, coursewaresApi } from '../api'
import { displayCoursewareTitle } from '../utils/markdown'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import SheetPanel from '../components/SheetPanel.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const showSheet = ref(false)
const evaluations = ref([])

const dimensions = [
  { key: 'difficulty', label: '内容难度' },
  { key: 'readability', label: '可读性' },
  { key: 'suitability', label: '适用性' },
  { key: 'practicality', label: '实用性' },
]

const form = reactive({
  courseware_id: '',
  difficulty: '3',
  readability: '3',
  suitability: '3',
  practicality: '3',
  suggestion: '',
})

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

async function handleSubmit() {
  try {
    app.setStatus('提交中...')
    await evaluationsApi.create({ ...form })
    showSheet.value = false
    app.setStatus('反馈提交成功。')
    resetForm()
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

function resetForm() {
  Object.assign(form, { courseware_id: '', difficulty: '3', readability: '3', suitability: '3', practicality: '3', suggestion: '' })
}

onMounted(load)
watch(() => app.currentClassId, load)
</script>
