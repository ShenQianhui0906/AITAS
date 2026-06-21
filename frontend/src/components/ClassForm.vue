<template>
  <form class="form-grid" @submit.prevent="$emit('submit', form)">
    <div class="field">
      <label :for="`${mode}-class-name`">班级名称</label>
      <input :id="`${mode}-class-name`" v-model="form.name" placeholder="例如：软件工程 1 班" required />
    </div>
    <div v-if="teacherOptions.length" class="field">
      <label :for="`${mode}-class-teacher`">授课教师</label>
      <select :id="`${mode}-class-teacher`" v-model="form.teacher_id" required>
        <option value="">请选择教师</option>
        <option v-for="t in teacherOptions" :key="t.id" :value="t.id">{{ t.display_name }} · {{ t.username }}</option>
      </select>
    </div>
    <div class="field">
      <label :for="`${mode}-class-desc`">班级说明</label>
      <textarea :id="`${mode}-class-desc`" v-model="form.description" placeholder="输入班级说明"></textarea>
    </div>
    <div class="button-row sheet-actions">
      <button class="primary-btn" type="submit">{{ mode === 'edit' ? '保存班级信息' : '创建班级' }}</button>
      <button class="ghost-btn" type="button" @click="$emit('cancel')">取消</button>
    </div>
  </form>
</template>

<script setup>
import { reactive } from 'vue'

const props = defineProps({
  mode: { type: String, required: true },
  teacherOptions: { type: Array, default: () => [] },
  currentClass: { type: Object, default: null },
})

defineEmits(['submit', 'cancel'])

const form = reactive({
  name: props.currentClass?.name || '',
  description: props.currentClass?.description || '',
  teacher_id: props.currentClass?.teacher_id || '',
})
</script>
