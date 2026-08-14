<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FilePlus2, Pencil } from 'lucide-vue-next'
import { questionApi, workbookApi } from '../api'
import type { Workbook } from '../types'

const route = useRoute()
const router = useRouter()
const workbooks = ref<Workbook[]>([])
const workbookId = ref<number | null>(null)
const type = ref('fill_blank')
const content = ref('')
const answer = ref('')
const analysis = ref('')
const difficulty = ref(1)
const options = ref<{ option_key: string; content: string }[]>([])
const error = ref('')
const editId = ref<number | null>(null)

const CHOICE_TYPES = ['single_choice', 'multiple_choice', 'true_false']
const TYPE_LABEL: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
}
const isChoice = computed(() => CHOICE_TYPES.includes(type.value))
const isEdit = computed(() => editId.value != null)

onMounted(async () => {
  workbooks.value = await workbookApi.list()
  const fromQuery = route.query.edit
  if (fromQuery != null) {
    await loadQuestion(Number(fromQuery))
  } else if (workbooks.value.length) {
    workbookId.value = workbooks.value[0].id
  }
})

async function loadQuestion(id: number) {
  const q = await questionApi.get(id)
  editId.value = q.id
  workbookId.value = q.workbook_id
  type.value = q.type
  content.value = q.content
  answer.value = q.answer
  analysis.value = q.analysis || ''
  difficulty.value = q.difficulty
  options.value = q.options.map((o) => ({ option_key: o.option_key, content: o.content }))
}

function addOption() {
  options.value.push({ option_key: String.fromCharCode(65 + options.value.length), content: '' })
}

function removeOption(index: number) {
  options.value.splice(index, 1)
}

function changeType() {
  if (isChoice.value && options.value.length === 0) {
    addOption()
    addOption()
  }
}

async function submit() {
  error.value = ''
  if (workbookId.value == null) {
    error.value = '请选择练习册'
    return
  }
  if (!content.value.trim()) {
    error.value = '请填写题目内容'
    return
  }
  if (!answer.value.trim()) {
    error.value = '请填写答案'
    return
  }

  const body: Record<string, unknown> = {
    type: type.value,
    content: content.value,
    answer: answer.value,
    analysis: analysis.value || null,
    difficulty: difficulty.value,
  }
  if (!isEdit.value) {
    body.workbook_id = workbookId.value
  }

  if (isChoice.value) {
    const valid = options.value.filter((o) => o.content.trim())
    if (valid.length < 2) {
      error.value = '选择题至少需要 2 个选项'
      return
    }
    body.options = valid.map((o, i) => ({ option_key: o.option_key, content: o.content, sort_order: i }))
  }

  try {
    if (isEdit.value) {
      await questionApi.update(editId.value!, body)
    } else {
      await questionApi.create(body)
    }
    router.push('/questions')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <h2 class="mb-4 flex items-center gap-2 text-xl font-bold text-slate-800 dark:text-white">
      <Pencil v-if="isEdit" :size="20" class="text-indigo-500" />
      <FilePlus2 v-else :size="20" class="text-indigo-500" />
      {{ isEdit ? '编辑题目' : '添加题目' }}
    </h2>
    <div class="card space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">所属练习册 *</label>
          <select v-model="workbookId" class="input" :disabled="isEdit">
            <option v-for="wb in workbooks" :key="wb.id" :value="wb.id">{{ wb.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">题型 *</label>
          <select v-model="type" class="input" @change="changeType">
            <option v-for="(label, key) in TYPE_LABEL" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
      </div>

      <div>
        <label class="label">题目内容 *（支持 $LaTeX$ 公式）</label>
        <textarea v-model="content" rows="3" class="input" placeholder="题干内容"></textarea>
      </div>

      <div v-if="isChoice">
        <label class="label">选项（至少 2 个）</label>
        <div v-for="(opt, i) in options" :key="i" class="mb-2 flex items-center gap-2">
          <span class="w-7 text-center font-bold text-slate-500 dark:text-slate-400">{{ opt.option_key }}</span>
          <input v-model="opt.content" class="input !mb-0" :placeholder="`选项 ${opt.option_key} 内容`" />
          <button class="btn-ghost !py-1 text-xs" @click="removeOption(i)">删</button>
        </div>
        <button class="btn-ghost !py-1 text-xs" @click="addOption">+ 添加选项</button>
      </div>

      <div>
        <label class="label">答案 *（选择题填字母如 A / ABD，填空/简答填文本）</label>
        <input v-model="answer" class="input" placeholder="正确答案" />
      </div>

      <div>
        <label class="label">解析（可选）</label>
        <textarea v-model="analysis" rows="3" class="input" placeholder="解题步骤 / 解析"></textarea>
      </div>

      <div class="w-32">
        <label class="label">难度（1-5）</label>
        <input v-model.number="difficulty" type="number" min="1" max="5" class="input" />
      </div>

      <p v-if="error" class="text-sm text-rose-500 dark:text-rose-400">{{ error }}</p>

      <div class="flex gap-2">
        <button class="btn-primary" @click="submit">保存</button>
        <button class="btn-ghost" @click="router.push('/questions')">取消</button>
      </div>
    </div>
  </div>
</template>
