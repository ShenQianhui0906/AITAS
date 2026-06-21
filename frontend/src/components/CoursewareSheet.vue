<template>
  <SheetPanel
    :eyebrow="editing ? '编辑课件' : '上传课件'"
    :title="editing ? editing.title : '新增课件'"
    :description="editing ? '更新当前课件的标题、课程名称与简介。' : '上传新课件后，班级学生可立即查看。'"
    :wide="true"
    @close="$emit('close')"
  >
    <form class="form-grid" @submit.prevent="onSubmit">
      <div class="field">
        <label for="cw-title">课件标题</label>
        <input id="cw-title" v-model="form.title" required />
      </div>
      <div class="field" :class="{ 'split-field': !editing }">
        <div class="field">
          <label for="cw-course-name">课程名称</label>
          <input id="cw-course-name" v-model="form.course_name" required />
        </div>
        <div v-if="!editing" class="field">
          <label for="cw-file">课件文件</label>
          <input id="cw-file" ref="fileInput" type="file" required />
        </div>
      </div>
      <div class="field">
        <label for="cw-description">课件简介</label>
        <textarea id="cw-description" v-model="form.description" placeholder="输入课件简介"></textarea>
      </div>
      <div v-if="editing" class="inline-hint">当前编辑会更新标题、课程名称与简介，文件本体保持不变。</div>
      <div class="button-row sheet-actions">
        <button class="primary-btn" type="submit">{{ editing ? '保存修改' : '上传课件' }}</button>
        <button class="ghost-btn" type="button" @click="$emit('close')">取消</button>
      </div>
    </form>
  </SheetPanel>
</template>

<script setup>
import { reactive, ref } from 'vue'
import SheetPanel from './SheetPanel.vue'

const props = defineProps({
  editing: { type: Object, default: null },
})
const emit = defineEmits(['close', 'submit'])

const fileInput = ref(null)
const form = reactive({
  title: props.editing?.title || '',
  course_name: props.editing?.course_name || '',
  description: props.editing?.description || '',
})

function onSubmit() {
  if (props.editing) {
    emit('submit', { title: form.title, course_name: form.course_name, description: form.description })
  } else {
    const fd = new FormData()
    fd.set('title', form.title)
    fd.set('course_name', form.course_name)
    fd.set('description', form.description)
    if (fileInput.value?.files?.[0]) {
      fd.set('file', fileInput.value.files[0])
    }
    emit('submit', fd)
  }
}
</script>
