<template>
  <Teleport to="body">
    <Transition name="chat-modal" @after-leave="$emit('closed')">
      <div v-if="isVisible" class="chat-modal-overlay" @click="handleOverlayClick">
        <div class="chat-modal-container" @click.stop>
          <div class="chat-modal-card">
            <!-- Sidebar: Conversation List -->
            <div class="chat-sidebar" :class="{ 'hidden': selectedConversation }">
              <!-- Sidebar Header -->
              <div class="sidebar-header">
                <h3>💬 私信</h3>
                <button @click="closeModal" class="close-btn" title="关闭">✕</button>
              </div>

              <!-- Search -->
              <div class="sidebar-search">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="搜索会话..."
                  class="search-input"
                />
                <span class="search-icon">🔍</span>
              </div>

              <!-- Conversation List -->
              <div class="conversation-list" ref="conversationListRef">
                <div v-if="messagingStore.isLoading" class="sidebar-loading">
                  <div class="spinner"></div>
                  <span>加载中...</span>
                </div>

                <div v-else-if="filteredConversations.length === 0" class="sidebar-empty">
                  <div class="empty-icon">💬</div>
                  <p>{{ searchQuery ? '未找到匹配的会话' : '还没有会话' }}</p>
                </div>

                <div
                  v-for="conv in filteredConversations"
                  :key="conv.id"
                  class="conversation-item"
                  :class="{ 'active': selectedConversation?.id === conv.id, 'unread': conv.unread_count > 0 }"
                  @click="selectConversation(conv)"
                >
                  <UserAvatar
                    :user="conv.other_participant"
                    size="small"
                    :clickable="false"
                  />
                  <div class="conversation-info">
                    <div class="conversation-name">
                      {{ conv.other_participant?.username || '未知用户' }}
                    </div>
                    <div class="conversation-preview">
                      {{ getLastMessagePreview(conv.last_message) }}
                    </div>
                  </div>
                  <div class="conversation-meta">
                    <span class="conversation-time">{{ formatTime(conv.updated_at) }}</span>
                    <span v-if="conv.unread_count > 0" class="unread-badge">
                      {{ conv.unread_count > 99 ? '99+' : conv.unread_count }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Chat Area -->
            <div class="chat-area" :class="{ 'active': selectedConversation }">
              <!-- Chat Header -->
              <div class="chat-header">
                <button
                  v-if="selectedConversation"
                  @click="backToList"
                  class="back-btn"
                  title="返回列表"
                >
                  ←
                </button>
                <div class="header-user" v-if="selectedConversation">
                  <UserAvatar
                    :user="selectedConversation?.other_participant"
                    size="small"
                    :clickable="false"
                  />
                  <div class="user-info">
                    <span class="username">{{ selectedConversation?.other_participant?.username || '加载中...' }}</span>
                    <span v-if="isOnline" class="online-status">在线</span>
                  </div>
                </div>
                <div v-else class="header-placeholder">
                  <span>选择一个会话开始聊天</span>
                </div>
                <div class="header-actions">
                  <!-- Telegram Chat Button - Show when both users have TG bound and display enabled -->
                  <button
                    v-if="canShowTelegramChat"
                    @click="openTelegramChat"
                    class="action-btn telegram-btn"
                    title="在 Telegram 中聊天"
                  >
                    ✈️
                  </button>
                  <button
                    v-if="selectedConversation?.other_participant?.id"
                    @click="viewProfile"
                    class="action-btn"
                    title="查看资料"
                  >
                    👤
                  </button>
                  <button @click="closeModal" class="close-btn" title="关闭">✕</button>
                </div>
              </div>

              <!-- Messages Area -->
              <div class="chat-messages" ref="messagesContainerRef">
                <div v-if="!selectedConversation" class="empty-chat">
                  <div class="empty-icon">💬</div>
                  <p>从左侧选择一个会话开始聊天</p>
                </div>

                <div v-else-if="messagingStore.isLoadingMessages" class="loading-state">
                  <div class="spinner"></div>
                  <span>加载消息中...</span>
                </div>

                <div v-else-if="messagingStore.error" class="error-state">
                  <div class="error-icon">⚠️</div>
                  <p>{{ messagingStore.error }}</p>
                  <button @click="loadMessages" class="retry-btn">重试</button>
                </div>

                <div v-else-if="messagingStore.messages.length === 0" class="empty-state">
                  <div class="empty-icon">💬</div>
                  <p>还没有消息</p>
                  <span class="empty-hint">发送第一条消息开始聊天吧！</span>
                </div>

                <template v-else>
                  <div
                    v-for="message in sortedMessages"
                    :key="message.id"
                    class="message-item"
                    :class="{ 'own': isOwnMessage(message) }"
                  >
                    <div class="message-bubble">
                      <!-- Text Message -->
                      <div v-if="message.message_type === 'text'" class="message-content">
                        {{ message.content }}
                      </div>

                      <!-- Image Message -->
                      <div v-else-if="message.message_type === 'image'" class="message-image">
                        <img
                          :src="message.file_url"
                          :alt="message.content || '图片'"
                          @click="openImagePreview(message.file_url!)"
                          class="message-image-preview"
                        />
                        <p v-if="message.content" class="image-caption">{{ message.content }}</p>
                      </div>

                      <!-- Voice Message -->
                      <div v-else-if="message.message_type === 'voice'" class="message-voice">
                        <button
                          @click="toggleVoicePlayback(message.id, message.file_url!)"
                          class="voice-play-btn"
                          :class="{ 'playing': currentlyPlayingVoice === message.id }"
                        >
                          {{ currentlyPlayingVoice === message.id ? '⏸️' : '▶️' }}
                        </button>
                        <div class="voice-waveform">
                          <span class="voice-duration">{{ formatDuration(message.file_duration) }}</span>
                          <div class="waveform-bars">
                            <span v-for="i in 10" :key="i" class="wave-bar" :style="{ height: getWaveHeight(i, message.id) + 'px' }"></span>
                          </div>
                        </div>
                      </div>

                      <div class="message-meta">
                        <span class="time">{{ formatTime(message.created_at) }}</span>
                        <span v-if="isOwnMessage(message)" class="read-status">
                          {{ message.is_read ? '已读' : '未读' }}
                        </span>
                      </div>
                    </div>
                  </div>
                </template>
              </div>

              <!-- Input Area -->
              <div v-if="selectedConversation" class="chat-input">
                <!-- Emoji Panel -->
                <div v-if="showEmojiPanel" class="emoji-panel">
                  <div class="emoji-categories">
                    <button
                      v-for="cat in emojiCategories"
                      :key="cat.name"
                      @click="currentEmojiCategory = cat.name"
                      class="emoji-category-btn"
                      :class="{ active: currentEmojiCategory === cat.name }"
                    >
                      {{ cat.icon }}
                    </button>
                  </div>
                  <div class="emoji-list">
                    <button
                      v-for="emoji in currentEmojis"
                      :key="emoji"
                      @click="insertEmoji(emoji)"
                      class="emoji-btn"
                    >
                      {{ emoji }}
                    </button>
                  </div>
                </div>

                <!-- Image Preview -->
                <div v-if="selectedImage" class="image-preview-bar">
                  <img :src="selectedImagePreview" alt="预览" class="preview-thumb" />
                  <span class="preview-text">{{ selectedImage.name }}</span>
                  <button @click="clearImage" class="clear-preview-btn">✕</button>
                </div>

                <!-- Voice Recording -->
                <div v-if="isRecording" class="voice-recording-bar">
                  <span class="recording-indicator">🔴</span>
                  <span class="recording-time">{{ formatRecordingTime(recordingTime) }}</span>
                  <button @click="stopRecording" class="stop-recording-btn">完成</button>
                  <button @click="cancelRecording" class="cancel-recording-btn">取消</button>
                </div>

                <div class="input-wrapper">
                  <!-- Emoji Toggle -->
                  <button
                    @click="toggleEmojiPanel"
                    class="input-action-btn"
                    :class="{ active: showEmojiPanel }"
                    title="表情"
                  >
                    😊
                  </button>

                  <!-- Image Upload -->
                  <button
                    @click="triggerImageUpload"
                    class="input-action-btn"
                    title="图片"
                    :disabled="isRecording"
                  >
                    📷
                  </button>
                  <input
                    ref="imageInputRef"
                    type="file"
                    accept="image/*"
                    @change="handleImageSelect"
                    style="display: none"
                  />

                  <!-- Voice Record -->
                  <button
                    v-if="!isRecording && !selectedImage && !newMessage.trim()"
                    @mousedown="startRecording"
                    @touchstart.prevent="startRecording"
                    class="input-action-btn"
                    title="按住录音"
                  >
                    🎤
                  </button>

                  <!-- Text Input -->
                  <textarea
                    v-if="!isRecording"
                    v-model="newMessage"
                    placeholder="输入消息..."
                    rows="1"
                    @keydown.enter.prevent="handleSend"
                    @input="autoResize"
                    ref="inputRef"
                    :disabled="isSending || !selectedConversation"
                  ></textarea>

                  <!-- Send Button -->
                  <button
                    v-if="!isRecording && (canSend || selectedImage)"
                    @click="handleSend"
                    class="send-btn"
                    :disabled="(!canSend && !selectedImage) || isSending"
                  >
                    <span v-if="isSending">⏳</span>
                    <span v-else>发送</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Image Preview Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="previewImageUrl" class="image-preview-overlay" @click="closeImagePreview">
          <img :src="previewImageUrl" alt="预览" class="image-preview-full" />
          <button class="close-preview-btn" @click.stop="closeImagePreview">✕</button>
        </div>
      </Transition>
    </Teleport>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagingStore } from '../stores/messaging'
import { useAuthStore } from '../stores/auth'
import { messagingApi } from '../lib/api'
import UserAvatar from './UserAvatar.vue'
import type { Conversation, PrivateMessage } from '../types/index'

interface Props {
  isVisible: boolean
}

const props = defineProps<Props>()

interface Emits {
  (e: 'close'): void
  (e: 'closed'): void
}

const emit = defineEmits<Emits>()

const router = useRouter()
const messagingStore = useMessagingStore()
const authStore = useAuthStore()

// State
const selectedConversation = ref<Conversation | null>(null)
const newMessage = ref('')
const isSending = ref(false)
const messagesContainerRef = ref<HTMLElement>()
const inputRef = ref<HTMLTextAreaElement>()
const conversationListRef = ref<HTMLElement>()
const isOnline = ref(false)
const searchQuery = ref('')

// Emoji State
const showEmojiPanel = ref(false)
const currentEmojiCategory = ref('smileys')
const emojiCategories = [
  { name: 'smileys', icon: '😊', emojis: ['😀', '😃', '😄', '😁', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴', '🤢', '🤮', '🤧', '😷', '🤒', '🤕'] },
  { name: 'people', icon: '👋', emojis: ['👋', '🤚', '🖐️', '✋', '🖖', '👌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏', '✍️', '💪', '🦾', '🦿', '🦵', '🦶', '👂', '🦻', '👃', '🧠', '🫀', '🫁', '🦷', '🦴', '👀', '👁️', '👅', '👄', '👶', '🧒', '👦', '👧', '🧑', '👱', '👨', '🧔', '👩', '🧓', '👴', '👵'] },
  { name: 'animals', icon: '🐱', emojis: ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐽', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🐣', '🐥', '🦆', '🦅', '🦉', '🦇', '🐺', '🐗', '🐴', '🦄', '🐝', '🐛', '🦋', '🐌', '🐞', '🐜', '🦟', '🦗', '🕷️', '🕸️', '🦂', '🐢', '🐍', '🦎', '🦖', '🦕', '🐙', '🦑', '🦐', '🦞', '🦀', '🐡', '🐠', '🐟', '🐬', '🐳', '🐋', '🦈', '🐊', '🐅', '🐆', '🦓', '🦍', '🦧', '🐘', '🦛', '🦏', '🐪', '🐫', '🦒', '🦘', '🐃', '🐂', '🐄', '🐎', '🐖', '🐏', '🐑', '🦙', '🐐', '🦌', '🐕', '🐩', '🦮', '🐕‍🦺', '🐈', '🐈‍⬛', '🐓', '🦃', '🦚', '🦜', '🦢', '🦩', '🕊️', '🐇', '🦝', '🦨', '🦡', '🦦', '🦥', '🐁', '🐀', '🐿️', '🦔'] },
  { name: 'food', icon: '🍎', emojis: ['🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🫐', '🍈', '🍒', '🍑', '🍍', '🥝', '🥥', '🥑', '🍆', '🥔', '🥕', '🌽', '🌶️', '🫑', '🥒', '🥬', '🥦', '🧄', '🧅', '🍄', '🥜', '🌰', '🍞', '🥐', '🥖', '🫓', '🥨', '🥯', '🥞', '🧇', '🧀', '🍖', '🍗', '🥩', '🥓', '🍔', '🍟', '🍕', '🌭', '🥪', '🌮', '🌯', '🫔', '🥙', '🧆', '🥚', '🍳', '🥘', '🍲', '🫕', '🥣', '🥗', '🍿', '🧈', '🧂', '🥫', '🍱', '🍘', '🍙', '🍚', '🍛', '🍜', '🍝', '🍠', '🍢', '🍣', '🍤', '🍥', '🥮', '🍡', '🥟', '🥠', '🥡', '🦀', '🦞', '🦐', '🦑', '🦪', '🍦', '🍧', '🍨', '🍩', '🍪', '🎂', '🍰', '🧁', '🥧', '🍫', '🍬', '🍭', '🍮', '🍯'] },
  { name: 'activities', icon: '⚽', emojis: ['⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🎱', '🪀', '🏓', '🏸', '🏒', '🏑', '🥍', '🏏', '🥅', '⛳', '🪁', '🏹', '🎣', '🤿', '🥊', '🥋', '⛸️', '🎿', '🛷', '🥌', '🎯', '🪃', '🪓', '🎱', '🔮', '🪄', '🎮', '🕹️', '🎰', '🎲', '🧩', '🧸', '🪅', '🪆', '♠️', '♥️', '♦️', '♣️', '♟️', '🃏', '🀄', '🎴', '🎭', '🖼️', '🎨', '🧵', '🪡', '🧶', '🪢'] },
  { name: 'objects', icon: '💡', emojis: ['⌚', '⏰', '⏱️', '⏲️', '🕰️', '🕛', '🕧', '🕐', '🕜', '🕑', '🕝', '🕒', '🕞', '🕓', '🕟', '🕔', '🕠', '🕕', '🕡', '🕖', '🕢', '🕗', '🕣', '🕘', '🕤', '🕙', '🕥', '🕚', '🕦', '🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘', '🌙', '🌚', '🌛', '🌜', '🌡️', '☀️', '🌝', '🌞', '🪐', '⭐', '🌟', '🌠', '🌌', '☁️', '⛅', '⛈️', '🌤️', '🌥️', '🌦️', '🌧️', '🌨️', '❄️', '🌬️', '💨', '💧', '💦', '☔', '☂️', '🌊', '🌫️'] },
]

const currentEmojis = computed(() => {
  const category = emojiCategories.find(c => c.name === currentEmojiCategory.value)
  return category?.emojis || []
})

// Image Upload State
const imageInputRef = ref<HTMLInputElement>()
const selectedImage = ref<File | null>(null)
const selectedImagePreview = ref<string>('')

// Voice Recording State
const isRecording = ref(false)
const recordingTime = ref(0)
const recordingInterval = ref<number | null>(null)
const mediaRecorder = ref<MediaRecorder | null>(null)
const recordedChunks = ref<Blob[]>([])

// Voice Playback State
const currentlyPlayingVoice = ref<string | null>(null)
const audioElement = ref<HTMLAudioElement | null>(null)
const voiceWaveformInterval = ref<number | null>(null)
const voiceWaveformData = ref<Record<string, number[]>>({})

// Computed
const sortedMessages = computed(() => {
  return [...messagingStore.messages].sort((a, b) =>
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
})

const canSend = computed(() => {
  return newMessage.value.trim() && !isSending.value && selectedConversation.value
})

const filteredConversations = computed(() => {
  if (!searchQuery.value) return messagingStore.sortedConversations
  const query = searchQuery.value.toLowerCase()
  return messagingStore.sortedConversations.filter(conv =>
    conv.other_participant?.username.toLowerCase().includes(query)
  )
})

// Check if both users have Telegram bound and display enabled
const canShowTelegramChat = computed(() => {
  // Current user must have Telegram bound and display enabled
  const currentUser = authStore.user
  const hasCurrentUserTg = currentUser?.telegram_username && currentUser?.show_telegram_account

  // Other participant must have Telegram username (which means they have it bound and display enabled)
  const otherUser = selectedConversation.value?.other_participant
  const hasOtherUserTg = otherUser?.telegram_username

  return hasCurrentUserTg && hasOtherUserTg
})

// Methods
const isOwnMessage = (message: PrivateMessage) => {
  return message.sender.id === authStore.user?.id
}

const formatTime = (dateString: string) => {
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
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const formatDuration = (seconds?: number) => {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const getLastMessagePreview = (lastMessage: Conversation['last_message']) => {
  if (!lastMessage) return '还没有消息'
  return lastMessage.content
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainerRef.value) {
      messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight
    }
  })
}

const autoResize = () => {
  const textarea = inputRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px'
  }
}

const selectConversation = async (conv: Conversation) => {
  selectedConversation.value = conv
  messagingStore.setCurrentConversation(conv)
  await loadMessages()
}

const loadMessages = async () => {
  if (!selectedConversation.value) return

  // Skip API call for temporary conversations (waiting for first message to create real conversation)
  if (selectedConversation.value.id.startsWith('temp-')) {
    return
  }

  await messagingStore.fetchMessages(selectedConversation.value.id, true)
  scrollToBottom()
}

const backToList = () => {
  selectedConversation.value = null
  messagingStore.setCurrentConversation(null)
}

const handleSend = async () => {
  if ((!newMessage.value.trim() && !selectedImage.value) || !selectedConversation.value || isSending.value) return

  isSending.value = true
  const isTempConversation = selectedConversation.value.id.startsWith('temp-')
  const recipientId = selectedConversation.value.other_participant!.id

  try {
    if (selectedImage.value) {
      // Send image message
      await messagingApi.sendMessage({
        recipient_id: recipientId,
        message_type: 'image',
        content: newMessage.value.trim(),
        file: selectedImage.value
      })
      clearImage()
    } else {
      // Send text message
      await messagingApi.sendMessage({
        recipient_id: recipientId,
        message_type: 'text',
        content: newMessage.value.trim()
      })
    }

    newMessage.value = ''

    // Reset textarea
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
    }

    // Refresh conversation list to get the new/updated conversation
    await messagingStore.fetchConversations()

    // If this was a temporary conversation, update selectedConversation to the real one
    if (isTempConversation) {
      const realConversation = messagingStore.conversations.find(
        c => c.other_participant?.id === recipientId
      )
      if (realConversation) {
        selectedConversation.value = realConversation
        messagingStore.setCurrentConversation(realConversation)
      }
    }

    // Refresh messages
    await loadMessages()
  } catch (err) {
    console.error('Failed to send message:', err)
  } finally {
    isSending.value = false
  }
}

const viewProfile = () => {
  if (selectedConversation.value?.other_participant?.id) {
    closeModal()
    router.push({
      name: 'profile',
      params: { id: selectedConversation.value.other_participant.id.toString() }
    })
  }
}

const openTelegramChat = () => {
  const otherUser = selectedConversation.value?.other_participant
  if (otherUser?.telegram_username) {
    // Open Telegram chat using deeplink
    const telegramUrl = `https://t.me/${otherUser.telegram_username}`
    window.open(telegramUrl, '_blank')
  }
}

const closeModal = () => {
  emit('close')
}

const handleOverlayClick = () => {
  closeModal()
}

// Emoji Methods
const toggleEmojiPanel = () => {
  showEmojiPanel.value = !showEmojiPanel.value
}

const insertEmoji = (emoji: string) => {
  newMessage.value += emoji
  showEmojiPanel.value = false
  inputRef.value?.focus()
}

// Image Methods
const triggerImageUpload = () => {
  imageInputRef.value?.click()
}

const handleImageSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedImage.value = file
    selectedImagePreview.value = URL.createObjectURL(file)
  }
}

const clearImage = () => {
  selectedImage.value = null
  selectedImagePreview.value = ''
  if (imageInputRef.value) {
    imageInputRef.value.value = ''
  }
}

const previewImageUrl = ref<string | null>(null)

const openImagePreview = (url: string) => {
  previewImageUrl.value = url
}

const closeImagePreview = () => {
  previewImageUrl.value = null
}

// Voice Recording Methods
const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.value = new MediaRecorder(stream)
    recordedChunks.value = []

    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunks.value.push(event.data)
      }
    }

    mediaRecorder.value.onstop = async () => {
      const blob = new Blob(recordedChunks.value, { type: 'audio/webm' })
      await sendVoiceMessage(blob, recordingTime.value)

      // Stop all tracks
      stream.getTracks().forEach(track => track.stop())
    }

    mediaRecorder.value.start()
    isRecording.value = true
    recordingTime.value = 0

    recordingInterval.value = window.setInterval(() => {
      recordingTime.value++
    }, 1000)
  } catch (err) {
    console.error('Failed to start recording:', err)
    alert('无法访问麦克风，请检查权限设置')
  }
}

const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop()
    isRecording.value = false

    if (recordingInterval.value) {
      clearInterval(recordingInterval.value)
      recordingInterval.value = null
    }
  }
}

const cancelRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop()
    isRecording.value = false

    if (recordingInterval.value) {
      clearInterval(recordingInterval.value)
      recordingInterval.value = null
    }

    // Stop all tracks
    mediaRecorder.value.stream?.getTracks().forEach(track => track.stop())
  }
}

const formatRecordingTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const sendVoiceMessage = async (blob: Blob, duration: number) => {
  if (!selectedConversation.value) return

  isSending.value = true
  const isTempConversation = selectedConversation.value.id.startsWith('temp-')
  const recipientId = selectedConversation.value.other_participant!.id

  try {
    const file = new File([blob], 'voice.webm', { type: 'audio/webm' })

    await messagingApi.sendMessage({
      recipient_id: recipientId,
      message_type: 'voice',
      content: '',
      file: file,
      file_duration: duration
    })

    // Refresh conversation list to get the new/updated conversation
    await messagingStore.fetchConversations()

    // If this was a temporary conversation, update selectedConversation to the real one
    if (isTempConversation) {
      const realConversation = messagingStore.conversations.find(
        c => c.other_participant?.id === recipientId
      )
      if (realConversation) {
        selectedConversation.value = realConversation
        messagingStore.setCurrentConversation(realConversation)
      }
    }

    // Refresh messages
    await loadMessages()
  } catch (err) {
    console.error('Failed to send voice message:', err)
  } finally {
    isSending.value = false
  }
}

// Voice Playback Methods
const toggleVoicePlayback = (messageId: string, fileUrl: string) => {
  if (currentlyPlayingVoice.value === messageId) {
    // Stop playback
    audioElement.value?.pause()
    currentlyPlayingVoice.value = null
    if (voiceWaveformInterval.value) {
      clearInterval(voiceWaveformInterval.value)
      voiceWaveformInterval.value = null
    }
  } else {
    // Start playback
    if (audioElement.value) {
      audioElement.value.pause()
    }

    audioElement.value = new Audio(fileUrl)
    audioElement.value.play()
    currentlyPlayingVoice.value = messageId

    // Generate random waveform data for animation
    voiceWaveformData.value[messageId] = Array.from({ length: 10 }, () => Math.random() * 20 + 5)

    voiceWaveformInterval.value = window.setInterval(() => {
      // Update waveform animation
      voiceWaveformData.value[messageId] = Array.from({ length: 10 }, () => Math.random() * 20 + 5)
    }, 100)

    audioElement.value.onended = () => {
      currentlyPlayingVoice.value = null
      if (voiceWaveformInterval.value) {
        clearInterval(voiceWaveformInterval.value)
        voiceWaveformInterval.value = null
      }
    }
  }
}

const getWaveHeight = (index: number, messageId: string) => {
  if (currentlyPlayingVoice.value !== messageId) {
    return 5 + (index % 3) * 3
  }
  return voiceWaveformData.value[messageId]?.[index - 1] || 5
}

// Auto-select conversation when chatModalUserId is set
const autoSelectConversation = async (userId: number) => {
  // Find existing conversation with this user (conversations already loaded by caller)
  const existingConv = messagingStore.conversations.find(
    c => c.other_participant?.id === userId
  )

  if (existingConv) {
    await selectConversation(existingConv)
  } else {
    // Create temporary conversation for new chat
    const username = messagingStore.chatModalUsername || '未知用户'
    const tempConv = await messagingStore.startConversation(userId, username)
    selectedConversation.value = tempConv
  }

  // Clear store values to avoid re-triggering
  messagingStore.chatModalUserId = undefined
  messagingStore.chatModalUsername = undefined
}

// Watch for visibility changes
watch(() => props.isVisible, async (visible) => {
  if (visible) {
    document.body.style.overflow = 'hidden'
    await messagingStore.fetchConversations()

    // Check if we need to auto-select a conversation
    if (messagingStore.chatModalUserId) {
      await autoSelectConversation(messagingStore.chatModalUserId)
    }
  } else {
    document.body.style.overflow = ''
    selectedConversation.value = null
    messagingStore.setCurrentConversation(null)
  }
})

// Watch for chatModalUserId changes while modal is already open
watch(() => messagingStore.chatModalUserId, async (userId) => {
  if (userId && props.isVisible) {
    await autoSelectConversation(userId)
  }
})

// Cleanup
onUnmounted(() => {
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value)
  }
  if (voiceWaveformInterval.value) {
    clearInterval(voiceWaveformInterval.value)
  }
  if (audioElement.value) {
    audioElement.value.pause()
  }
})

onMounted(() => {
  if (props.isVisible) {
    messagingStore.fetchConversations()
    document.body.style.overflow = 'hidden'
  }
})
</script>

<style scoped>
/* Chat Modal Transitions */
.chat-modal-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-modal-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-modal-enter-from {
  opacity: 0;
}

.chat-modal-enter-from .chat-modal-card {
  transform: scale(0.9) translateY(20px);
  opacity: 0;
}

.chat-modal-leave-to {
  opacity: 0;
}

.chat-modal-leave-to .chat-modal-card {
  transform: scale(0.9) translateY(20px);
  opacity: 0;
}

/* Overlay */
.chat-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  padding: 1rem;
}

/* Container */
.chat-modal-container {
  max-width: 900px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

/* Card - Split Layout */
.chat-modal-card {
  background: white;
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  display: flex;
  overflow: hidden;
  height: 600px;
  max-height: 80vh;
  animation: chat-modal-bounce 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

@keyframes chat-modal-bounce {
  0% {
    transform: scale(0.8) translateY(20px);
    opacity: 0;
  }
  50% {
    transform: scale(1.02);
  }
  100% {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

/* Sidebar */
.chat-sidebar {
  width: 320px;
  border-right: 3px solid #000;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border-bottom: 3px solid #000;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-search {
  position: relative;
  padding: 0.75rem;
  border-bottom: 2px solid #e9ecef;
}

.search-input {
  width: 100%;
  padding: 0.5rem 0.75rem 0.5rem 2rem;
  border: 2px solid #000;
  border-radius: 8px;
  font-size: 0.875rem;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.search-input:focus {
  outline: none;
  box-shadow: 3px 3px 0 #000;
  transform: translate(-1px, -1px);
}

.search-icon {
  position: absolute;
  left: 1.25rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.875rem;
  opacity: 0.5;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.sidebar-loading,
.sidebar-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #6c757d;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  margin-bottom: 0.5rem;
}

.conversation-item:hover {
  background: white;
  border-color: #000;
  box-shadow: 2px 2px 0 #000;
}

.conversation-item.active {
  background: #007bff;
  color: white;
  border-color: #000;
  box-shadow: 2px 2px 0 #000;
}

.conversation-item.unread {
  background: #e3f2fd;
}

.conversation-item.unread.active {
  background: #007bff;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-name {
  font-weight: 700;
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-preview {
  font-size: 0.75rem;
  opacity: 0.7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 0.25rem;
}

.conversation-item.active .conversation-preview {
  opacity: 0.9;
}

.conversation-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.conversation-time {
  font-size: 0.7rem;
  opacity: 0.6;
}

.unread-badge {
  background: #dc3545;
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.125rem 0.375rem;
  border-radius: 10px;
  border: 2px solid #000;
  min-width: 18px;
  text-align: center;
}

/* Chat Area */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border-bottom: 3px solid #000;
}

.back-btn {
  display: none;
  background: rgba(0, 0, 0, 0.2);
  border: 2px solid #000;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: 700;
  color: white;
  margin-right: 0.5rem;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.header-placeholder {
  flex: 1;
  text-align: center;
  opacity: 0.8;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 800;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.online-status {
  font-size: 0.75rem;
  opacity: 0.8;
  color: #90EE90;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn,
.close-btn {
  background: rgba(0, 0, 0, 0.2);
  border: 2px solid #000;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: 700;
  font-size: 1rem;
  transition: all 0.2s ease;
  color: white;
}

.action-btn:hover,
.close-btn:hover {
  background: rgba(0, 0, 0, 0.4);
  transform: scale(1.1);
}

.action-btn.telegram-btn {
  background: linear-gradient(135deg, #0088cc, #005f8a);
  border-color: #000;
}

.action-btn.telegram-btn:hover {
  background: linear-gradient(135deg, #0099e6, #0077b3);
  transform: scale(1.1);
  box-shadow: 0 0 10px rgba(0, 136, 204, 0.5);
}

/* Messages Area */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6c757d;
}

.loading-state,
.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #6c757d;
}

.error-state {
  color: #dc3545;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.5rem 1.5rem;
  background: #007bff;
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 0.75rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.empty-hint {
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

/* Message Items */
.message-item {
  display: flex;
  max-width: 80%;
}

.message-item:not(.own) {
  align-self: flex-start;
}

.message-item.own {
  align-self: flex-end;
  justify-content: flex-end;
}

.message-bubble {
  background: white;
  padding: 0.625rem 0.875rem;
  border-radius: 12px;
  border: 2px solid #000;
  box-shadow: 3px 3px 0 #000;
  max-width: 100%;
}

.message-item.own .message-bubble {
  background: #007bff;
  color: white;
}

.message-content {
  font-size: 0.9375rem;
  line-height: 1.4;
  word-break: break-word;
}

/* Image Message */
.message-image {
  max-width: 250px;
}

.message-image-preview {
  width: 100%;
  border-radius: 8px;
  border: 2px solid #000;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.message-image-preview:hover {
  transform: scale(1.02);
}

.image-caption {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  opacity: 0.9;
}

/* Voice Message */
.message-voice {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 150px;
}

.voice-play-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid #000;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.voice-play-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.voice-play-btn.playing {
  background: #28a745;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.voice-waveform {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.voice-duration {
  font-size: 0.75rem;
  opacity: 0.8;
  min-width: 35px;
}

.waveform-bars {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 20px;
}

.wave-bar {
  width: 3px;
  background: currentColor;
  border-radius: 2px;
  opacity: 0.6;
  transition: height 0.1s ease;
}

.message-item.own .wave-bar {
  opacity: 0.9;
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
  color: rgba(255, 255, 255, 0.8);
}

.read-status {
  font-weight: 600;
}

/* Input Area */
.chat-input {
  padding: 0.75rem;
  background: white;
  border-top: 3px solid #000;
}

/* Emoji Panel */
.emoji-panel {
  background: #f8f9fa;
  border: 2px solid #000;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  box-shadow: 3px 3px 0 #000;
}

.emoji-categories {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem;
  border-bottom: 1px solid #e9ecef;
  overflow-x: auto;
}

.emoji-category-btn {
  background: white;
  border: 2px solid #000;
  border-radius: 6px;
  padding: 0.375rem;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s ease;
}

.emoji-category-btn:hover,
.emoji-category-btn.active {
  background: #007bff;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
}

.emoji-list {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 0.25rem;
  padding: 0.5rem;
  max-height: 150px;
  overflow-y: auto;
}

.emoji-btn {
  background: transparent;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.emoji-btn:hover {
  background: #e9ecef;
  transform: scale(1.2);
}

/* Image Preview Bar */
.image-preview-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #e3f2fd;
  border: 2px solid #000;
  border-radius: 8px;
  margin-bottom: 0.5rem;
}

.preview-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #000;
}

.preview-text {
  flex: 1;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clear-preview-btn {
  background: #dc3545;
  color: white;
  border: 2px solid #000;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.75rem;
}

/* Voice Recording Bar */
.voice-recording-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  background: #ffebee;
  border: 2px solid #000;
  border-radius: 8px;
  margin-bottom: 0.5rem;
}

.recording-indicator {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.recording-time {
  flex: 1;
  font-weight: 700;
  font-family: monospace;
}

.stop-recording-btn,
.cancel-recording-btn {
  padding: 0.375rem 0.75rem;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.75rem;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.stop-recording-btn {
  background: #28a745;
  color: white;
}

.cancel-recording-btn {
  background: #6c757d;
  color: white;
}

.stop-recording-btn:hover,
.cancel-recording-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

/* Input Wrapper */
.input-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
}

.input-action-btn {
  background: #f8f9fa;
  border: 2px solid #000;
  border-radius: 8px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.25rem;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.input-action-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
  background: #e9ecef;
}

.input-action-btn.active {
  background: #007bff;
  color: white;
}

.input-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-wrapper textarea {
  flex: 1;
  padding: 0.625rem 0.875rem;
  border: 2px solid #000;
  border-radius: 8px;
  font-size: 0.9375rem;
  resize: none;
  min-height: 40px;
  max-height: 100px;
  font-family: inherit;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.input-wrapper textarea:focus {
  outline: none;
  box-shadow: 3px 3px 0 #000;
  transform: translate(-1px, -1px);
}

.input-wrapper textarea:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-btn {
  background: #28a745;
  color: white;
  border: 2px solid #000;
  border-radius: 8px;
  padding: 0.625rem 1.25rem;
  font-weight: 700;
  font-size: 0.875rem;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  white-space: nowrap;
  height: 40px;
}

.send-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.send-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.7;
}

/* Image Preview Overlay */
.image-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  padding: 2rem;
}

.image-preview-full {
  max-width: 100%;
  max-height: 90vh;
  border-radius: 8px;
  border: 4px solid white;
}

.close-preview-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: white;
  border: 2px solid #000;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.25rem;
  font-weight: 700;
  box-shadow: 2px 2px 0 #000;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Mobile Responsive */
@media (max-width: 640px) {
  .chat-modal-overlay {
    padding: 0;
    align-items: flex-end;
  }

  .chat-modal-container {
    max-width: 100%;
    max-height: 100vh;
  }

  .chat-modal-card {
    height: 100vh;
    max-height: 100vh;
    border-radius: 12px 12px 0 0;
    border-bottom: none;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
    animation: chat-modal-slide-up 0.3s ease;
    flex-direction: column;
  }

  .chat-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 3px solid #000;
    display: flex;
  }

  .chat-sidebar.hidden {
    display: none;
  }

  .chat-area {
    display: none;
  }

  .chat-area.active {
    display: flex;
  }

  .back-btn {
    display: flex;
  }

  @keyframes chat-modal-slide-up {
    0% {
      transform: translateY(100%);
    }
    100% {
      transform: translateY(0);
    }
  }

  .chat-header {
    padding: 0.875rem;
  }

  .chat-messages {
    padding: 0.875rem;
  }

  .message-item {
    max-width: 85%;
  }

  .message-image {
    max-width: 200px;
  }

  .chat-input {
    padding: 0.625rem;
  }

  .emoji-list {
    grid-template-columns: repeat(6, 1fr);
  }

  .input-wrapper textarea {
    font-size: 16px;
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .chat-modal-enter-active,
  .chat-modal-leave-active {
    transition: opacity 0.2s ease;
  }

  .chat-modal-card {
    animation: none;
  }
}

/* Scrollbar Styling */
.chat-messages::-webkit-scrollbar,
.conversation-list::-webkit-scrollbar,
.emoji-list::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track,
.conversation-list::-webkit-scrollbar-track,
.emoji-list::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb,
.conversation-list::-webkit-scrollbar-thumb,
.emoji-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover,
.conversation-list::-webkit-scrollbar-thumb:hover,
.emoji-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
