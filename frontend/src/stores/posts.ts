import { defineStore } from 'pinia'
import { ref } from 'vue'
import { postsApi } from '../lib/api'
import type { Post, PaginatedResponse } from '../types/index.js'

export const usePostsStore = defineStore('posts', () => {
  // State
  const posts = ref<Post[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalCount = ref(0)
  const hasMore = ref(true)

  // Actions
  const fetchPosts = async (params?: {
    type?: string;
    search?: string;
    user?: number;
    page?: number;
    page_size?: number;
  }) => {
    loading.value = true
    error.value = null

    try {
      const response = await postsApi.getPosts({
        ...params,
        page: params?.page || 1
      })

      if (params?.page === 1 || !params?.page) {
        // First page or reset - replace all posts
        posts.value = response.results || []
        currentPage.value = 1
      } else {
        // Subsequent pages - append to existing posts
        posts.value.push(...(response.results || []))
        currentPage.value = params.page
      }

      totalCount.value = response.count || 0
      hasMore.value = !!response.next
    } catch (err: any) {
      error.value = '加载动态失败'
      console.error('Error fetching posts:', err)
    } finally {
      loading.value = false
    }
  }

  // Get paginated posts for infinite scroll
  const getPaginatedPosts = async (page: number, pageSize: number = 10): Promise<PaginatedResponse<Post>> => {
    const response = await postsApi.getPosts({
      page,
      page_size: pageSize
    })
    return response
  }

  const likePost = async (postId: string) => {
    try {
      const response = await postsApi.likePost(postId)

      // Update local state
      const postIndex = posts.value.findIndex(post => post.id === postId)
      if (postIndex !== -1) {
        posts.value[postIndex].likes_count = response.likes_count
        posts.value[postIndex].user_has_liked = true
      }
    } catch (err) {
      console.error('Error liking post:', err)
      throw err
    }
  }

  const unlikePost = async (postId: string) => {
    try {
      const response = await postsApi.unlikePost(postId)

      // Update local state
      const postIndex = posts.value.findIndex(post => post.id === postId)
      if (postIndex !== -1) {
        posts.value[postIndex].likes_count = response.likes_count
        posts.value[postIndex].user_has_liked = false
      }
    } catch (err) {
      console.error('Error unliking post:', err)
      throw err
    }
  }

  const createPost = async (postData: {
    content: string
    post_type: 'normal' | 'checkin'
    images?: File[]
    location?: { latitude: number; longitude: number }
  }) => {
    try {
      const newPost = await postsApi.createPost(postData)
      posts.value.unshift(newPost) // Add to beginning of array
      return newPost
    } catch (err) {
      console.error('Error creating post:', err)
      throw err
    }
  }

  const deletePost = async (postId: string) => {
    try {
      await postsApi.deletePost(postId)

      // Remove from local state
      const postIndex = posts.value.findIndex(post => post.id === postId)
      if (postIndex !== -1) {
        posts.value.splice(postIndex, 1)
      }
    } catch (err) {
      console.error('Error deleting post:', err)
      throw err
    }
  }

  return {
    // State
    posts,
    loading,
    error,
    currentPage,
    totalCount,
    hasMore,
    // Actions
    fetchPosts,
    getPaginatedPosts,
    likePost,
    unlikePost,
    createPost,
    deletePost
  }
})