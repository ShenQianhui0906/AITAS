<template>
  <div class="quiz-page page-root">
    <!-- 教师：测验列表 + 发布/AI生成 -->
    <template v-if="auth.role === 'teacher'">
      <SectionTitle title="智能测验" :subtitle="'班级测验管理 · AI 自动生成'">
        <template #actions>
          <button class="primary-btn" @click="openCreatePanel">+ 新建测验</button>
        </template>
      </SectionTitle>

      <div v-if="!quizzes.length && !loading" class="empty-wrap">
        <EmptyState icon="quiz" message="暂无测验，点击「新建测验」开始" />
      </div>

      <div v-for="q in quizzes" :key="q.id" class="quiz-card card-panel">
        <div class="quiz-card-header">
          <h3>{{ q.title }}</h3>
          <span class="badge">{{ q.question_count || (q.questions && q.questions.length) || 0 }} 题</span>
        </div>
        <div class="quiz-card-body">
          <div class="quiz-card-class" v-if="q.class_name">{{ q.class_name }}</div>
          <div class="quiz-card-meta">
            <span>创建于 {{ fmtDate(q.created_at) }}</span>
            <span>{{ getSubmissionCount(q) }} 份提交</span>
          </div>
        </div>
        <div class="quiz-card-actions">
          <button class="ghost-btn slim-btn" @click="viewQuizDetail(q)">查看详情</button>
          <button class="ghost-btn slim-btn" @click="viewSubmissions(q)">查看提交</button>
          <button class="danger-btn slim-btn" @click="handleDelete(q.id)">删除</button>
        </div>
      </div>

      <!-- 教师创建/预览面板 -->
      <SheetPanel
        v-if="showCreatePanel"
        wide
        :eyebrow="isViewing ? '教师端 · 测验详情' : '教师端 · 智能测验'"
        :title="isViewing ? form.title : (editingQuizId ? '编辑测验' : '新建测验')"
        :description="isViewing ? '' : 'AI 自动生成题目，教师审核后发布到班级。'"
        @close="closeCreatePanel"
      >
        <div class="quiz-panel-form form-grid">
          <div v-if="!isViewing" class="field">
            <label for="quiz-title">测验标题</label>
            <input id="quiz-title" v-model="form.title" type="text" placeholder="输入测验标题" class="narrow-input" />
          </div>
          <div v-if="!isViewing" class="field">
            <label for="quiz-class">所属班级</label>
            <select id="quiz-class" v-model="form.class_id" class="narrow-input">
              <option :value="null" disabled>选择班级</option>
              <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div v-if="!isViewing" class="field">
            <label>手动创建题目</label>
            <button v-if="!showManualEditor" class="ghost-btn slim-btn" @click="showManualEditor = true">+ 手动添加题目</button>
            <div v-else class="manual-question-editor">
              <div class="mq-row">
                <label class="mq-sub-label">题目类型</label>
                <select v-model="manualQ.type" class="narrow-input">
                  <option value="choice">单选题</option>
                  <option value="multi_choice">多选题</option>
                  <option value="short">简答题</option>
                </select>
              </div>
              <div class="mq-row">
                <label class="mq-sub-label">题目内容</label>
                <textarea v-model="manualQ.question" class="input" rows="2" placeholder="输入题目内容"></textarea>
              </div>
              <template v-if="manualQ.type === 'choice' || manualQ.type === 'multi_choice'">
                <div class="mq-row">
                  <label class="mq-sub-label">选项列表</label>
                  <div class="mq-options-list">
                    <div v-for="(opt, oi) in manualQ.options" :key="oi" class="mq-option-item">
                      <span class="mq-opt-key">{{ optLetter(oi) }}</span>
                      <input v-model="manualQ.options[oi]" type="text" class="input" :placeholder="'选项 ' + optLetter(oi)" />
                      <button class="ghost-btn slim-btn" @click="manualQ.options.splice(oi, 1)" :disabled="manualQ.options.length <= 2">×</button>
                    </div>
                  </div>
                  <button class="ghost-btn slim-btn" @click="manualQ.options.push('')">+ 添加选项</button>
                </div>
                <div class="mq-row">
                  <label class="mq-sub-label">正确答案</label>
                  <div v-if="manualQ.type === 'choice'" class="mq-answer-opts">
                    <label v-for="(opt, oi) in manualQ.options" :key="oi" class="mq-answer-opt" :class="{ active: manualQ.answer === optLetter(oi) }">
                      <input type="radio" :value="optLetter(oi)" v-model="manualQ.answer" />
                      {{ optLetter(oi) }}. {{ opt || '(空选项)' }}
                    </label>
                  </div>
                  <div v-else class="mq-answer-opts">
                    <label v-for="(opt, oi) in manualQ.options" :key="oi" class="mq-answer-opt" :class="{ active: manualQ.answer.includes(optLetter(oi)) }">
                      <input type="checkbox" :value="optLetter(oi)" v-model="manualQ.answer" />
                      {{ optLetter(oi) }}. {{ opt || '(空选项)' }}
                    </label>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="mq-row">
                  <label class="mq-sub-label">参考答案</label>
                  <textarea v-model="manualQ.answer" class="input" rows="2" placeholder="输入参考答案"></textarea>
                </div>
              </template>
              <div class="mq-row">
                <label class="mq-sub-label">答案解析（可选）</label>
                <textarea v-model="manualQ.explanation" class="input" rows="2" placeholder="输入答案解析，帮助学生理解"></textarea>
              </div>
              <div class="mq-actions">
                <button class="primary-btn slim-btn" @click="commitManualQ">添加题目</button>
                <button class="ghost-btn slim-btn" @click="cancelManualQ">取消</button>
              </div>
            </div>
          </div>

          <div v-if="!isViewing" class="field">
            <label>AI 生成设置</label>
            <textarea v-model="genDescription" class="input" rows="2" placeholder="输入测验知识范围描述（如：第三章微积分基础），留空则使用测验标题检索知识库" style="max-width: 100%; margin-bottom: 8px;"></textarea>
            <div class="form-inline">
              <select v-model="genCount" class="input-sm">
                <option v-for="n in [3,5,8,10]" :key="n" :value="n">{{ n }} 题</option>
              </select>
              <select v-model="genDifficulty" class="input-sm">
                <option value="easy">简单</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>
              <button class="ghost-btn slim-btn" @click="aiGenerate">🤖 AI 生成题目</button>
            </div>
          </div>
        </div>
        <div v-if="form.questions.length" class="quiz-panel-questions">
          <h4>题目列表 ({{ form.questions.length }} 题)</h4>
          <div v-for="(q, i) in form.questions" :key="i" class="quiz-question-card">
            <div class="qq-header">
              <span class="qq-index">#{{ i + 1 }}</span>
              <span class="qq-type">{{ typeLabel(q.type) }}</span>
              <button v-if="!isViewing" class="ghost-btn slim-btn" @click="removeQuestion(i)">删除</button>
            </div>
            <div class="qq-body">
              <p class="qq-question">{{ q.question }}</p>
              <ul v-if="q.options" class="qq-options">
                <li v-for="opt in q.options" :key="opt"
                    :class="{ correct: Array.isArray(q.answer) ? q.answer.includes(getOptKey(opt)) : getOptKey(opt) === q.answer }">
                  {{ opt }}
                </li>
              </ul>
              <p v-else class="qq-answer"><strong>答案：</strong>{{ Array.isArray(q.answer) ? q.answer.join(', ') : q.answer }}</p>
              <p v-if="q.explanation" class="qq-explain">{{ q.explanation }}</p>
            </div>
          </div>
          <div class="button-row sheet-actions">
            <button v-if="!isViewing" class="primary-btn" @click="publishQuiz">发布测验</button>
            <button class="ghost-btn" @click="closeCreatePanel">{{ isViewing ? '关闭' : '取消' }}</button>
          </div>
        </div>
      </SheetPanel>

      <!-- 教师查看提交详情与简答题复核 -->
      <div v-if="showSubmissions" class="quiz-panel quiz-panel--submissions">
        <div class="quiz-panel-header">
          <div>
            <button v-if="activeSubmission" class="submission-back" @click="activeSubmission = null">← 返回提交列表</button>
            <h3>{{ viewingQuiz?.title }} · {{ activeSubmission ? '答卷明细' : '提交列表' }}</h3>
            <p v-if="activeSubmission" class="submission-panel-subtitle">
              {{ activeSubmission.student_name || activeSubmission.student_code }} ·
              {{ fmtDateTime(activeSubmission.submitted_at) }}
            </p>
          </div>
          <button class="ghost-btn" @click="closeSubmissions">×</button>
        </div>

        <template v-if="!activeSubmission">
          <div v-if="submissions.length" class="submission-summary-grid">
            <div><strong>{{ submissionSummary.submission_count || 0 }}</strong><span>已提交</span></div>
            <div><strong>{{ submissionSummary.pending_review_count || 0 }}</strong><span>待复核答卷</span></div>
            <div><strong>{{ submissionSummary.average_percentage || 0 }}%</strong><span>平均得分率</span></div>
          </div>

          <div v-if="submissionsLoading" class="submission-loading">正在加载提交明细…</div>
          <div v-else-if="!submissions.length" class="empty-wrap">
            <EmptyState icon="quiz" message="暂无学生提交，发布测验后学生即可作答" />
          </div>
          <div v-else class="submission-list">
            <button
              v-for="sub in submissions"
              :key="sub.id"
              type="button"
              class="submission-card"
              @click="openSubmission(sub)"
            >
              <div class="sub-header">
                <div class="submission-student">
                  <strong>{{ sub.student_name || sub.student_code || '学生' }}</strong>
                  <span v-if="sub.student_code">{{ sub.student_code }}</span>
                </div>
                <span class="badge" :class="sub.pending_short_count ? 'badge-pending' : 'badge-ok'">
                  {{ sub.score }}/{{ sub.total }}
                </span>
              </div>
              <div class="sub-meta">
                <span>{{ fmtDateTime(sub.submitted_at) }}</span>
                <span v-if="sub.pending_short_count" class="review-pending-text">
                  {{ sub.pending_short_count }} 道简答题待复核
                </span>
                <span v-else>批改已完成</span>
              </div>
            </button>
          </div>
        </template>

        <template v-else>
          <div class="submission-review-score">
            <div><strong>{{ activeSubmission.score }}/{{ activeSubmission.total }}</strong><span>当前成绩</span></div>
            <div><strong>{{ activeSubmission.percentage }}%</strong><span>得分率</span></div>
            <div>
              <strong>{{ activeSubmission.pending_short_count }}</strong>
              <span>简答题待复核</span>
            </div>
          </div>
          <div class="quiz-panel-scroll submission-review-list">
            <article
              v-for="detail in activeSubmission.details"
              :key="detail.question_index"
              class="submission-question-detail"
              :class="{ 'needs-review': detail.question_type === 'short' && detail.review_status !== 'reviewed' }"
            >
              <div class="submission-question-heading">
                <div class="qq-header">
                  <span class="qq-index">#{{ detail.question_index + 1 }}</span>
                  <span class="qq-type">{{ typeLabel(detail.question_type) }}</span>
                </div>
                <span v-if="detail.question_type !== 'short'" class="result-status" :class="detail.correct ? 'is-correct' : 'is-wrong'">
                  {{ detail.correct ? '正确' : '错误' }}
                </span>
                <span v-else class="result-status" :class="detail.review_status === 'reviewed' ? 'is-correct' : 'is-pending'">
                  {{ detail.review_status === 'reviewed' ? '已人工复核' : '待人工复核' }}
                </span>
              </div>
              <p class="qq-question">{{ questionAt(detail.question_index)?.question || '题目内容不可用' }}</p>
              <div class="answer-compare-grid">
                <div><span>学生答案</span><p>{{ formatAnswer(detail.given) || '未作答' }}</p></div>
                <div><span>参考答案</span><p>{{ formatAnswer(detail.expected) || '未设置' }}</p></div>
              </div>
              <p v-if="detail.explanation" class="qq-explain">解析：{{ detail.explanation }}</p>

              <div v-if="detail.question_type === 'short'" class="short-review-editor">
                <div class="review-choice-row">
                  <span>人工判定</span>
                  <button
                    type="button"
                    class="review-choice correct-choice"
                    :class="{ active: reviewDraft[detail.question_index]?.correct === true }"
                    @click="setReviewDecision(detail.question_index, true)"
                  >判为正确</button>
                  <button
                    type="button"
                    class="review-choice wrong-choice"
                    :class="{ active: reviewDraft[detail.question_index]?.correct === false }"
                    @click="setReviewDecision(detail.question_index, false)"
                  >判为错误</button>
                </div>
                <textarea
                  v-model="reviewDraft[detail.question_index].comment"
                  class="input review-comment"
                  rows="2"
                  maxlength="500"
                  placeholder="复核备注（可选，将随复核结果保存）"
                  @input="markReviewDirty(detail.question_index)"
                ></textarea>
                <p v-if="detail.manual_review" class="manual-review-meta">
                  上次由 {{ detail.manual_review.reviewer_name }} 于
                  {{ fmtDateTime(detail.manual_review.reviewed_at) }} 复核
                </p>
              </div>
            </article>
          </div>
          <div class="quiz-submit-row submission-review-actions">
            <span>已选择 {{ selectedReviewCount }} 道简答题的判定</span>
            <button class="primary-btn" :disabled="reviewSaving || !selectedReviewCount" @click="saveShortReviews">
              {{ reviewSaving ? '保存中…' : '保存复核并重算成绩' }}
            </button>
          </div>
        </template>
      </div>
    </template>

    <!-- 学生：测验列表 + 作答 -->
    <template v-else>
      <SectionTitle title="在线测验" subtitle="完成 AI 生成的智能测验" />
      <div v-if="!app.currentClassId" class="empty-wrap">
        <EmptyState icon="quiz" message="请先在「班级」页面选择当前班级" />
      </div>
      <div v-else-if="!quizzes.length && !loading" class="empty-wrap">
        <EmptyState icon="quiz" message="暂无可用的测验" />
      </div>
      <div v-for="q in quizzes" :key="q.id" class="quiz-card card-panel">
        <div class="quiz-card-header">
          <h3>{{ q.title }}</h3>
          <span class="badge">{{ (q.questions && q.questions.length) || 0 }} 题</span>
        </div>
        <div class="quiz-card-body">
          <div class="quiz-card-meta">
            <span>教师：{{ q.teacher_name || '未知' }}</span>
            <span>发布：{{ fmtDate(q.created_at) }}</span>
          </div>
          <div v-if="q.my_submission" class="quiz-score">
            成绩：{{ q.my_submission.score }}/{{ q.my_submission.total || (q.questions && q.questions.length) || 0 }}
            ({{ q.my_submission.percentage }}%)
          </div>
        </div>
        <div class="quiz-card-actions">
          <button v-if="!q.my_submission" class="primary-btn slim-btn" @click="startQuiz(q)">开始答题</button>
          <button v-else class="ghost-btn slim-btn" @click="reviewQuiz(q)">查看结果</button>
        </div>
      </div>

      <!-- 学生答题面板 -->
      <div v-if="activeQuiz" class="quiz-panel quiz-panel--student quiz-taking">
        <div class="quiz-panel-header">
          <h3>{{ activeQuiz.title }}</h3>
          <div class="quiz-timer">共 {{ activeQuiz.questions.length }} 题</div>
        </div>
        <div class="quiz-panel-scroll">
          <div v-for="(q, i) in activeQuiz.questions" :key="i" class="quiz-question-card qq-taking">
            <div class="qq-header">
              <span class="qq-index">#{{ i + 1 }}</span>
              <span class="qq-type">{{ typeLabel(q.type) }}</span>
            </div>
            <p class="qq-question">{{ q.question }}</p>
            <template v-if="q.type === 'choice' && q.options">
              <label v-for="opt in q.options" :key="opt" class="qq-opt-label"
                     :class="{ selected: studentAnswers[i] === getOptKey(opt) }">
                <input type="radio" :value="getOptKey(opt)" v-model="studentAnswers[i]" />
                {{ opt }}
              </label>
            </template>
            <template v-else-if="q.type === 'multi_choice' && q.options">
              <label v-for="opt in q.options" :key="opt" class="qq-opt-label"
                     :class="{ selected: studentAnswers[i] && studentAnswers[i].includes(getOptKey(opt)) }">
                <input type="checkbox" :value="getOptKey(opt)" v-model="studentAnswers[i]" />
                {{ opt }}
              </label>
            </template>
            <template v-else-if="q.type === 'truefalse'">
              <label class="qq-opt-label" :class="{ selected: studentAnswers[i] === 'true' }">
                <input type="radio" value="true" v-model="studentAnswers[i]" /> 正确
              </label>
              <label class="qq-opt-label" :class="{ selected: studentAnswers[i] === 'false' }">
                <input type="radio" value="false" v-model="studentAnswers[i]" /> 错误
              </label>
            </template>
            <template v-else>
              <textarea v-model="studentAnswers[i]" class="input" rows="2" placeholder="输入你的答案"></textarea>
            </template>
          </div>
        </div>
        <div class="quiz-submit-row">
          <button class="primary-btn" :disabled="submitting" @click="submitQuiz">
            {{ submitting ? '提交中…' : '提交答卷' }}
          </button>
          <button class="ghost-btn" @click="activeQuiz = null">取消</button>
        </div>
      </div>

      <!-- 学生查看批改结果 -->
      <div v-if="reviewingQuiz" class="quiz-panel quiz-panel--student">
        <div class="quiz-panel-header">
          <h3>{{ reviewingQuiz.title }} · 答题结果</h3>
          <button class="ghost-btn" @click="reviewingQuiz = null">×</button>
        </div>
        <div class="quiz-score-bar">
          <span class="score-big">{{ reviewingResult.score }}/{{ reviewingResult.total }}</span>
          <span class="score-pct">{{ reviewingResult.percentage }}%</span>
          <span v-if="reviewingResult.pending_short_count" class="score-review-note">
            当前含 {{ reviewingResult.pending_short_count }} 道待教师复核简答题
          </span>
        </div>
        <div class="quiz-panel-scroll">
          <div v-for="(d, i) in reviewingResult.details" :key="i" class="quiz-result-item"
               :class="{
                 correct: d.correct,
                 wrong: !d.correct,
                 'pending-review': d.question_type === 'short' && d.review_status !== 'reviewed'
               }">
            <div class="result-marker">
              {{ d.question_type === 'short' && d.review_status !== 'reviewed' ? '待' : (d.correct ? '✓' : '✗') }}
            </div>
            <div class="result-body">
              <p class="result-question"><strong>#{{ i + 1 }}</strong> {{ reviewingQuiz.questions?.[i]?.question }}</p>
              <p class="result-given"><strong>你的答案：</strong>{{ d.given || '未作答' }}</p>
              <p v-if="!d.correct || d.question_type === 'short'"><strong>参考答案：</strong>{{ formatAnswer(d.expected) }}</p>
              <p v-if="d.explanation" class="result-explain">{{ d.explanation }}</p>
              <p v-if="d.question_type === 'short' && d.review_status !== 'reviewed'" class="result-review-pending">
                当前为自动初判，教师复核后成绩可能更新。
              </p>
              <p v-if="d.manual_review?.comment" class="result-review-comment">
                <strong>教师复核：</strong>{{ d.manual_review.comment }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <LoadingSpinner v-if="loading" />
    <ToastNotification ref="toast" />
    <DialogModal ref="dialog" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAppStore } from '../store/app'
import { useAuthStore } from '../store/auth'
import { quizApi, classesApi } from '../api'
import SectionTitle from '../components/SectionTitle.vue'
import EmptyState from '../components/EmptyState.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import ToastNotification from '../components/ToastNotification.vue'
import DialogModal from '../components/DialogModal.vue'
import SheetPanel from '../components/SheetPanel.vue'

const app = useAppStore()
const auth = useAuthStore()

const quizzes = ref([])
const classes = ref([])
const loading = ref(false)

// 教师面板
const showCreatePanel = ref(false)
const showSubmissions = ref(false)
const editingQuizId = ref(null)
const isViewing = ref(false)
const viewingQuiz = ref(null)
const submissions = ref([])
const submissionSummary = ref({ submission_count: 0, pending_review_count: 0, average_percentage: 0 })
const submissionsLoading = ref(false)
const activeSubmission = ref(null)
const reviewDraft = ref({})
const reviewSaving = ref(false)
const form = ref({ title: '', class_id: null, questions: [], settings: {} })
const genCount = ref(5)
const genDifficulty = ref('medium')
const genDescription = ref('')

// 手动创建题目
const showManualEditor = ref(false)
const manualQ = ref({ type: 'choice', question: '', options: ['', ''], answer: '', explanation: '' })

// 学生面板
const activeQuiz = ref(null)
const reviewingQuiz = ref(null)
const reviewingResult = ref({ score: 0, total: 0, percentage: 0, details: [] })
const studentAnswers = ref([])
const submitting = ref(false)

const toast = ref(null)
const dialog = ref(null)
const selectedReviewCount = computed(() => Object.values(reviewDraft.value).filter(
  item => item?.dirty && typeof item?.correct === 'boolean'
).length)

onMounted(async () => {
  await loadQuizzes()
  if (auth.role === 'teacher') {
    await loadClasses()
  }
})

watch(() => app.currentClassId, () => {
  if (auth.role === 'student') loadQuizzes()
})

async function loadQuizzes() {
  loading.value = true
  try {
    const params = {}
    if (auth.role === 'student' && app.currentClassId) {
      params.class_id = app.currentClassId
    }
    const res = await quizApi.list(params)
    const raw = res.quizzes || []
    // 学生端附上自己的提交状态
    if (auth.role === 'student') {
      for (const q of raw) {
        try {
          const d = await quizApi.detail(q.id)
          q.my_submission = d.submission || null
        } catch { /* ignore */ }
      }
    }
    quizzes.value = raw
  } catch (e) {
    console.error('load quizzes error', e)
  } finally {
    loading.value = false
  }
}

async function loadClasses() {
  try {
    const res = await classesApi.list()
    classes.value = res.classes || []
  } catch { /* ignore */ }
}

function openCreatePanel() {
  editingQuizId.value = null
  isViewing.value = false
  form.value = { title: '', class_id: app.currentClassId, questions: [], settings: {} }
  genDescription.value = ''
  showCreatePanel.value = true
  showSubmissions.value = false
}

function closeCreatePanel() {
  showCreatePanel.value = false
  editingQuizId.value = null
  isViewing.value = false
}

async function aiGenerate() {
  if (!form.value.class_id) {
    toast.value?.show('请先选择班级', 'warn')
    return
  }
  const description = genDescription.value.trim() || form.value.title.trim()
  if (!description) {
    toast.value?.show('请输入知识范围描述或测验标题', 'warn')
    return
  }
  loading.value = true
  try {
    const res = await quizApi.generate({
      description: description,
      class_id: form.value.class_id,
      question_count: genCount.value,
      question_types: ['choice', 'truefalse', 'short'],
      difficulty: genDifficulty.value
    })
    if (res.questions && res.questions.length) {
      form.value.questions = res.questions
      toast.value?.show(`AI 已生成 ${res.questions.length} 道题目`, 'ok')
    } else {
      toast.value?.show('AI 生成失败，请重试', 'error')
    }
  } catch (e) {
    toast.value?.show('AI 生成失败: ' + (e.message || '网络错误'), 'error')
  } finally {
    loading.value = false
  }
}

async function publishQuiz() {
  if (!form.value.title.trim() || !form.value.class_id || !form.value.questions.length) {
    toast.value?.show('请填写完整信息', 'warn')
    return
  }
  loading.value = true
  try {
    await quizApi.publish(form.value)
    toast.value?.show('测验发布成功', 'ok')
    closeCreatePanel()
    await loadQuizzes()
  } catch (e) {
    toast.value?.show('发布失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    loading.value = false
  }
}

function removeQuestion(index) {
  form.value.questions.splice(index, 1)
}

function resetManualQ() {
  manualQ.value = { type: 'choice', question: '', options: ['', ''], answer: '', explanation: '' }
}

function cancelManualQ() {
  showManualEditor.value = false
  resetManualQ()
}

function commitManualQ() {
  if (!manualQ.value.question.trim()) {
    toast.value?.show('请输入题目内容', 'warn')
    return
  }
  if (manualQ.value.type === 'choice' || manualQ.value.type === 'multi_choice') {
    const filled = manualQ.value.options.filter(o => o.trim())
    if (filled.length < 2) {
      toast.value?.show('至少填写 2 个选项', 'warn')
      return
    }
    if (!manualQ.value.answer || (Array.isArray(manualQ.value.answer) && !manualQ.value.answer.length)) {
      toast.value?.show('请选择正确答案', 'warn')
      return
    }
  } else {
    if (!manualQ.value.answer.trim()) {
      toast.value?.show('请填写参考答案', 'warn')
      return
    }
  }
  const q = { ...manualQ.value }
  if (q.type === 'choice' || q.type === 'multi_choice') {
    q.options = q.options.map((opt, i) => optLetter(i) + '. ' + (opt || ''))
  }
  form.value.questions.push(q)
  toast.value?.show('题目已添加', 'ok')
  cancelManualQ()
}

async function viewQuizDetail(q) {
  editingQuizId.value = q.id
  isViewing.value = true
  try {
    const res = await quizApi.detail(q.id)
    form.value = {
      title: res.quiz.title,
      class_id: res.quiz.class_id,
      questions: res.quiz.questions,
      settings: res.quiz.settings || {}
    }
    showCreatePanel.value = true
    showSubmissions.value = false
  } catch (e) {
    toast.value?.show('加载失败', 'error')
  }
}

async function viewSubmissions(q) {
  viewingQuiz.value = q
  showSubmissions.value = true
  showCreatePanel.value = false
  activeSubmission.value = null
  submissions.value = []
  submissionSummary.value = { submission_count: 0, pending_review_count: 0, average_percentage: 0 }
  submissionsLoading.value = true
  try {
    const res = await quizApi.submissions(q.id)
    viewingQuiz.value = res.quiz || q
    submissions.value = res.submissions || []
    submissionSummary.value = res.summary || submissionSummary.value
  } catch (e) {
    toast.value?.show('加载提交明细失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    submissionsLoading.value = false
  }
}

function closeSubmissions() {
  showSubmissions.value = false
  activeSubmission.value = null
  reviewDraft.value = {}
}

function openSubmission(submission) {
  activeSubmission.value = submission
  reviewDraft.value = {}
  for (const detail of submission.details || []) {
    if (detail.question_type !== 'short') continue
    const manualReview = detail.manual_review || null
    reviewDraft.value[detail.question_index] = {
      correct: typeof manualReview?.correct === 'boolean' ? manualReview.correct : null,
      comment: manualReview?.comment || '',
      dirty: false,
    }
  }
}

function setReviewDecision(questionIndex, correct) {
  if (!reviewDraft.value[questionIndex]) {
    reviewDraft.value[questionIndex] = { correct: null, comment: '', dirty: false }
  }
  reviewDraft.value[questionIndex].correct = correct
  reviewDraft.value[questionIndex].dirty = true
}

function markReviewDirty(questionIndex) {
  if (reviewDraft.value[questionIndex]) {
    reviewDraft.value[questionIndex].dirty = true
  }
}

async function saveShortReviews() {
  const reviews = Object.entries(reviewDraft.value)
    .filter(([, value]) => value?.dirty && typeof value?.correct === 'boolean')
    .map(([questionIndex, value]) => ({
      question_index: Number(questionIndex),
      correct: value.correct,
      comment: (value.comment || '').trim(),
    }))
  if (!reviews.length || !activeSubmission.value || !viewingQuiz.value) return

  reviewSaving.value = true
  try {
    const res = await quizApi.reviewSubmission(
      viewingQuiz.value.id,
      activeSubmission.value.id,
      { reviews },
    )
    const updated = res.submission
    const index = submissions.value.findIndex(item => item.id === updated.id)
    if (index >= 0) submissions.value.splice(index, 1, updated)
    activeSubmission.value = updated
    openSubmission(updated)
    submissionSummary.value.pending_review_count = submissions.value.filter(
      item => item.pending_short_count > 0
    ).length
    submissionSummary.value.average_percentage = submissions.value.length
      ? Math.round(
        submissions.value.reduce((sum, item) => sum + Number(item.percentage || 0), 0)
        / submissions.value.length * 10,
      ) / 10
      : 0
    const quiz = quizzes.value.find(item => item.id === viewingQuiz.value.id)
    if (quiz) quiz.submission_count = submissions.value.length
    toast.value?.show('简答题复核已保存，成绩已重新计算', 'ok')
  } catch (e) {
    toast.value?.show('保存复核失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    reviewSaving.value = false
  }
}

async function handleDelete(quizId) {
  const ok = await dialog.value?.confirm('确定删除该测验？所有提交将被清除。')
  if (!ok) return
  try {
    await quizApi.delete(quizId)
    toast.value?.show('已删除', 'ok')
    await loadQuizzes()
  } catch (e) {
    toast.value?.show('删除失败', 'error')
  }
}

function startQuiz(q) {
  activeQuiz.value = q
  reviewingQuiz.value = null
  studentAnswers.value = q.questions.map(qq => qq.type === 'multi_choice' ? [] : '')
}

async function submitQuiz() {
  if (studentAnswers.value.some(a => Array.isArray(a) ? !a.length : !a)) {
    const ok = await dialog.value?.confirm('有题目未作答，确定提交？')
    if (!ok) return
  }
  submitting.value = true
  try {
    const answers = studentAnswers.value.map((ans, i) => ({
      question_index: i,
      answer: Array.isArray(ans) ? ans.join(',') : ans
    }))
    const res = await quizApi.submit(activeQuiz.value.id, { answers })
    reviewingQuiz.value = activeQuiz.value
    reviewingResult.value = res
    activeQuiz.value = null
    toast.value?.show(`得分：${res.score}/${res.total} (${res.percentage}%)`, 'ok')
    await loadQuizzes()
  } catch (e) {
    toast.value?.show('提交失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    submitting.value = false
  }
}

function reviewQuiz(q) {
  if (q.my_submission && q.my_submission.score != null) {
    reviewingQuiz.value = q
    const sub = q.my_submission
    reviewingResult.value = {
      score: sub.score,
      total: sub.total || q.questions.length,
      percentage: sub.percentage || 0,
      details: sub.details || [],
      pending_short_count: sub.pending_short_count || 0,
    }
  }
}

function typeLabel(type) {
  const map = { choice: '单选题', multi_choice: '多选题', truefalse: '判断题', short: '简答题' }
  return map[type] || type
}

function optLetter(index) {
  return String.fromCharCode(65 + index)
}

function getOptKey(opt) {
  if (typeof opt !== 'string') return ''
  const m = opt.match(/^([A-Z])[.\s、]/)
  return m ? m[1].toUpperCase() : opt
}

function questionAt(index) {
  return viewingQuiz.value?.questions?.[index] || null
}

function formatAnswer(answer) {
  if (Array.isArray(answer)) return answer.join('、')
  if (answer === true || answer === 'true') return '正确'
  if (answer === false || answer === 'false') return '错误'
  return answer == null ? '' : String(answer)
}

function fmtDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

function fmtDateTime(d) {
  if (!d) return ''
  return new Date(d.replace?.(' ', 'T') || d).toLocaleString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

function getSubmissionCount(quiz) {
  return Number(quiz?.submission_count || 0)
}
</script>
