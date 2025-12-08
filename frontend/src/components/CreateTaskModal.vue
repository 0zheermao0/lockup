<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>创建任务</h2>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-body">
        <!-- Task Type Selection -->
        <div class="form-group">
          <label>任务类型</label>
          <div class="task-type-selector">
            <button
              type="button"
              @click="form.task_type = 'lock'"
              :class="['task-type-btn', { active: form.task_type === 'lock' }]"
            >
              🔒 带锁任务
              <span class="task-type-desc">自律挑战任务</span>
            </button>
            <button
              type="button"
              @click="form.task_type = 'board'"
              :class="['task-type-btn', { active: form.task_type === 'board' }]"
            >
              📋 任务板
              <span class="task-type-desc">悬赏任务发布</span>
            </button>
          </div>
        </div>

        <div class="form-group">
          <label for="title">任务标题</label>
          <input
            id="title"
            v-model="form.title"
            type="text"
            placeholder="输入任务标题..."
            maxlength="100"
            required
          />
        </div>

        <div class="form-group">
          <label for="description">任务描述</label>
          <textarea
            id="description"
            v-model="form.description"
            :placeholder="form.task_type === 'lock' ? '描述一下你的自律挑战...' : '详细描述任务需求和要求...'"
            rows="3"
            maxlength="500"
            required
          ></textarea>
        </div>

        <!-- Lock Task Fields -->
        <template v-if="form.task_type === 'lock'">
          <div class="form-row">
            <div class="form-group">
              <label for="difficulty">难度等级</label>
              <select id="difficulty" v-model="form.difficulty" required>
                <option value="easy">简单 - 适合初学者</option>
                <option value="normal">普通 - 日常挑战</option>
                <option value="hard">困难 - 需要坚强意志</option>
                <option value="hell">地狱 - 极限挑战</option>
              </select>
            </div>

            <div class="form-group">
              <label for="unlock_type">解锁方式</label>
              <select id="unlock_type" v-model="form.unlock_type" required>
                <option value="time">定时解锁</option>
                <option value="vote">投票解锁</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label for="duration_type">持续时间类型</label>
            <div class="radio-group">
              <label class="radio-option">
                <input
                  type="radio"
                  v-model="form.duration_type"
                  value="fixed"
                />
                <span>固定时间</span>
              </label>
              <label class="radio-option">
                <input
                  type="radio"
                  v-model="form.duration_type"
                  value="random"
                />
                <span>随机时间</span>
              </label>
            </div>
          </div>

          <div class="duration-section">
            <DurationSelector
              v-model="form.duration_value!"
              :label="form.duration_type === 'fixed' ? '持续时间' : '最短时间'"
              :min-minutes="1"
              :max-minutes="10080"
              :required="true"
            />

            <DurationSelector
              v-if="form.duration_type === 'random'"
              v-model="form.duration_max!"
              label="最长时间"
              :min-minutes="form.duration_value || 1"
              :max-minutes="10080"
              :required="true"
            />
          </div>

          <div v-if="form.unlock_type === 'vote'" class="form-group">
            <label for="vote_agreement_ratio">同意比例要求</label>
            <select id="vote_agreement_ratio" v-model="form.vote_agreement_ratio" required>
              <option value="0.5">50% - 简单多数</option>
              <option value="0.6">60% - 普通多数</option>
              <option value="0.7">70% - 绝对多数</option>
              <option value="0.8">80% - 超级多数</option>
              <option value="0.9">90% - 压倒性多数</option>
            </select>
            <small class="help-text">
              只要有人投票且同意比例达到要求即可解锁，无最低投票人数限制
            </small>
          </div>

        </template>

        <!-- Task Board Fields -->
        <template v-if="form.task_type === 'board'">
          <div class="form-row">
            <div class="form-group">
              <label for="reward">奖励金额</label>
              <input
                id="reward"
                v-model.number="form.reward"
                type="number"
                min="1"
                max="10000"
                placeholder="完成任务的奖励"
                required
              />
            </div>
            <div class="form-group">
              <label for="max_duration">最大完成时间 (小时)</label>
              <input
                id="max_duration"
                v-model.number="form.max_duration"
                type="number"
                min="1"
                max="720"
                placeholder="任务最长完成时间"
                required
              />
            </div>
          </div>

        </template>

        <div class="modal-footer">
          <button type="button" @click="closeModal" class="cancel-btn">取消</button>
          <button type="submit" :disabled="submitting" class="submit-btn">
            {{ submitting ? '创建中...' : '创建任务' }}
          </button>
        </div>
      </form>

      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { tasksApi } from '../lib/api-tasks'
import type { TaskCreateRequest } from '../types/index.js'
import DurationSelector from './DurationSelector.vue'

interface Props {
  isVisible: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const submitting = ref(false)
const successMessage = ref('')

const form = reactive<TaskCreateRequest>({
  task_type: 'lock',
  title: '',
  description: '',
  // Lock task fields
  duration_type: 'fixed',
  duration_value: 60, // 默认1小时
  duration_max: undefined,
  difficulty: 'normal',
  unlock_type: 'time',
  // Board task fields
  reward: undefined,
  max_duration: 24 // 默认24小时
})

// Watch for modal visibility changes
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    resetForm()
  }
})

const resetForm = () => {
  form.task_type = 'lock'
  form.title = ''
  form.description = ''
  // Lock task fields
  form.duration_type = 'fixed'
  form.duration_value = 60
  form.difficulty = 'normal'
  form.unlock_type = 'time'
  form.duration_max = 120 // 默认2小时作为随机时间的最大值
  form.vote_agreement_ratio = undefined
  // Board task fields
  form.reward = undefined
  form.max_duration = 24
  successMessage.value = ''
  submitting.value = false
}

const closeModal = () => {
  if (!submitting.value) {
    emit('close')
  }
}

const handleSubmit = async () => {
  if (submitting.value) return

  // 基础验证
  if (!form.title.trim() || !form.description.trim()) {
    alert('请填写完整的任务信息')
    return
  }

  // 带锁任务验证
  if (form.task_type === 'lock') {
    if (form.duration_type === 'random' && (!form.duration_max || !form.duration_value || form.duration_max <= form.duration_value)) {
      alert('最长时间必须大于最短时间')
      return
    }

    if (form.unlock_type === 'vote') {
      if (!form.vote_agreement_ratio) {
        alert('请设置投票同意比例')
        return
      }
    }

  }

  // 任务板验证
  if (form.task_type === 'board') {
    if (!form.reward || form.reward < 1) {
      alert('请设置有效的奖励金额')
      return
    }

    if (!form.max_duration || form.max_duration < 1) {
      alert('请设置最大完成时间')
      return
    }
  }

  submitting.value = true

  try {
    // Clean up form data based on task type
    const cleanedForm = { ...form }

    if (form.task_type === 'lock') {
      // Remove board-specific fields for lock tasks
      delete cleanedForm.reward
      delete cleanedForm.max_duration
    } else if (form.task_type === 'board') {
      // Remove lock-specific fields for board tasks
      delete cleanedForm.duration_type
      delete cleanedForm.duration_value
      delete cleanedForm.duration_max
      delete cleanedForm.difficulty
      delete cleanedForm.unlock_type
      delete cleanedForm.vote_agreement_ratio
    }

    // Create the task through API
    const newTask = await tasksApi.createTask(cleanedForm)
    console.log('Task created successfully:', newTask)

    // 显示成功消息
    successMessage.value = `${form.task_type === 'lock' ? '带锁任务' : '任务板'}创建成功！`
    emit('success')

    // 延迟1.5秒后关闭窗口
    setTimeout(() => {
      if (successMessage.value) {
        closeModal()
      }
    }, 1500)

  } catch (error: any) {
    console.error('Error creating task:', error)
    const errorMessage = error.status === 401
      ? '请先登录'
      : error.data?.error || error.message || '创建失败，请重试'
    alert(errorMessage)
  } finally {
    submitting.value = false
  }
}

// Watch for task type changes to reset form
watch(() => form.task_type, (newValue) => {
  if (newValue === 'lock') {
    // Reset board fields
    form.reward = undefined
    form.max_duration = 24
    // Initialize lock fields
    form.duration_type = 'fixed'
    form.duration_value = 60
    form.duration_max = 120
  } else if (newValue === 'board') {
    // Reset lock fields
    form.duration_type = 'fixed'
    form.duration_value = 60
    form.duration_max = undefined
    form.difficulty = 'normal'
    form.unlock_type = 'time'
    form.vote_agreement_ratio = undefined
  }
})

// Watch for unlock_type changes to reset vote_threshold
watch(() => form.unlock_type, (newValue) => {
  if (newValue !== 'vote') {
    form.vote_agreement_ratio = undefined
  }
})

// Watch for duration_type changes to reset duration_max
watch(() => form.duration_type, (newValue) => {
  if (newValue === 'random') {
    // 如果切换到随机时间，设置默认的最大时间
    const minValue = form.duration_value || 60
    if (!form.duration_max || form.duration_max <= minValue) {
      form.duration_max = Math.max(minValue * 2, 120) // 至少是最短时间的2倍，或2小时
    }
  } else {
    form.duration_max = undefined
  }
})

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 8px 8px 0 #000;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background-color: #f8f9fa;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #007bff;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.radio-group {
  display: flex;
  gap: 1rem;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: normal;
}

.radio-option input[type="radio"] {
  width: auto;
  margin: 0;
}

.task-type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.task-type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
  font-weight: 600;
}

.task-type-btn:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.task-type-btn.active {
  border-color: #007bff;
  background-color: #007bff;
  color: white;
}

.task-type-desc {
  font-size: 0.75rem;
  font-weight: normal;
  margin-top: 0.25rem;
  opacity: 0.8;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.cancel-btn, .submit-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

.cancel-btn {
  background-color: #6c757d;
  color: white;
}

.cancel-btn:hover {
  background-color: #5a6268;
}

.submit-btn {
  background-color: #28a745;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background-color: #218838;
}

.submit-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.success-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: #d4edda;
  color: #155724;
  padding: 1rem 2rem;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  font-weight: 600;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.help-text {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #666;
  font-style: italic;
}

.duration-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0.5rem;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-body {
    padding: 1rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .radio-group {
    flex-direction: column;
    gap: 0.5rem;
  }

  .modal-footer {
    flex-direction: column;
  }
}
</style>