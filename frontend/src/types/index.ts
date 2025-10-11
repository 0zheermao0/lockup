// User Types
export interface User {
  id: number
  username: string
  email: string
  level: 1 | 2 | 3 | 4
  activity_score: number
  last_active: string
  location_precision: number
  coins: number
  avatar?: string
  bio: string
  total_posts: number
  total_likes_received: number
  total_tasks_completed: number
  created_at: string
  updated_at: string
}

export interface UserProfile extends User {
  is_friend?: boolean
  friendship_status?: 'pending' | 'accepted' | 'blocked'
}

// Post Types
export interface Post {
  id: string
  user: User
  post_type: 'normal' | 'checkin'
  content: string
  latitude?: number
  longitude?: number
  location_name?: string
  verification_string?: string
  is_verified: boolean
  likes_count: number
  comments_count: number
  images: PostImage[]
  comments?: Comment[]
  created_at: string
  updated_at: string
  user_has_liked?: boolean
}

export interface PostImage {
  id: number
  image: string
  order: number
  created_at: string
}

export interface Comment {
  id: string
  user: User
  post_id: string
  content: string
  parent?: string
  likes_count: number
  replies: Comment[]
  created_at: string
  updated_at: string
  is_liked?: boolean
}

// Task Types
export interface LockTask {
  id: string
  user: User
  title: string
  description: string
  duration_type: 'fixed' | 'random'
  duration_value: number
  duration_max?: number
  difficulty: 'easy' | 'normal' | 'hard' | 'hell'
  unlock_type: 'time' | 'vote'
  vote_threshold?: number
  key_holder?: User
  start_time: string
  end_time?: string
  status: 'pending' | 'active' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface TaskBoard {
  id: string
  publisher: User
  title: string
  description: string
  reward: number
  deadline: string
  status: 'open' | 'taken' | 'completed' | 'failed'
  taker?: User
  completion_proof?: string
  created_at: string
  updated_at: string
}

// Game Types
export interface GameItem {
  id: string
  type: 'key' | 'photo' | 'bottle' | 'coin'
  owner: User
  data: Record<string, any>
  latitude?: number
  longitude?: number
  status: 'active' | 'used' | 'hidden'
  created_at: string
}

export interface DriftBottle {
  id: string
  sender: User
  content: string
  items: GameItem[]
  latitude: number
  longitude: number
  found_by?: User
  found_at?: string
  created_at: string
}

// Friend Types
export interface Friendship {
  id: number
  from_user: User
  to_user: User
  status: 'pending' | 'accepted' | 'blocked'
  created_at: string
  updated_at: string
}

// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
  status: 'success' | 'error'
}

export interface PaginatedResponse<T> {
  results: T[]
  count: number
  next?: string
  previous?: string
}

// Auth Types
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  password_confirm: string
}

export interface AuthResponse {
  user: User
  token: string
  refresh_token?: string
}

// Form Types
export interface PostCreateRequest {
  content: string
  post_type: 'normal' | 'checkin'
  images?: File[]
  latitude?: number
  longitude?: number
  location_name?: string
}

export interface TaskCreateRequest {
  title: string
  description: string
  duration_type: 'fixed' | 'random'
  duration_value: number
  duration_max?: number
  difficulty: 'easy' | 'normal' | 'hard' | 'hell'
  unlock_type: 'time' | 'vote'
  vote_threshold?: number
}

// Store Types
export interface UserStore {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  updateProfile: (data: Partial<User>) => Promise<void>
}

export interface PostStore {
  posts: Post[]
  loading: boolean
  error: string | null
  fetchPosts: () => Promise<void>
  createPost: (data: PostCreateRequest) => Promise<void>
  likePost: (postId: string) => Promise<void>
  addComment: (postId: string, content: string, parentId?: string) => Promise<void>
}

export interface TaskStore {
  tasks: LockTask[]
  taskBoards: TaskBoard[]
  loading: boolean
  error: string | null
  fetchTasks: () => Promise<void>
  createTask: (data: TaskCreateRequest) => Promise<void>
  updateTask: (id: string, data: Partial<LockTask>) => Promise<void>
}

// UI Types
export interface NavigationItem {
  name: string
  href: string
  icon: any // Generic icon component type for Vue
  badge?: number
}

export interface NotificationItem {
  id: string
  type: 'like' | 'comment' | 'friend' | 'task' | 'system'
  title: string
  message: string
  read: boolean
  created_at: string
  link?: string
}

// Geolocation Types
export interface LocationData {
  latitude: number
  longitude: number
  accuracy: number
  timestamp: number
}

export interface GeolocationError {
  code: number
  message: string
}