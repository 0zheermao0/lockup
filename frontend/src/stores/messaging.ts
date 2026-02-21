import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { messagingApi } from '../lib/api'
import type { Conversation, PrivateMessage, User } from '../types/index'

console.log('[MessagingStore] Module loading...')

export const useMessagingStore = defineStore('messaging', () => {
  console.log('[MessagingStore] Store instance created')
  // State
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<PrivateMessage[]>([])
  const isLoading = ref(false)
  const isLoadingMessages = ref(false)
  const error = ref<string | null>(null)
  const totalUnreadCount = ref(0)

  // Chat Modal State
  const isChatModalVisible = ref(false)
  const chatModalUserId = ref<number | undefined>(undefined)
  const chatModalUsername = ref<string | undefined>(undefined)

  // Pagination
  const messagesPage = ref(1)
  const hasMoreMessages = ref(true)

  // Getters
  const sortedConversations = computed(() => {
    return [...conversations.value].sort((a, b) => {
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    })
  })

  const unreadConversations = computed(() => {
    return conversations.value.filter(c => c.unread_count > 0)
  })

  // Actions
  const fetchConversations = async () => {
    isLoading.value = true
    error.value = null
    try {
      const response = await messagingApi.getConversations()
      conversations.value = response.results || []
      updateTotalUnreadCount()
      return response.results
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取会话列表失败'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchMessages = async (conversationId: string, reset = true) => {
    if (reset) {
      messagesPage.value = 1
      hasMoreMessages.value = true
      messages.value = []
    }

    if (!hasMoreMessages.value) return

    isLoadingMessages.value = true
    try {
      const response = await messagingApi.getMessages(conversationId, {
        page: messagesPage.value,
        page_size: 20
      })

      const newMessages = response.results || []
      if (reset) {
        messages.value = newMessages
      } else {
        messages.value.push(...newMessages)
      }

      hasMoreMessages.value = response.next !== null
      if (hasMoreMessages.value) {
        messagesPage.value++
      }

      return newMessages
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取消息失败'
      throw err
    } finally {
      isLoadingMessages.value = false
    }
  }

  const sendMessage = async (recipientId: number, content: string) => {
    try {
      const result = await messagingApi.sendMessage({
        recipient_id: recipientId,
        content,
        message_type: 'text'
      })

      // 如果当前在会话中，添加到消息列表
      if (currentConversation.value) {
        messages.value.unshift(result.data)
      }

      // 刷新会话列表以更新最后一条消息
      await fetchConversations()

      return result
    } catch (err) {
      error.value = err instanceof Error ? err.message : '发送消息失败'
      throw err
    }
  }

  const markAsRead = async (conversationId: string) => {
    try {
      const result = await messagingApi.markConversationAsRead(conversationId)

      // 更新本地状态
      const conversation = conversations.value.find(c => c.id === conversationId)
      if (conversation) {
        conversation.unread_count = 0
      }

      updateTotalUnreadCount()
      return result
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  const updateTotalUnreadCount = () => {
    totalUnreadCount.value = conversations.value.reduce((sum, c) => sum + c.unread_count, 0)
  }

  const setCurrentConversation = (conversation: Conversation | null) => {
    currentConversation.value = conversation
    if (conversation && conversation.unread_count > 0) {
      markAsRead(conversation.id)
    }
  }

  const startConversation = async (userId: number, username: string) => {
    // 检查是否已有会话
    const existing = conversations.value.find(c =>
      c.other_participant?.id === userId
    )

    if (existing) {
      setCurrentConversation(existing)
      return existing
    }

    // 如果没有，创建临时会话对象（发送第一条消息后会被真实会话替换）
    const tempConversation: Conversation = {
      id: `temp-${userId}`,
      participants: [],
      other_participant: { id: userId, username } as User,
      last_message: null,
      unread_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    setCurrentConversation(tempConversation)
    return tempConversation
  }

  // Chat Modal Actions
  const openChatModal = (userId: number, username?: string) => {
    console.log('[MessagingStore] Opening chat modal for user:', userId, username)
    chatModalUserId.value = userId
    chatModalUsername.value = username
    isChatModalVisible.value = true
  }

  const closeChatModal = () => {
    console.log('[MessagingStore] Closing chat modal')
    isChatModalVisible.value = false
    // Delay clearing the data to allow for exit animation
    setTimeout(() => {
      chatModalUserId.value = undefined
      chatModalUsername.value = undefined
    }, 300)
  }

  return {
    conversations,
    currentConversation,
    messages,
    isLoading,
    isLoadingMessages,
    error,
    totalUnreadCount,
    // Chat Modal State
    isChatModalVisible,
    chatModalUserId,
    chatModalUsername,
    // Getters
    sortedConversations,
    unreadConversations,
    // Actions
    fetchConversations,
    fetchMessages,
    sendMessage,
    markAsRead,
    setCurrentConversation,
    startConversation,
    openChatModal,
    closeChatModal
  }
})

console.log('[MessagingStore] Module loaded, useMessagingStore:', useMessagingStore)