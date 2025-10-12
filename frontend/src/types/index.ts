// Lock Status Types
export interface ActiveLockTask {
  id: string
  title: string
  difficulty: 'easy' | 'normal' | 'hard' | 'hell'
  start_time?: string
  end_time?: string
  time_remaining_ms?: number
  is_expired: boolean
  can_complete: boolean
  duration_value?: number
  duration_type?: 'fixed' | 'random'
  duration_max?: number
}

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
  active_lock_task?: ActiveLockTask | null
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
  task_type: 'lock' | 'board'
  title: string
  description: string
  status: 'pending' | 'active' | 'voting' | 'completed' | 'failed' | 'open' | 'taken' | 'submitted'
  // 带锁任务字段
  duration_type?: 'fixed' | 'random'
  duration_value?: number
  duration_max?: number
  difficulty?: 'easy' | 'normal' | 'hard' | 'hell'
  unlock_type?: 'time' | 'vote'
  vote_threshold?: number
  vote_agreement_ratio?: number // 投票同意比例 (0.5 = 50%)
  // 投票期相关字段
  voting_start_time?: string
  voting_end_time?: string
  voting_duration?: number // 投票持续时间（分钟）
  vote_failed_penalty_minutes?: number // 投票失败加时分钟数
  key_holder?: User
  key_id?: string
  overtime_multiplier?: number // 加时惩罚倍数 (3, 5, 10)
  overtime_duration?: number // 置顶时间 (分钟)
  start_time?: string
  end_time?: string
  // 任务板字段
  reward?: number
  deadline?: string
  max_duration?: number // 任务最大完成时间 (小时)
  taker?: User
  taken_at?: string
  completion_proof?: string
  completed_at?: string
  // 计算字段
  vote_count?: number
  vote_agreement_count?: number
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
  max_duration: number // 任务最大完成时间 (小时)
  status: 'open' | 'taken' | 'completed' | 'failed'
  taker?: User
  taken_at?: string
  completion_proof?: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export interface TaskKey {
  id: string
  task_id: string
  holder: User
  created_at: string
  used_at?: string
  status: 'active' | 'used'
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
  task_type: 'lock' | 'board'
  title: string
  description: string
  // 带锁任务字段
  duration_type?: 'fixed' | 'random'
  duration_value?: number
  duration_max?: number
  difficulty?: 'easy' | 'normal' | 'hard' | 'hell'
  unlock_type?: 'time' | 'vote'
  vote_threshold?: number
  vote_agreement_ratio?: number
  overtime_multiplier?: number
  overtime_duration?: number
  // 任务板字段
  reward?: number
  deadline?: string
  max_duration?: number
}

// Store Types (Pinia stores)
export interface UserStore {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  updateProfile: (data: Partial<User>) => Promise<void>
}

// Game Store Types
export interface ItemType {
  id: string
  name: 'photo_paper' | 'photo' | 'drift_bottle' | 'key' | 'note'
  display_name: string
  description: string
  icon: string
  is_consumable: boolean
  created_at: string
}

export interface Item {
  id: string
  item_type: ItemType
  owner: User
  inventory?: UserInventory
  properties: Record<string, any>
  status: 'available' | 'used' | 'expired' | 'in_drift_bottle' | 'buried'
  created_at: string
  used_at?: string
  expires_at?: string
}

export interface UserInventory {
  user: number
  items: Item[]
  max_slots: number
  used_slots: number
  available_slots: number
  created_at: string
  updated_at: string
}

export interface StoreItem {
  id: string
  item_type: ItemType
  name: string
  description: string
  price: number
  icon: string
  is_available: boolean
  stock?: number
  daily_limit?: number
  level_requirement: number
  created_at: string
  updated_at: string
}

export interface Purchase {
  id: string
  user: User
  store_item: StoreItem
  item: Item
  price_paid: number
  created_at: string
}

export interface Game {
  id: string
  game_type: 'time_wheel' | 'rock_paper_scissors' | 'exploration'
  creator: User
  participants: GameParticipant[]
  bet_amount: number
  max_players: number
  status: 'waiting' | 'active' | 'completed' | 'cancelled'
  game_data: Record<string, any>
  result: Record<string, any>
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface GameParticipant {
  game: string
  user: User
  joined_at: string
  action: Record<string, any>
}

export interface DriftBottleItem {
  id: string
  sender: User
  finder?: User
  message: string
  items: Item[]
  drift_duration: number
  location_hint: string
  status: 'floating' | 'found' | 'expired'
  created_at: string
  found_at?: string
  expires_at: string
}

export interface BuriedTreasure {
  id: string
  burier: User
  finder?: User
  item: Item
  location_zone: string
  location_hint: string
  difficulty: 'easy' | 'normal' | 'hard'
  status: 'buried' | 'found' | 'expired'
  created_at: string
  found_at?: string
  expires_at: string
}

export interface GameSession {
  id: string
  user: User
  game_type: string
  bet_amount: number
  result_data: Record<string, any>
  related_task?: string
  created_at: string
}

export interface ExplorationZone {
  name: string
  display_name: string
  description: string
  difficulty: 'easy' | 'normal' | 'hard'
  treasure_count: number
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