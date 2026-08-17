<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { IPureNode } from 'markmap-common'
import { Markmap } from 'markmap-view'
import type { MindMapNode } from '../types'

const props = defineProps<{ root: MindMapNode | null }>()
const emit = defineEmits<{ (e: 'select', node: { id: number; label: string }): void }>()
const svgEl = ref<SVGSVGElement | null>(null)
let mm: Markmap | null = null

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// markmap 的 Transformer 会重建节点并丢弃自定义 payload 字段，
// 因此把 id 写进 content HTML 的 data-kid 属性，渲染后从 DOM 读取。
function toMarkmap(node: MindMapNode, isRoot = false): IPureNode {
  const content = isRoot
    ? escapeHtml(node.label)
    : `<span data-kid="${node.id}">${escapeHtml(node.label)}</span>`
  return {
    content,
    children: (node.children || []).map((c) => toMarkmap(c)),
  }
}

function render() {
  if (!props.root || !svgEl.value) return
  const data = toMarkmap(props.root, true)
  if (!mm) {
    mm = Markmap.create(svgEl.value, { initialExpandLevel: 2 }, data)
    // mm.svg 是 d3 selection，用 .on 绑定而非原生 addEventListener
    mm.svg.on('click', onSvgClick)
    // 首次布局可能发生在容器尺寸稳定前，延迟校正一次，避免节点跑出视口
    window.setTimeout(() => mm?.fit(), 150)
  } else {
    mm.setData(data)
    window.setTimeout(() => mm?.fit(), 150)
  }
}

function onSvgClick(e: MouseEvent) {
  const g = (e.target as Element).closest?.('g.markmap-node')
  const span = g?.querySelector?.('[data-kid]')
  const kid = span?.getAttribute('data-kid')
  if (kid == null) return
  const label = span?.textContent || ''
  emit('select', { id: Number(kid), label })
}

onMounted(render)
watch(() => props.root, render)
</script>

<template>
  <svg ref="svgEl" class="w-full" style="height: 62vh"></svg>
</template>
