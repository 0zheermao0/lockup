<template>
  <div class="chat-view">
    <div class="chat-container">
      <!-- 左侧会话列表 -->
      <div class="conversations-sidebar" :class="{ 'hidden': currentConversation }">
        <div class="sidebar-header">
          <h2>💬 私信</h2>
          <span v-if="totalUnreadCount > 0" class="unread-badge">
            {{ totalUnreadCount }}
          </span>
        </div>

        <div v-if="isLoading && conversations.length === 0" class="loading-state">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>

        <div v-else-if="conversations.length === 0" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无会话</p>
          <p class="empty-hint">从用户资料页点击"私聊"开始聊天</p>
        </div>

        <div v-else class="conversations-list">
          <div
            v-for="conversation in sortedConversations"
            :key="conversation.id"
            class="conversation-item"
            :class="{
              'active': currentConversation?.id === conversation.id,
              'unread': conversation.unread_count > 0
            }"
            @click="selectConversation(conversation)"
          >
            <div class="conversation-avatar">
              <UserAvatar
                :user="conversation.other_participant"
                size="normal"
                :clickable="false"
              />
            </div>
            <div class="conversation-info">
              <div class="conversation-header">
                <span class="username">{{ conversation.other_participant?.username || '未知用户' }}</span>
                <span v-if="conversation.unread_count > 0" class="unread-count">
                  {{ conversation.unread_count }}
                </span>
              </div>
              <div class="last-message" v-if="conversation.last_message">
                <span class="message-preview">{{ conversation.last_message.content }}</span>
                <span class="message-time">{{ formatTimeAgo(conversation.last_message.created_at) }}</span>
              </div>
              <div class="last-message" v-else>
                <span class="message-preview empty">点击开始聊天</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧消息区域 -->
      <div class="messages-area" :class="{ 'active': currentConversation }">
        <div v-if="!currentConversation" class="no-conversation">
          <div class="no-conversation-content">
            <div class="icon">💬</div>
            <p>选择一个会话开始聊天</p>
            <p class="hint">或从用户资料页点击"私聊"按钮</p>
          </div>
        </div>

        <template v-else>
          <!-- 消息头部 -->
          <div class="messages-header">
            <button class="back-btn" @click="closeConversation">
              ← 返回
            </button>
            <div class="header-user">
              <UserAvatar
                :user="currentConversation.other_participant"
                size="small"
                :clickable="false"
              />
              <span class="username">{{ currentConversation.other_participant?.username }}</span>
            </div>
            <button
              class="view-profile-btn"
              @click="viewUserProfile(currentConversation.other_participant?.id)"
            >
              查看资料
            </button>
          </div>

          <!-- 消息列表 -->
          <div class="messages-list" ref="messagesListRef">
            <div v-if="isLoadingMessages && messages.length === 0" class="loading-messages">
              <div class="spinner"></div>
              <span>加载消息中...</span>
            </div>

            <div v-else-if="messages.length === 0" class="empty-messages">
              <p>还没有消息</p>
              <p class="hint">发送第一条消息开始聊天吧！</p>
            </div>

            <template v-else>
              <div
                v-for="message in sortedMessages"
                :key="message.id"
                class="message-item"
                :class="{ 'own': isOwnMessage(message) }"
              >
                <div class="message-bubble">
                  <div class="message-content">{{ message.content }}</div>
                  <div class="message-meta">
                    <span class="time">{{ formatTimeAgo(message.created_at) }}</span>
                    <span v-if="isOwnMessage(message)" class="read-status">
                      {{ message.is_read ? '已读' : '未读' }}
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="isLoadingMore" class="loading-more">
                <div class="spinner small"></div>
                <span>加载更多...</span>
              </div>
            </template>
          </div>

          <!-- 消息输入 -->
          <div class="message-input-area">
            <div class="input-wrapper">
              <textarea
                v-model="newMessage"
                placeholder="输入消息..."
                rows="1"
                @keydown.enter.prevent="sendMessage"
                @input="autoResize"
                ref="messageInputRef"
              ></textarea>
              <button
                class="send-btn"
                :disabled="!newMessage.trim() || isSending"
                @click="sendMessage"
              >
                <span v-if="isSending">发送中...</span>
                <span v-else>发送</span>
              </button>
            </div>
            <div class="input-hint">按 Enter 发送，Shift + Enter 换行</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessagingStore } from '../stores/messaging'
import { useAuthStore } from '../stores/auth'
import UserAvatar from '../components/UserAvatar.vue'
import type { Conversation, PrivateMessage } from '../types/index'

const route = useRoute()
const router = useRouter()
const messagingStore = useMessagingStore()
const authStore = useAuthStore()

// State
const newMessage = ref('')
const isSending = ref(false)
const messagesListRef = ref<HTMLElement>()
const messageInputRef = ref<HTMLTextAreaElement>()

// Computed
const conversations = computed(() => messagingStore.conversations)
const sortedConversations = computed(() => messagingStore.sortedConversations)
const currentConversation = computed(() => messagingStore.currentConversation)
const messages = computed(() => messagingStore.messages)
const sortedMessages = computed(() => {
  return [...messages.value].sort((a, b) =>
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
})
const isLoading = computed(() => messagingStore.isLoading)
const isLoadingMessages = computed(() => messagingStore.isLoadingMessages)
const isLoadingMore = computed(() => messagingStore.isLoadingMessages)
const totalUnreadCount = computed(() => messagingStore.totalUnreadCount)

// Methods
const selectConversation = (conversation: Conversation) => {
  messagingStore.setCurrentConversation(conversation)
  messagingStore.fetchMessages(conversation.id)

  // Update URL without navigation
  if (!conversation.id.startsWith('temp-')) {
    router.replace({ name: 'chat-conversation', params: { conversationId: conversation.id } })
  }
}

const closeConversation = () => {
  messagingStore.setCurrentConversation(null)
  router.replace({ name: 'chat' })
}

const isOwnMessage = (message: PrivateMessage) => {
  return message.sender.id === authStore.user?.id
}

const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

const sendMessage = async () => {
  const content = newMessage.value.trim()
  if (!content || isSending.value) return

  const recipientId = currentConversation.value?.other_participant?.id
  if (!recipientId) return

  isSending.value = true
  try {
    await messagingStore.sendMessage(recipientId, content)
    newMessage.value = ''

    // Reset textarea height
    if (messageInputRef.value) {
      messageInputRef.value.style.height = 'auto'
    }

    // Scroll to bottom
    await nextTick()
    scrollToBottom()
  } catch (err) {
    console.error('Failed to send message:', err)
    alert('发送失败，请重试')
  } finally {
    isSending.value = false
  }
}

const autoResize = () => {
  const textarea = messageInputRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }
}

const scrollToBottom = () => {
  if (messagesListRef.value) {
    messagesListRef.value.scrollTop = messagesListRef.value.scrollHeight
  }
}

const viewUserProfile = (userId?: number) => {
  if (userId) {
    router.push({ name: 'profile', params: { id: userId.toString() } })
  }
}

// Initialize
onMounted(async () => {
  await messagingStore.fetchConversations()

  // Check for conversationId in route params
  const conversationId = route.params.conversationId as string
  if (conversationId) {
    const conversation = conversations.value.find(c => c.id === conversationId)
    if (conversation) {
      selectConversation(conversation)
    }
  }

  // Check for userId in query params (from profile modal)
  const userId = route.query.userId as string
  const username = route.query.username as string
  if (userId) {
    await messagingStore.startConversation(parseInt(userId), username || '未知用户')
    // Clear query params
    router.replace({ name: 'chat' })
  }
})

// Watch for route changes
watch(() => route.params.conversationId, (newId) => {
  if (newId && typeof newId === 'string') {
    const conversation = conversations.value.find(c => c.id === newId)
    if (conversation) {
      selectConversation(conversation)
    }
  }
})
</script>

<style scoped>
.chat-view {
  min-height: calc(100vh - 64px);
  background: #f5f5f5;
  padding: 1rem;
}

.chat-container {
  max-width: 1200px;
  margin: 0 auto;
  background: white;
  border: 3px solid #000;
  box-shadow: 8px 8px 0 #000;
  display: flex;
  height: calc(100vh - 96px);
  overflow: hidden;
}

/* 左侧会话列表 */
.conversations-sidebar {
  width: 320px;
  border-right: 3px solid #000;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
}

.sidebar-header {
  padding: 1rem;
  background: #007bff;
  color: white;
  border-bottom: 3px solid #000;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.unread-badge {
  background: #dc3545;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  border: 2px solid #000;
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner.small {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-hint {
  color: #6c757d;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-bottom: 2px solid #e9ecef;
  cursor: pointer;
  transition: all 0.2s ease;
}

.conversation-item:hover {
  background: #e7f3ff;
}

.conversation-item.active {
  background: #007bff;
  color: white;
}

.conversation-item.unread {
  border-left: 4px solid #007bff;
}

.conversation-item.active.unread {
  border-left-color: white;
}

.conversation-avatar {
  margin-right: 0.75rem;
  flex-shrink: 0;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.username {
  font-weight: 700;
  font-size: 0.9375rem;
}

.unread-count {
  background: #dc3545;
  color: white;
  padding: 0.125rem 0.375rem;
  border-radius: 10px;
  font-size: 0.6875rem;
  font-weight: 700;
  border: 1px solid #000;
}

.conversation-item.active .unread-count {
  background: white;
  color: #007bff;
}

.last-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8125rem;
}

.message-preview {
  color: #6c757d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  margin-right: 0.5rem;
}

.message-preview.empty {
  font-style: italic;
}

.conversation-item.active .message-preview {
  color: rgba(255, 255, 255, 0.8);
}

.message-time {
  color: #adb5bd;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.conversation-item.active .message-time {
  color: rgba(255, 255, 255, 0.6);
}

/* 右侧消息区域 */
.messages-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
}

.no-conversation {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-conversation-content {
  text-align: center;
  padding: 2rem;
}

.no-conversation-content .icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.no-conversation-content p {
  font-size: 1.125rem;
  color: #333;
  margin: 0;
}

.no-conversation-content .hint {
  font-size: 0.875rem;
  color: #6c757d;
  margin-top: 0.5rem;
}

.messages-header {
  padding: 1rem;
  background: #f8f9fa;
  border-bottom: 3px solid #000;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn {
  background: #6c757d;
  color: white;
  border: 2px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.back-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.view-profile-btn {
  background: #007bff;
  color: white;
  border: 2px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.view-profile-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.loading-messages,
.empty-messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-messages p {
  font-size: 1rem;
  color: #333;
  margin: 0;
}

.empty-messages .hint {
  font-size: 0.875rem;
  color: #6c757d;
  margin-top: 0.5rem;
}

.message-item {
  display: flex;
  max-width: 70%;
}

.message-item.own {
  align-self: flex-end;
}

.message-bubble {
  background: #f1f3f4;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  border: 2px solid #000;
  box-shadow: 3px 3px 0 #000;
}

.message-item.own .message-bubble {
  background: #007bff;
  color: white;
}

.message-content {
  font-size: 0.9375rem;
  line-height: 1.5;
  word-break: break-word;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
  font-size: 0.6875rem;
}

.message-item:not(.own) .message-meta {
  color: #6c757d;
}

.message-item.own .message-meta {
  color: rgba(255, 255, 255, 0.7);
}

.read-status {
  font-weight: 600;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem;
  color: #6c757d;
  font-size: 0.875rem;
}

/* 消息输入区域 */
.message-input-area {
  padding: 1rem;
  background: #f8f9fa;
  border-top: 3px solid #000;
}

.input-wrapper {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}

.input-wrapper textarea {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #000;
  border-radius: 8px;
  font-size: 0.9375rem;
  resize: none;
  min-height: 44px;
  max-height: 120px;
  font-family: inherit;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.input-wrapper textarea:focus {
  outline: none;
  box-shadow: 4px 4px 0 #000;
  transform: translate(-1px, -1px);
}

.send-btn {
  background: #28a745;
  color: white;
  border: 2px solid #000;
  padding: 0.75rem 1.5rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.send-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.send-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.input-hint {
  font-size: 0.75rem;
  color: #6c757d;
  margin-top: 0.5rem;
  text-align: center;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .chat-view {
    padding: 0;
  }

  .chat-container {
    height: calc(100vh - 60px);
    box-shadow: none;
    border: none;
  }

  .conversations-sidebar {
    width: 100%;
    border-right: none;
  }

  .conversations-sidebar.hidden {
    display: none;
  }

  .messages-area {
    display: none;
  }

  .messages-area.active {
    display: flex;
  }

  .message-item {
    max-width: 85%;
  }

  .input-wrapper textarea {
    font-size: 16px; /* Prevent zoom on iOS */
  }
}
</style>
