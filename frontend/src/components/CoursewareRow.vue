<template>
  <article class="list-row resource-row" :class="{ active }">
    <div class="row-main">
      <div class="resource-head">
        <div>
          <h4>{{ displayTitle }}</h4>
          <span>{{ courseware.course_name }}</span>
        </div>
        <time>{{ courseware.uploaded_at }}</time>
      </div>
      <p>{{ courseware.description || '暂无简介' }}</p>
    </div>
    <div class="row-actions">
      <a class="ghost-btn slim-btn" :href="courseware.viewer_url" target="_blank" rel="noreferrer">查看</a>
      <button class="secondary-btn slim-btn" @click="$emit('edit')">编辑</button>
      <button class="danger-btn slim-btn" @click="$emit('delete')">删除</button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { displayCoursewareTitle } from '../utils/markdown'

const props = defineProps({
  courseware: { type: Object, required: true },
  active: { type: Boolean, default: false },
})
defineEmits(['edit', 'delete'])

const displayTitle = computed(() => displayCoursewareTitle(props.courseware.title))
</script>
