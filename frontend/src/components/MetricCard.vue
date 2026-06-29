<template>
  <article class="metric-card" :class="tone">
    <div class="metric-icon" :class="tone" v-html="iconSvg"></div>
    <div class="metric-copy">
      <strong>{{ displayValue }}</strong>
      <span>{{ label }}</span>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { navigationIcon } from '../utils/navigationIcons'

const props = defineProps({
  value: { type: [Number, String], default: null },
  label: { type: String, required: true },
  tone: { type: String, default: 'blue' },
  icon: { type: String, default: '' },
})

const displayValue = computed(() => (props.value == null ? '-' : String(props.value)))

const icons = {
  blue: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19h16"></path><path d="M7 16V9"></path><path d="M12 16V5"></path><path d="M17 16v-4"></path></svg>`,
  green: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16"></path><path d="m13 5 7 7-7 7"></path></svg>`,
  amber: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v18"></path><path d="M5 10h14"></path><path d="M7 21h10"></path></svg>`,
  red: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 6 8 6 8-6"></path><path d="M4 6h16v12H4z"></path></svg>`,
}

const iconSvg = computed(() => (
  props.icon ? navigationIcon(props.icon) : (icons[props.tone] || icons.blue)
))
</script>
