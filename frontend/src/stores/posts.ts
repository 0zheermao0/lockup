import { defineStore } from 'pinia'
import { ref } from 'vue'
import { postsApi } from '../lib/api'
import type { Post } from '../types/index.js'

export const usePostsStore = defineStore('posts', () => {
  // State
  const posts = ref<Post[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  const fetchPosts = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await postsApi.getPosts()
      posts.value = response.results || []
    } catch (err: any) {
      error.value = '加载动态失败'
      console.error('Error fetching posts:', err)
    } finally {
      loading.value = false
    }
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
    // Actions
    fetchPosts,
    likePost,
    unlikePost,
    createPost,
    deletePost
  }
})