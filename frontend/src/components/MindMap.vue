<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import type { MindMapNode } from '../types'

const props = defineProps<{ root: MindMapNode | null }>()
const svgEl = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null

function toMarkmap(node: MindMapNode): Record<string, unknown> {
  return { content: node.label, children: (node.children || []).map(toMarkmap) }
}

function render() {
  if (!props.root || !svgEl.value) return
  const transformer = new Transformer()
  const data = transformer.transform(toMarkmap(props.root) as never)
  if (!mm) {
    mm = Markmap.create(svgEl.value, {}, data.root)
  } else {
    mm.setData(data.root)
    mm.fit()
  }
}

onMounted(render)
watch(() => props.root, render)
</script>

<template>
  <svg ref="svgEl" class="w-full" style="height: 62vh"></svg>
</template>
