<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { IPureNode } from 'markmap-common'
import { Markmap } from 'markmap-view'
import type { MindMapNode } from '../types'

const props = defineProps<{ root: MindMapNode | null }>()
const svgEl = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null

function toMarkmap(node: MindMapNode): IPureNode {
  return { content: node.label, children: (node.children || []).map(toMarkmap) }
}

function render() {
  if (!props.root || !svgEl.value) return
  const data = toMarkmap(props.root)
  if (!mm) {
    mm = Markmap.create(svgEl.value, {}, data)
  } else {
    mm.setData(data)
    mm.fit()
  }
}

onMounted(render)
watch(() => props.root, render)
</script>

<template>
  <svg ref="svgEl" class="w-full" style="height: 62vh"></svg>
</template>
