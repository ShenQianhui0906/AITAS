<template>
  <template v-if="currentClass">
    <article class="surface section-shell teacher-class-current-panel">
      <div class="teacher-class-current-head">
        <div class="teacher-class-current-copy">
          <span class="eyebrow">当前班级</span>
          <h3>{{ currentClass.name || '尚未选择班级' }}</h3>
          <p>{{ currentClass.description || '暂无班级说明' }}</p>
        </div>
        <div class="teacher-class-meta-strip">
          <article class="teacher-mini-stat">
            <span>班级成员</span>
            <strong>{{ membersData?.members?.length || 0 }}</strong>
          </article>
          <article class="teacher-mini-stat">
            <span>待审核</span>
            <strong>{{ membersData?.pending_requests?.length || 0 }}</strong>
          </article>
          <article class="teacher-mini-stat">
            <span>候选学生</span>
            <strong>{{ membersData?.available_students?.length || 0 }}</strong>
          </article>
        </div>
      </div>
    </article>

    <div class="teacher-class-board admin-class-board">
      <!-- Pending Requests -->
      <article class="surface section-shell teacher-class-panel teacher-request-panel">
        <div class="teacher-panel-heading">
          <div>
            <h4>入班申请</h4>
            <p>审核学生提交的加入申请</p>
          </div>
          <span class="count-badge">{{ membersData?.pending_requests?.length || 0 }}</span>
        </div>
        <div class="list-stack separated-list teacher-scroll-list">
          <EmptyState v-if="!membersData?.pending_requests?.length" class="teacher-compact-empty" message="暂无待审核申请" />
          <article v-for="r in membersData?.pending_requests" :key="r.id" class="list-row entity-row">
            <div class="row-main">
              <strong>{{ r.display_name }}</strong>
              <span>学生 · {{ r.username }}{{ r.student_number ? ` · 学号 ${r.student_number}` : '' }}</span>
              <small>申请时间 {{ r.requested_at }}</small>
            </div>
            <div class="row-actions">
              <button class="secondary-btn slim-btn" @click="$emit('approve', r.id)">通过</button>
              <button class="danger-btn slim-btn" @click="$emit('reject', r.id)">拒绝</button>
            </div>
          </article>
        </div>
      </article>

      <!-- Members -->
      <article class="surface section-shell teacher-class-panel teacher-members-panel">
        <div class="teacher-panel-heading">
          <div>
            <h4>班级成员</h4>
            <p>{{ currentClass.name }}的教师与学生</p>
          </div>
          <span class="count-badge">{{ membersData?.members?.length || 0 }}</span>
        </div>
        <div class="list-stack separated-list teacher-scroll-list">
          <EmptyState v-if="!membersData?.members?.length" class="teacher-compact-empty" message="当前班级还没有成员" />
          <article v-for="m in membersData?.members" :key="m.id" class="list-row entity-row">
            <div class="row-main">
              <strong>{{ m.display_name }}</strong>
              <span>{{ m.role === 'teacher' ? '教师' : '学生' }} · {{ m.username }}{{ m.student_number ? ` · 学号 ${m.student_number}` : '' }}</span>
            </div>
            <div class="row-actions">
              <button v-if="m.role === 'student'" class="danger-btn slim-btn" @click="$emit('remove', m.id)">移除</button>
              <span v-else class="soft-badge">{{ m.id === currentClass?.teacher_id ? '授课教师' : '教师' }}</span>
            </div>
          </article>
        </div>
      </article>

      <!-- Available Students -->
      <article class="surface section-shell teacher-class-panel teacher-candidates-panel">
        <div class="teacher-panel-heading">
          <div>
            <h4>候选学生</h4>
            <p>将未入班学生直接加入当前班级</p>
          </div>
          <span class="count-badge">{{ membersData?.available_students?.length || 0 }}</span>
        </div>
        <div class="list-stack separated-list teacher-scroll-list">
          <EmptyState v-if="!membersData?.available_students?.length" class="teacher-compact-empty" message="没有可加入的学生" />
          <article v-for="s in membersData?.available_students" :key="s.id" class="list-row entity-row">
            <div class="row-main">
              <strong>{{ s.display_name }}</strong>
              <span>{{ s.username }}{{ s.student_number ? ` · 学号 ${s.student_number}` : '' }}</span>
            </div>
            <div class="row-actions">
              <button class="secondary-btn slim-btn" @click="$emit('add', s.id)">直接加入</button>
            </div>
          </article>
        </div>
      </article>
    </div>
  </template>
  <article v-else class="surface section-shell">
    <SectionTitle title="尚未选择班级" />
  </article>
</template>

<script setup>
import SectionTitle from './SectionTitle.vue'
import EmptyState from './EmptyState.vue'

defineProps({
  currentClass: { type: Object, default: null },
  membersData: { type: Object, default: null },
})
defineEmits(['approve', 'reject', 'remove', 'add'])
</script>
