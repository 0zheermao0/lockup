<template>
  <div class="rich-text-container">
    <div class="toolbar">
      <button
        type="button"
        @click="toggleBold"
        :class="['toolbar-btn', { active: isBold }]"
        title="粗体"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        @click="toggleItalic"
        :class="['toolbar-btn', { active: isItalic }]"
        title="斜体"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        @click="insertList"
        class="toolbar-btn"
        title="插入列表"
      >
        📝
      </button>
      <button
        type="button"
        @click="insertHeading"
        class="toolbar-btn"
        title="插入标题"
      >
        H
      </button>
    </div>
    <div
      ref="editorRef"
      class="rich-text-editor"
      contenteditable
      @input="handleContentChange"
      @focus="updateSelection"
      @mouseup="updateSelection"
      @keyup="updateSelection"
      :data-placeholder="isEditorEmpty ? placeholder : ''"
    ></div>
    <div v-if="showCharCount" class="char-count">
      {{ contentLength }} / {{ maxLength }} 字符
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

interface Props {
  modelValue: string
  placeholder?: string
  maxLength?: number
  showCharCount?: boolean
  minHeight?: string
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请输入内容...',
  maxLength: 2000,
  showCharCount: true,
  minHeight: '120px',
  disabled: false
})

const emit = defineEmits<Emits>()

// Rich text editor state
const editorRef = ref<HTMLElement>()
const isBold = ref(false)
const isItalic = ref(false)

// Computed properties
const isEditorEmpty = computed(() => !props.modelValue || props.modelValue.trim() === '')

const contentLength = computed(() => {
  // Strip HTML tags for character count
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = props.modelValue
  return tempDiv.textContent?.length || 0
})

// Watch for external model changes
watch(() => props.modelValue, (newValue) => {
  if (editorRef.value && editorRef.value.innerHTML !== newValue) {
    editorRef.value.innerHTML = newValue
  }
})

// Watch for disabled state
watch(() => props.disabled, (disabled) => {
  if (editorRef.value) {
    editorRef.value.contentEditable = disabled ? 'false' : 'true'
  }
})

// Rich text editor functions
const updateSelection = () => {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  // Check if selection contains bold/italic
  isBold.value = document.queryCommandState('bold')
  isItalic.value = document.queryCommandState('italic')
}

const toggleBold = () => {
  if (props.disabled) return
  document.execCommand('bold', false)
  editorRef.value?.focus()
  updateContentFromEditor()
}

const toggleItalic = () => {
  if (props.disabled) return
  document.execCommand('italic', false)
  editorRef.value?.focus()
  updateContentFromEditor()
}

const insertList = () => {
  if (props.disabled) return
  document.execCommand('insertUnorderedList', false)
  editorRef.value?.focus()
  updateContentFromEditor()
}

const insertHeading = () => {
  if (props.disabled) return
  const selection = window.getSelection()
  if (selection && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0)
    const selectedText = range.toString()

    if (selectedText) {
      const heading = document.createElement('h3')
      heading.textContent = selectedText
      range.deleteContents()
      range.insertNode(heading)
    } else {
      const heading = document.createElement('h3')
      heading.textContent = '标题'
      range.insertNode(heading)
    }

    selection.removeAllRanges()
    editorRef.value?.focus()
    updateContentFromEditor()
  }
}

const handleContentChange = () => {
  updateContentFromEditor()
}

const updateContentFromEditor = () => {
  if (editorRef.value) {
    emit('update:modelValue', editorRef.value.innerHTML)
  }
}

// Focus method for external use
const focus = () => {
  editorRef.value?.focus()
}

// Clear content method for external use
const clear = () => {
  if (editorRef.value) {
    editorRef.value.innerHTML = ''
    emit('update:modelValue', '')
  }
}

// Expose methods
defineExpose({
  focus,
  clear
})

onMounted(() => {
  if (editorRef.value) {
    editorRef.value.innerHTML = props.modelValue
    editorRef.value.contentEditable = props.disabled ? 'false' : 'true'
  }
})
</script>

<style scoped>
/* Rich Text Editor */
.rich-text-container {
  border: 3px solid #000;
  background: white;
  box-shadow: 4px 4px 0 #000;
}

.toolbar {
  background: #f8f9fa;
  border-bottom: 2px solid #000;
  padding: 0.75rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.toolbar-btn {
  background: white;
  border: 2px solid #000;
  padding: 0.5rem;
  cursor: pointer;
  font-weight: 900;
  min-width: 35px;
  min-height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.toolbar-btn.active {
  background: #007bff;
  color: white;
}

.rich-text-editor {
  min-height: v-bind(minHeight);
  padding: 1rem;
  font-size: 1rem;
  line-height: 1.6;
  outline: none;
  font-family: inherit;
}

.rich-text-editor:empty::before {
  content: attr(data-placeholder);
  color: #999;
  font-style: italic;
}

.rich-text-editor[contenteditable="false"] {
  background-color: #f8f9fa;
  opacity: 0.7;
  cursor: not-allowed;
}

.char-count {
  text-align: right;
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.5rem;
  padding: 0 1rem 0.5rem;
  font-family: monospace;
}

/* Rich text editor content styles */
.rich-text-editor h1,
.rich-text-editor h2,
.rich-text-editor h3 {
  margin: 0.5rem 0;
  font-weight: 900;
}

.rich-text-editor ul {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.rich-text-editor li {
  margin: 0.25rem 0;
}

.rich-text-editor strong {
  font-weight: 900;
}

.rich-text-editor em {
  font-style: italic;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .toolbar {
    padding: 0.5rem;
  }

  .toolbar-btn {
    min-width: 30px;
    min-height: 30px;
    font-size: 0.875rem;
  }

  .rich-text-editor {
    min-height: 100px;
    padding: 0.75rem;
  }
}
</style>