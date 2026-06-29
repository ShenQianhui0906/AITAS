<template>
  <ul class="rubric-bullet-list">
    <li v-for="(node, index) in nodes" :key="`${index}-${node.label}`">
      <span>{{ node.label }}</span>
      <RubricBulletList v-if="node.children?.length" :nodes="node.children" />
    </li>
  </ul>
</template>

<script setup>
defineProps({
  nodes: {
    type: Array,
    default: () => [],
  },
})
</script>
