<template>
  <LoadingSpinner v-if="loading" />

  <div v-else-if="!app.currentClassId" class="surface empty-surface">
    <SectionTitle title="暂无班级" />
    <p class="empty-copy">先创建或加入班级，再使用作业模块。</p>
    <button class="primary-btn" @click="$router.push({ name: 'classes' })">进入班级页</button>
  </div>

  <section v-else class="surface section-shell assignments-page">
    <div class="section-toolbar assignment-toolbar">
      <SectionTitle
        title="作业中心"
        :subline="auth.role === 'teacher' ? '发布班级作业并查看、批改学生提交' : '查看作业要求并在线或通过附件提交'"
      />
      <div v-if="auth.role === 'teacher'" class="assignment-mode-tabs">
        <button
          class="assignment-mode-btn"
          :class="{ active: teacherMode === 'publish' }"
          @click="teacherMode = 'publish'"
        >发布作业</button>
        <button
          class="assignment-mode-btn"
          :class="{ active: teacherMode === 'grade' }"
          @click="teacherMode = 'grade'"
        >批改作业</button>
      </div>
    </div>

    <template v-if="auth.role === 'teacher'">
      <div v-if="teacherMode === 'publish'" class="assignment-section-head">
        <div>
          <strong>已发布作业</strong>
          <span>共 {{ assignments.length }} 项</span>
        </div>
        <button class="primary-btn" @click="showPublishSheet = true">发布新作业</button>
      </div>

      <div v-else class="assignment-section-head">
        <div>
          <strong>提交与批改</strong>
          <span>选择作业查看学生提交</span>
        </div>
      </div>

      <div class="assignment-card-grid">
        <EmptyState v-if="!assignments.length" message="当前班级还没有发布作业" />
        <article v-for="assignment in assignments" :key="assignment.id" class="assignment-card">
          <div class="assignment-card-top">
            <span :class="['assignment-status', isPastDue(assignment.due_at) ? 'late' : 'open']">
              {{ isPastDue(assignment.due_at) ? '已截止' : '进行中' }}
            </span>
            <time>截止 {{ formatDate(assignment.due_at) }}</time>
          </div>
          <h4>{{ assignment.title }}</h4>
          <p>{{ assignment.description || '暂无补充说明' }}</p>
          <div class="assignment-progress">
            <span>{{ assignment.submission_count }}/{{ assignment.student_count }} 已提交</span>
            <span>{{ assignment.graded_count }} 已批改</span>
          </div>
          <div class="button-row assignment-card-actions">
            <button
              v-if="teacherMode === 'grade'"
              class="primary-btn slim-btn"
              @click="openGrading(assignment)"
            >查看并批改</button>
            <button
              v-else
              class="secondary-btn slim-btn"
              @click="openGrading(assignment)"
            >查看提交</button>
            <button class="danger-btn slim-btn" @click="confirmDeleteAssignment(assignment)">删除</button>
          </div>
        </article>
      </div>
    </template>

    <template v-else>
      <div class="assignment-section-head">
        <div>
          <strong>班级作业</strong>
          <span>共 {{ assignments.length }} 项</span>
        </div>
      </div>
      <div class="assignment-card-grid student-assignment-grid">
        <EmptyState v-if="!assignments.length" message="教师暂未发布作业" />
        <article v-for="assignment in assignments" :key="assignment.id" class="assignment-card">
          <div class="assignment-card-top">
            <span :class="['assignment-status', studentStatusClass(assignment)]">
              {{ studentStatusText(assignment) }}
            </span>
            <time>截止 {{ formatDate(assignment.due_at) }}</time>
          </div>
          <h4>{{ assignment.title }}</h4>
          <p>{{ assignment.description || '暂无补充说明' }}</p>
          <div v-if="assignment.submission_status === 'graded'" class="assignment-grade-summary">
            <strong>{{ formatScore(assignment.score) }} 分</strong>
            <span>{{ assignment.feedback || '教师未填写评语' }}</span>
          </div>
          <button class="primary-btn block-btn" @click="openStudentSubmission(assignment)">
            {{ assignment.submission_id ? '查看或修改提交' : '提交作业' }}
          </button>
        </article>
      </div>
    </template>
  </section>

  <SheetPanel
    v-if="showPublishSheet"
    eyebrow="教师端 · 发布作业"
    title="发布新的班级作业"
    description="学生将在当前班级的作业模块中看到这项任务。"
    @close="closePublishSheet"
  >
    <form class="form-grid" @submit.prevent="publishAssignment">
      <div class="field">
        <label for="assignment-title">作业标题</label>
        <input id="assignment-title" v-model="publishForm.title" required placeholder="例如：需求分析章节练习" />
      </div>
      <div class="field">
        <label for="assignment-description">作业要求</label>
        <textarea id="assignment-description" v-model="publishForm.description" placeholder="说明任务内容、格式和评分要求"></textarea>
      </div>
      <div class="field">
        <label for="assignment-due">截止时间</label>
        <input id="assignment-due" v-model="publishForm.due_at" type="datetime-local" required />
      </div>
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit" :disabled="submitting">{{ submitting ? '发布中...' : '确认发布' }}</button>
        <button class="ghost-btn" type="button" @click="closePublishSheet">取消</button>
      </div>
    </form>
  </SheetPanel>

  <SheetPanel
    v-if="showGradeSheet && activeAssignment"
    wide
    eyebrow="教师端 · 批改作业"
    :title="activeAssignment.title"
    :description="`截止时间：${formatDate(activeAssignment.due_at)}`"
    @close="closeGradeSheet"
  >
    <section class="assignment-rubric-card">
      <div class="assignment-rubric-head">
        <div>
          <strong>本作业评分标准</strong>
          <span v-if="gradingRubric" class="assignment-rubric-source">
            来源：{{ rubricSourceLabel(gradingRubric.source) }} · {{ gradingRubric.updated_at }}
          </span>
          <span v-else class="subtle-text">首次使用 AI 批改时，将从知识库、历史批改或作业要求中生成。</span>
        </div>
        <button
          class="secondary-btn slim-btn"
          type="button"
          :disabled="rubricBusy === 'regenerate'"
          @click="regenerateRubric"
        >{{ rubricBusy === 'regenerate' ? '生成中...' : '重新生成' }}</button>
      </div>
      <div v-if="gradingRubric && !rubricEditing" class="assignment-rubric-display">
        <RubricBulletList :nodes="rubricDisplayNodes" />
      </div>
      <textarea
        v-else
        v-model="rubricContent"
        class="assignment-rubric-editor"
        placeholder="可手动填写本项作业的评价维度、分值和判定依据"
      ></textarea>
      <div class="button-row">
        <button
          v-if="rubricEditing"
          class="primary-btn slim-btn"
          type="button"
          :disabled="!rubricContent.trim() || rubricBusy === 'save'"
          @click="saveRubric"
        >{{ rubricBusy === 'save' ? '保存中...' : '保存评价标准' }}</button>
        <button
          v-else
          class="secondary-btn slim-btn"
          type="button"
          @click="startRubricEditing"
        >编辑评价标准</button>
        <button
          v-if="rubricEditing && gradingRubric"
          class="ghost-btn slim-btn"
          type="button"
          @click="cancelRubricEditing"
        >取消编辑</button>
      </div>

      <div v-if="rubricCandidate" class="assignment-rubric-candidate">
        <div>
          <strong>新生成的候选标准</strong>
          <span>来源：{{ rubricSourceLabel(rubricCandidate.source) }}</span>
        </div>
        <div class="assignment-rubric-display candidate-display">
          <RubricBulletList :nodes="rubricCandidateNodes" />
        </div>
        <div class="button-row">
          <button
            class="primary-btn slim-btn"
            type="button"
            :disabled="rubricBusy === 'confirm'"
            @click="confirmRubricCandidate"
          >{{ rubricBusy === 'confirm' ? '替换中...' : '确认替换' }}</button>
          <button class="ghost-btn slim-btn" type="button" @click="rubricCandidate = null">取消</button>
        </div>
      </div>
    </section>

    <div class="assignment-submission-list">
      <EmptyState v-if="!sortedSubmissions.length" message="还没有学生提交这项作业" />
      <article
        v-for="submission in sortedSubmissions"
        :key="submission.id"
        class="assignment-submission-card"
      >
        <div class="assignment-submission-head">
          <div>
            <strong>{{ submission.student_name }}</strong>
            <span>{{ submission.student_number || '未填写学号' }}</span>
          </div>
          <div class="assignment-submission-meta">
            <span v-if="submission.is_late" class="assignment-status late">迟交</span>
            <span v-if="submission.status === 'graded'" class="assignment-status graded">已批改</span>
            <time>{{ submission.submitted_at }}</time>
          </div>
        </div>

        <div
          v-if="submission.content_html"
          class="assignment-rich-content"
          v-html="submission.content_html"
        ></div>
        <p v-else class="subtle-text">该学生仅提交了附件。</p>

        <div v-if="attachmentFiles(submission).length" class="assignment-file-list">
          <div
            v-for="file in attachmentFiles(submission)"
            :key="file.id"
            class="assignment-file-item"
          >
            <button
              class="assignment-file-chip"
              type="button"
              title="使用浏览器预览"
              @click="previewFile(file)"
            >📎 {{ file.original_file_name }} · {{ formatFileSize(file.file_size) }}</button>
            <button
              class="assignment-file-download"
              type="button"
              @click="downloadFile(file)"
            >下载</button>
          </div>
        </div>

        <div v-if="submission.ai_draft" class="assignment-ai-draft-note">
          <strong>AI 建议草稿 · 尚未保存为正式成绩</strong>
          <span>生成于 {{ submission.ai_draft.generated_at }}，可以修改后保存或直接丢弃。</span>
        </div>

        <section
          v-if="submission.graded_at && !submission.ai_draft && !gradeEditingState[submission.id]"
          class="assignment-grade-view"
        >
          <div class="assignment-grade-label-row">
            <strong>批改结果</strong>
            <button
              class="secondary-btn slim-btn"
              type="button"
              :disabled="Boolean(aiGradingState[submission.id])"
              @click="runAiGrading(submission)"
            >{{ aiGradingState[submission.id] ? 'AI批改中...' : 'AI批改' }}</button>
          </div>
          <div class="assignment-rubric-display assignment-feedback-display">
            <RubricBulletList :nodes="rubricToBulletNodes(submission.feedback || '教师未填写评语')" />
          </div>
          <div class="assignment-grade-footer">
            <span class="assignment-saved-score">分数：{{ formatScore(submission.score) }}</span>
            <button
              class="secondary-btn slim-btn"
              type="button"
              @click="startGradeEditing(submission)"
            >编辑批改</button>
          </div>
        </section>

        <form v-else class="assignment-grade-form" @submit.prevent="submitGrade(submission)">
          <div class="field assignment-feedback-field">
            <div class="assignment-grade-label-row">
              <label :for="`feedback-${submission.id}`">评语</label>
              <button
                class="secondary-btn slim-btn"
                type="button"
                :disabled="Boolean(aiGradingState[submission.id])"
                @click="runAiGrading(submission)"
              >{{ aiGradingState[submission.id] ? 'AI批改中...' : 'AI批改' }}</button>
            </div>
            <textarea
              :id="`feedback-${submission.id}`"
              v-model="gradeForms[submission.id].feedback"
              placeholder="填写批改意见"
            ></textarea>
          </div>
          <div class="assignment-grade-footer">
            <div class="field assignment-score-field">
              <label :for="`score-${submission.id}`">分数</label>
              <input
                :id="`score-${submission.id}`"
                v-model="gradeForms[submission.id].score"
                type="number"
                min="0"
                max="100"
                step="0.5"
                required
              />
            </div>
            <div class="assignment-grade-actions">
              <button
                v-if="submission.graded_at && !submission.ai_draft"
                class="ghost-btn"
                type="button"
                @click="cancelGradeEditing(submission)"
              >取消编辑</button>
              <button
                v-if="submission.ai_draft"
                class="ghost-btn"
                type="button"
                @click="discardAiDraft(submission)"
              >丢弃AI草稿</button>
              <button class="primary-btn" type="submit">保存批改</button>
            </div>
          </div>
        </form>
      </article>
    </div>
  </SheetPanel>

  <SheetPanel
    v-if="showSubmitSheet && activeAssignment"
    wide
    eyebrow="学生端 · 提交作业"
    :title="activeAssignment.title"
    :description="`截止时间：${formatDate(activeAssignment.due_at)}`"
    @close="closeSubmitSheet"
  >
    <form class="form-grid" @submit.prevent="submitStudentAssignment">
      <div class="assignment-requirement-card">
        <strong>作业要求</strong>
        <p>{{ activeAssignment.description || '教师未填写补充说明。' }}</p>
      </div>

      <div v-if="activeAssignment.my_submission?.graded_at" class="assignment-result-card">
        <strong>批改结果：{{ formatScore(activeAssignment.my_submission.score) }} 分</strong>
        <p>{{ activeAssignment.my_submission.feedback || '教师未填写评语' }}</p>
      </div>

      <template v-if="!activeAssignment.my_submission?.graded_at">
        <div class="field">
          <label>在线编辑内容</label>
          <div class="assignment-editor-toolbar">
            <button class="secondary-btn slim-btn" type="button" @click="imageInput?.click()">插入图片</button>
            <span>可直接输入文字、粘贴图片或插入本地图片</span>
            <input ref="imageInput" class="sr-only" type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple @change="handleImageSelect" />
          </div>
          <div
            ref="editor"
            class="assignment-rich-editor"
            contenteditable="true"
            data-placeholder="在这里输入作业内容……"
            @paste="handleEditorPaste"
          ></div>
        </div>

        <div class="field">
          <label for="assignment-attachments">本地文件</label>
          <input id="assignment-attachments" ref="attachmentInput" type="file" multiple @change="handleAttachmentSelect" />
          <span class="subtle-text">最多上传 10 个文件，单个文件不超过 20MB。再次提交会替换之前的正文和附件。</span>
        </div>

        <div v-if="attachmentFiles(activeAssignment.my_submission || {}).length" class="assignment-existing-files">
          <strong>上次提交的附件</strong>
          <div
            v-for="file in attachmentFiles(activeAssignment.my_submission)"
            :key="file.id"
            class="assignment-file-item"
          >
            <button
              type="button"
              class="assignment-file-chip"
              title="使用浏览器预览"
              @click="previewFile(file)"
            >📎 {{ file.original_file_name }}</button>
            <button
              type="button"
              class="assignment-file-download"
              @click="downloadFile(file)"
            >下载</button>
          </div>
        </div>

        <div class="button-row sheet-actions">
          <button class="primary-btn" type="submit" :disabled="submitting">{{ submitting ? '提交中...' : '提交作业' }}</button>
          <button class="ghost-btn" type="button" @click="closeSubmitSheet">取消</button>
        </div>
      </template>
    </form>
  </SheetPanel>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../store/auth'
import { useAppStore } from '../store/app'
import { assignmentsApi } from '../api'
import EmptyState from '../components/EmptyState.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SectionTitle from '../components/SectionTitle.vue'
import SheetPanel from '../components/SheetPanel.vue'
import RubricBulletList from '../components/RubricBulletList.vue'

const auth = useAuthStore()
const app = useAppStore()
const loading = ref(true)
const submitting = ref(false)
const assignments = ref([])
const teacherMode = ref('publish')
const showPublishSheet = ref(false)
const showGradeSheet = ref(false)
const showSubmitSheet = ref(false)
const activeAssignment = ref(null)
const editor = ref(null)
const imageInput = ref(null)
const attachmentInput = ref(null)
const inlineImages = ref([])
const attachmentUploads = ref([])
const objectUrls = []
const gradeForms = reactive({})
const gradingRubric = ref(null)
const rubricContent = ref('')
const rubricCandidate = ref(null)
const rubricBusy = ref('')
const rubricEditing = ref(false)
const aiGradingState = reactive({})
const gradeEditingState = reactive({})

const publishForm = reactive({ title: '', description: '', due_at: '' })

const sortedSubmissions = computed(() => {
  const submissions = activeAssignment.value?.submissions || []
  return [...submissions].sort((left, right) => {
    const gradeOrder = Number(Boolean(left.graded_at)) - Number(Boolean(right.graded_at))
    if (gradeOrder) return gradeOrder
    return String(right.submitted_at || '').localeCompare(String(left.submitted_at || ''))
  })
})

const rubricDisplayNodes = computed(() => rubricToBulletNodes(gradingRubric.value?.content || ''))
const rubricCandidateNodes = computed(() => rubricToBulletNodes(rubricCandidate.value?.content || ''))

function parseRubricContent(content) {
  let value = String(content || '').trim().replace(/^```(?:json)?\s*|\s*```$/gi, '')
  for (let attempt = 0; attempt < 3 && typeof value === 'string'; attempt += 1) {
    const candidate = value.trim()
    if (!candidate || !['{', '[', '"'].includes(candidate[0])) break
    try {
      value = JSON.parse(candidate)
    } catch {
      break
    }
  }
  return value
}

function rubricChildren(value) {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => {
      if (item && typeof item === 'object') {
        return [{ label: `第 ${index + 1} 项`, children: rubricChildren(item) }]
      }
      return [{ label: String(item), children: [] }]
    })
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).map(([key, child]) => {
      if (child && typeof child === 'object') {
        return { label: key, children: rubricChildren(child) }
      }
      const text = child === null || child === undefined ? '未设置' : String(child)
      return { label: `${key}：${text}`, children: [] }
    })
  }
  return [{ label: String(value), children: [] }]
}

function rubricToBulletNodes(content) {
  const parsed = parseRubricContent(content)
  if (parsed && typeof parsed === 'object') return rubricChildren(parsed)
  const lines = String(parsed || '')
    .split(/\n+|[；;]+/)
    .map(line => line.trim().replace(/^[-*•]\s*/, ''))
    .filter(Boolean)
  return (lines.length ? lines : ['暂无评分标准']).map(label => ({ label, children: [] }))
}

function formatRubricForEditor(content) {
  const parsed = parseRubricContent(content)
  return parsed && typeof parsed === 'object'
    ? JSON.stringify(parsed, null, 2)
    : String(content || '')
}

function formatDate(value) {
  if (!value) return '-'
  const parsed = new Date(value.replace(' ', 'T'))
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString('zh-CN', { hour12: false })
}

function formatScore(value) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toFixed(Number(value) % 1 ? 1 : 0)
}

function formatFileSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function isPastDue(value) {
  return value ? new Date(value.replace(' ', 'T')).getTime() < Date.now() : false
}

function studentStatusClass(assignment) {
  if (assignment.submission_status === 'graded') return 'graded'
  if (assignment.submission_status === 'submitted') return assignment.is_late ? 'late' : 'submitted'
  return isPastDue(assignment.due_at) ? 'late' : 'open'
}

function studentStatusText(assignment) {
  if (assignment.submission_status === 'graded') return '已批改'
  if (assignment.submission_status === 'submitted') return assignment.is_late ? '已迟交' : '已提交'
  return isPastDue(assignment.due_at) ? '已截止 · 未提交' : '待提交'
}

function attachmentFiles(submission) {
  return (submission?.files || []).filter(file => !file.is_inline)
}

function rubricSourceLabel(source) {
  return {
    knowledge_base: '课程知识库',
    history: '历史批改',
    assignment: '当前作业要求',
    teacher: '教师编辑',
  }[source] || '未知来源'
}

async function load() {
  if (!app.currentClassId) {
    assignments.value = []
    loading.value = false
    return
  }
  loading.value = true
  try {
    const data = await assignmentsApi.list({ class_id: app.currentClassId })
    assignments.value = data.assignments || []
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    loading.value = false
  }
}

function closePublishSheet() {
  showPublishSheet.value = false
  Object.assign(publishForm, { title: '', description: '', due_at: '' })
}

async function publishAssignment() {
  submitting.value = true
  try {
    await assignmentsApi.create({ ...publishForm, class_id: app.currentClassId })
    closePublishSheet()
    app.setStatus('作业已发布。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    submitting.value = false
  }
}

async function openGrading(assignment) {
  try {
    const [data, rubricData] = await Promise.all([
      assignmentsApi.detail(assignment.id),
      assignmentsApi.rubric(assignment.id),
    ])
    activeAssignment.value = data.assignment
    gradingRubric.value = rubricData.rubric || null
    rubricContent.value = formatRubricForEditor(gradingRubric.value?.content || '')
    rubricEditing.value = !gradingRubric.value
    rubricCandidate.value = null
    for (const submission of activeAssignment.value.submissions || []) {
      const draft = submission.ai_draft
      gradeForms[submission.id] = {
        score: draft?.score ?? submission.score ?? '',
        feedback: draft?.feedback || submission.feedback || '',
      }
      gradeEditingState[submission.id] = !submission.graded_at || Boolean(draft)
    }
    showGradeSheet.value = true
    await nextTick()
    await hydrateProtectedImages()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

function closeGradeSheet() {
  showGradeSheet.value = false
  activeAssignment.value = null
  gradingRubric.value = null
  rubricContent.value = ''
  rubricCandidate.value = null
  rubricBusy.value = ''
  rubricEditing.value = false
}

function startRubricEditing() {
  rubricContent.value = formatRubricForEditor(gradingRubric.value?.content || '')
  rubricEditing.value = true
}

function cancelRubricEditing() {
  rubricContent.value = formatRubricForEditor(gradingRubric.value?.content || '')
  rubricEditing.value = false
}

async function saveRubric() {
  if (!activeAssignment.value || !rubricContent.value.trim()) return
  rubricBusy.value = 'save'
  try {
    const data = await assignmentsApi.saveRubric(activeAssignment.value.id, {
      content: rubricContent.value.trim(),
    })
    gradingRubric.value = data.rubric
    rubricContent.value = formatRubricForEditor(data.rubric.content)
    rubricEditing.value = false
    app.setStatus('本作业评分标准已保存。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    rubricBusy.value = ''
  }
}

async function regenerateRubric() {
  if (!activeAssignment.value) return
  rubricBusy.value = 'regenerate'
  try {
    const data = await assignmentsApi.regenerateRubric(activeAssignment.value.id)
    rubricCandidate.value = data.candidate
    app.setStatus('已生成候选评价标准，请确认后替换。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    rubricBusy.value = ''
  }
}

async function confirmRubricCandidate() {
  if (!activeAssignment.value || !rubricCandidate.value) return
  rubricBusy.value = 'confirm'
  try {
    const candidate = rubricCandidate.value
    const data = await assignmentsApi.saveRubric(activeAssignment.value.id, {
      content: candidate.content,
      source: candidate.source,
      source_refs: candidate.source_refs || [],
    })
    gradingRubric.value = data.rubric
    rubricContent.value = formatRubricForEditor(data.rubric.content)
    rubricCandidate.value = null
    rubricEditing.value = false
    app.setStatus('新的评价标准已启用。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    rubricBusy.value = ''
  }
}

async function runAiGrading(submission) {
  if (!activeAssignment.value) return
  aiGradingState[submission.id] = true
  try {
    const data = await assignmentsApi.aiGrade(activeAssignment.value.id, submission.id)
    gradeForms[submission.id].score = data.suggestion.score
    gradeForms[submission.id].feedback = data.suggestion.feedback
    submission.ai_draft = data.draft
    gradeEditingState[submission.id] = true
    gradingRubric.value = data.rubric
    rubricContent.value = formatRubricForEditor(data.rubric.content)
    rubricEditing.value = false
    app.setStatus('AI 批改草稿已生成并保存，请确认后保存正式成绩。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    aiGradingState[submission.id] = false
  }
}

async function discardAiDraft(submission) {
  if (!activeAssignment.value) return
  try {
    await assignmentsApi.discardAiGrade(activeAssignment.value.id, submission.id)
    submission.ai_draft = null
    gradeForms[submission.id] = {
      score: submission.score ?? '',
      feedback: submission.feedback || '',
    }
    gradeEditingState[submission.id] = !submission.graded_at
    app.setStatus('AI 批改草稿已丢弃。')
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function submitGrade(submission) {
  const form = gradeForms[submission.id]
  try {
    await assignmentsApi.grade(activeAssignment.value.id, submission.id, form)
    app.setStatus('批改结果已保存。')
    await openGrading(activeAssignment.value)
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

function startGradeEditing(submission) {
  gradeForms[submission.id] = {
    score: submission.score ?? '',
    feedback: submission.feedback || '',
  }
  gradeEditingState[submission.id] = true
}

function cancelGradeEditing(submission) {
  gradeForms[submission.id] = {
    score: submission.score ?? '',
    feedback: submission.feedback || '',
  }
  gradeEditingState[submission.id] = false
}

async function confirmDeleteAssignment(assignment) {
  const confirmed = await new Promise(resolve => {
    app.setDialog({
      eyebrow: '作业管理',
      title: '删除这项作业？',
      description: '删除后所有学生提交、正文图片、附件和批改结果都会一并删除。',
      confirmText: '确认删除',
      confirmClass: 'danger-btn',
    })
    window._aitasSetDialogResolver(resolve)
  })
  if (!confirmed) return
  try {
    await assignmentsApi.delete(assignment.id)
    app.setStatus('作业已删除。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

async function openStudentSubmission(assignment) {
  try {
    const data = await assignmentsApi.detail(assignment.id)
    activeAssignment.value = data.assignment
    inlineImages.value = []
    attachmentUploads.value = []
    showSubmitSheet.value = true
    await nextTick()
    if (attachmentInput.value) attachmentInput.value.value = ''
    if (editor.value) editor.value.innerHTML = activeAssignment.value.my_submission?.content_html || ''
    await hydrateProtectedImages(editor.value)
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

function closeSubmitSheet() {
  showSubmitSheet.value = false
  activeAssignment.value = null
  inlineImages.value = []
  attachmentUploads.value = []
  if (attachmentInput.value) attachmentInput.value.value = ''
}

function insertImageFile(file) {
  if (!file.type.startsWith('image/')) return
  if (file.size > 20 * 1024 * 1024) {
    app.setStatus('单张图片不能超过 20MB。', 'error')
    return
  }
  const index = inlineImages.value.push(file) - 1
  const url = URL.createObjectURL(file)
  objectUrls.push(url)
  const image = document.createElement('img')
  image.src = url
  image.alt = file.name
  image.dataset.inlineIndex = String(index)
  image.className = 'assignment-editor-image'

  const selection = window.getSelection()
  if (selection?.rangeCount && editor.value?.contains(selection.anchorNode)) {
    const range = selection.getRangeAt(0)
    range.deleteContents()
    range.insertNode(image)
    range.setStartAfter(image)
    range.collapse(true)
    selection.removeAllRanges()
    selection.addRange(range)
  } else {
    editor.value?.appendChild(image)
  }
  editor.value?.appendChild(document.createElement('br'))
}

function handleImageSelect(event) {
  for (const file of event.target.files || []) insertImageFile(file)
  event.target.value = ''
}

function handleEditorPaste(event) {
  const images = [...(event.clipboardData?.files || [])].filter(file => file.type.startsWith('image/'))
  if (!images.length) return
  event.preventDefault()
  images.forEach(insertImageFile)
}

function handleAttachmentSelect(event) {
  attachmentUploads.value = [...(event.target.files || [])]
}

function selectedAttachmentFiles() {
  const inputFiles = attachmentInput.value?.files
  return inputFiles?.length ? [...inputFiles] : attachmentUploads.value
}

async function submitStudentAssignment() {
  const clone = editor.value?.cloneNode(true)
  const formData = new FormData()
  if (clone) {
    clone.querySelectorAll('img[data-assignment-file-id]').forEach(image => image.remove())
    const newImages = [...clone.querySelectorAll('img[data-inline-index]')]
    newImages.forEach((image, newIndex) => {
      const oldIndex = Number(image.dataset.inlineIndex)
      image.removeAttribute('src')
      image.dataset.inlineIndex = String(newIndex)
      const file = inlineImages.value[oldIndex]
      if (file) formData.append('inline_images', file)
    })
    formData.set('content_html', clone.innerHTML)
  }
  selectedAttachmentFiles().forEach(file => formData.append('attachments', file))

  submitting.value = true
  try {
    await assignmentsApi.submit(activeAssignment.value.id, formData)
    closeSubmitSheet()
    app.setStatus('作业提交成功。')
    await load()
  } catch (error) {
    app.setStatus(error.message, 'error')
  } finally {
    submitting.value = false
  }
}

async function hydrateProtectedImages(root = document) {
  if (!root) return
  const images = [...root.querySelectorAll('img[data-assignment-file-id]')]
  await Promise.all(images.map(async image => {
    if (image.src?.startsWith('blob:')) return
    try {
      const blob = await assignmentsApi.file(image.dataset.assignmentFileId)
      const url = URL.createObjectURL(blob)
      objectUrls.push(url)
      image.src = url
    } catch { image.alt = '图片加载失败' }
  }))
}

async function previewFile(file) {
  const previewWindow = window.open('about:blank', '_blank')
  if (!previewWindow) {
    app.setStatus('浏览器阻止了预览窗口，请允许本站打开新窗口。', 'error')
    return
  }
  previewWindow.opener = null
  previewWindow.document.title = '正在加载附件预览'
  previewWindow.document.body.textContent = '正在加载附件预览…'
  try {
    const blob = await assignmentsApi.preview(file.id)
    const url = URL.createObjectURL(blob)
    previewWindow.location.replace(url)
    setTimeout(() => URL.revokeObjectURL(url), 5 * 60 * 1000)
  } catch (error) {
    previewWindow.close()
    app.setStatus(error.message, 'error')
  }
}

async function downloadFile(file) {
  try {
    const blob = await assignmentsApi.file(file.id, { download: true })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.original_file_name
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    app.setStatus(error.message, 'error')
  }
}

onMounted(load)
watch(() => app.currentClassId, () => {
  closeGradeSheet()
  closeSubmitSheet()
  load()
})
onBeforeUnmount(() => objectUrls.forEach(url => URL.revokeObjectURL(url)))
</script>
