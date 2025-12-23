import { defineStore } from 'pinia'
import { ref } from 'vue'
import { postsApi } from '../lib/api'
import type { Post, PaginatedResponse } from '../types/index'

export const usePostsStore = defineStore('posts', () => {
  // State
  const posts = ref<Post[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalCount = ref(0)
  const hasMore = ref(true)

  // Cache state for infinite scroll
  const postsCache = ref<Map<string, {
    data: PaginatedResponse<Post>
    timestamp: number
    page: number
  }>>(new Map())

  // Cache configuration
  const CACHE_TTL = 5 * 60 * 1000 // 5 minutes
  const MAX_CACHE_SIZE = 50 // Maximum cached pages

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

  // Get paginated posts for infinite scroll with caching
  const getPaginatedPosts = async (
    page: number,
    pageSize: number = 10,
    useCache: boolean = true
  ): Promise<PaginatedResponse<Post>> => {
    const cacheKey = `posts_${page}_${pageSize}`

    // Check cache first if caching is enabled
    if (useCache && postsCache.value.has(cacheKey)) {
      const cached = postsCache.value.get(cacheKey)!
      const now = Date.now()

      if (now - cached.timestamp < CACHE_TTL) {
        console.log('📦 Using cached posts for page', page)
        return cached.data
      } else {
        // Remove expired cache
        console.log('🗑️ Removing expired cache for page', page)
        postsCache.value.delete(cacheKey)
      }
    }

    // Fetch from API
    console.log('🌐 Fetching posts from API for page', page)
    const response = await postsApi.getPosts({
      page,
      page_size: pageSize
    })

    // Cache the response if caching is enabled
    if (useCache) {
      // Manage cache size - remove oldest entries if at limit
      if (postsCache.value.size >= MAX_CACHE_SIZE) {
        const oldestKey = postsCache.value.keys().next().value
        if (oldestKey) {
          console.log('🧹 Evicting oldest cache entry:', oldestKey)
          postsCache.value.delete(oldestKey)
        }
      }

      postsCache.value.set(cacheKey, {
        data: response,
        timestamp: Date.now(),
        page
      })
      console.log('💾 Cached posts for page', page)
    }

    return response
  }

  const likePost = async (postId: string) => {
    try {
      const response = await postsApi.likePost(postId)

      // Update local state
      const postIndex = posts.value.findIndex(post => post.id === postId)
      if (postIndex !== -1 && posts.value[postIndex]) {
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
      if (postIndex !== -1 && posts.value[postIndex]) {
        posts.value[postIndex].likes_count = response.likes_count
        posts.value[postIndex].user_has_liked = false
      }
    } catch (err) {
      console.error('Error unliking post:', err)
      throw err
    }
  }

  // Cache management methods
  const clearPostsCache = () => {
    console.log('🗑️ Clearing all posts cache')
    postsCache.value.clear()
  }

  const invalidatePostsCache = () => {
    console.log('🗑️ Invalidating posts cache due to new content')
    clearPostsCache()
  }

  const createPost = async (postData: {
    content: string
    post_type: 'normal' | 'checkin'
    images?: File[]
  }) => {
    try {
      const newPost = await postsApi.createPost(postData)
      posts.value.unshift(newPost) // Add to beginning of array

      // Invalidate cache since new content was added
      invalidatePostsCache()

      return newPost
    } catch (err) {
      console.error('Error creating post:', err)
      throw err
    }
  }

  const voteOnCheckinPost = async (postId: string, voteType: 'pass' | 'reject') => {
    try {
      const response = await postsApi.voteOnCheckinPost(postId, voteType)

      // Update local state
      const postIndex = posts.value.findIndex(post => post.id === postId)
      if (postIndex !== -1 && posts.value[postIndex]) {
        posts.value[postIndex].user_vote = voteType
        if (posts.value[postIndex].voting_session) {
          posts.value[postIndex].voting_session!.total_coins_collected = response.total_coins_collected
        }
      }

      return response
    } catch (err) {
      console.error('Error voting on checkin post:', err)
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
    deletePost,
    voteOnCheckinPost,
    // Cache management
    clearPostsCache,
    invalidatePostsCache
  }
})