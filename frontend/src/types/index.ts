// Lock Status Types
export interface ActiveLockTask {
  id: string
  title: string
  difficulty: 'easy' | 'normal' | 'hard' | 'hell'
  status?: 'pending' | 'active' | 'voting' | 'completed' | 'failed'
  start_time?: string
  end_time?: string
  time_remaining_ms?: number
  is_expired: boolean
  can_complete: boolean
  duration_value?: number
  duration_type?: 'fixed' | 'random'
  duration_max?: number
  time_display_hidden?: boolean // 时间显示控制状态
  // 冻结/解冻字段
  is_frozen?: boolean // 是否冻结倒计时
  frozen_at?: string | null // 冻结时间
  frozen_end_time?: string | null // 冻结时保存的原始结束时间
  total_frozen_duration?: number // 总冻结时长（秒）
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
  total_lock_duration: number // 总带锁任务时长（分钟）
  task_completion_rate: number // 任务完成率（%）
  created_at: string
  updated_at: string
  active_lock_task?: ActiveLockTask | null
  is_superuser?: boolean
  is_staff?: boolean
  telegram_username?: string
  telegram_notifications_enabled?: boolean
  show_telegram_account?: boolean
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
  location?: {
    latitude: number
    longitude: number
    name?: string
  }
  verification_string?: string
  is_verified: boolean
  likes_count: number
  comments_count: number
  images: PostImage[]
  comments?: Comment[]
  created_at: string
  updated_at: string
  user_has_liked?: boolean
  user_vote?: 'pass' | 'reject' // User's vote on this post
  voting_session?: {
    voting_deadline: string
    total_coins_collected: number
    is_processed: boolean
    result: 'pending' | 'passed' | 'rejected'
  }
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
  post_id?: string
  content: string
  parent?: string
  root_reply_id?: string
  path?: string
  depth?: number
  likes_count: number
  replies_count?: number
  replies?: Comment[]
  reply_to_user?: User
  images?: PostImage[]
  created_at: string
  updated_at: string
  is_liked?: boolean
}

// Check-in Voting Types
export interface CheckinVote {
  id: string
  post: string
  voter: string
  vote_type: 'pass' | 'reject'
  coins_spent: number
  created_at: string
}

export interface CheckinVotingSession {
  post: string
  voting_deadline: string
  total_coins_collected: number
  is_processed: boolean
  result: 'pending' | 'passed' | 'rejected'
  processed_at?: string
  created_at: string
}

// Task Types
export interface BaseLockTask {
  id: string
  user: User
  title: string
  description?: string
  status: 'pending' | 'active' | 'voting' | 'voting_passed' | 'completed' | 'failed' | 'open' | 'taken' | 'submitted'
  created_at: string
  updated_at: string
  // 计算字段
  vote_count?: number
  vote_agreement_count?: number
  timeline_events?: any[]
}

export interface LockTask extends BaseLockTask {
  task_type: 'lock'
  // 带锁任务字段
  duration_type: 'fixed' | 'random'
  duration_value: number
  duration_max?: number
  difficulty: 'easy' | 'normal' | 'hard' | 'hell'
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
  // 钥匙玩法字段
  time_display_hidden?: boolean // 是否隐藏时间显示
  // 冻结/解冻字段
  is_frozen?: boolean // 是否冻结倒计时
  frozen_at?: string | null // 冻结时间
  frozen_end_time?: string | null // 冻结时保存的原始结束时间
  total_frozen_duration?: number // 总冻结时长（秒）
  // 严格模式字段
  strict_mode?: boolean // 是否为严格模式
  strict_code?: string | null // 严格模式随机码
  // 防护罩字段
  shield_active?: boolean // 是否开启防护罩
  shield_activated_at?: string | null // 防护罩开启时间
  shield_activated_by?: User | null // 开启防护罩的钥匙持有者
  // 任务完成相关字段
  taker?: User
  completion_proof?: string
  submission_files?: TaskSubmissionFile[]
}

export interface TaskParticipant {
  id: string
  participant: User
  status: 'joined' | 'submitted' | 'approved' | 'rejected'
  submission_text?: string
  submitted_at?: string
  reviewed_at?: string
  review_comment?: string
  reward_amount?: number
  joined_at: string
  updated_at: string
  submission_files?: TaskSubmissionFile[]
}

export interface BoardTask extends BaseLockTask {
  task_type: 'board'
  // 任务板字段
  reward: number
  deadline?: string
  max_duration: number // 任务最大完成时间 (小时)
  max_participants: number // 最大参与人数
  completion_rate_threshold?: number // 任务完成率门槛 (0-100)
  taker?: User
  taken_at?: string
  completion_proof?: string
  completed_at?: string
  reject_reason?: string
  submission_files?: TaskSubmissionFile[]
  // 多人任务字段
  participants?: TaskParticipant[]
  participant_count?: number
  available_spots?: number
  is_full?: boolean
  submitted_count?: number
  approved_count?: number
  can_take?: boolean
}

export type Task = LockTask | BoardTask

// Task Submission File Types
export interface TaskSubmissionFile {
  id: string
  file_name: string
  file_url: string
  file_size: number
  file_type: string
  is_image: boolean
  is_video: boolean
  is_primary: boolean
  description?: string
  created_at: string
  uploader?: User
  participant?: TaskParticipant
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

// Pinning System Types - 置顶惩罚系统
export interface PinnedUser {
  id: string
  task: {
    id: string
    title: string
    status: string
    difficulty: string
    task_type: string
  }
  pinned_user: {
    id: string
    username: string
  }
  key_holder: {
    id: string
    username: string
  }
  coins_spent: number
  duration_minutes: number
  is_active: boolean
  position: number | null // 1-3 or null for queue
  created_at: string
  expires_at: string
  activated_at?: string
  time_remaining?: number // calculated field in seconds
}

export interface PinningQueueStatus {
  active_pins: PinnedUser[]
  queued_pins: PinnedUser[]
  active_count: number
  queue_count: number
  max_positions: number
}

export interface PinningCarouselData {
  id: string
  position: number
  task: {
    id: string
    title: string
    status: string
    difficulty: string
    task_type: string
  }
  pinned_user: {
    id: string
    username: string
  }
  key_holder: {
    id: string
    username: string
  }
  time_remaining: number
  expires_at: string
  created_at: string
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
  next: string | null
  previous: string | null
}

export interface PaginatedData<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
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
  // 自动发布动态字段
  autoPost?: boolean // 前端字段
  auto_publish?: boolean // 后端字段
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
  strict_mode?: boolean // 严格模式
  // 任务板字段
  reward?: number
  deadline?: string
  max_duration?: number
  max_participants?: number
  completion_rate_threshold?: number
}

export interface SimplePasswordChangeRequest {
  new_password: string
  new_password_confirm: string
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
  name: 'photo_paper' | 'photo' | 'drift_bottle' | 'key' | 'note' | 'little_treasury' | 'detection_radar' | 'blizzard_bottle' | 'sun_bottle' | 'time_hourglass'
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
  original_owner?: User
  original_creator?: User
  inventory?: UserInventory
  properties: Record<string, any>
  status: 'available' | 'used' | 'expired' | 'in_drift_bottle' | 'buried' | 'in_game'
  created_at: string
  used_at?: string
  expires_at?: string
  is_universal_key?: boolean
}

// Treasury Item Types
export interface TreasuryItem extends Item {
  item_type: ItemType & { name: 'little_treasury' }
  properties: {
    stored_coins: number
    depositor_username?: string
    deposit_time?: string
  }
}

export interface TreasuryDepositRequest {
  amount: number
}

export interface TreasuryDepositResponse {
  success: boolean
  message: string
  stored_coins: number
  user_remaining_coins: number
}

export interface TreasuryWithdrawResponse {
  success: boolean
  message: string
  withdrawn_coins: number
  user_total_coins: number
  depositor_info?: {
    username: string
    deposit_time: string
  }
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
  game_type: 'time_wheel' | 'rock_paper_scissors' | 'exploration' | 'dice'
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
  tasks: Task[]
  taskBoards: TaskBoard[]
  loading: boolean
  error: string | null
  fetchTasks: () => Promise<void>
  createTask: (data: TaskCreateRequest) => Promise<void>
  updateTask: (id: string, data: Partial<Task>) => Promise<void>
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
  notification_type: 'post_liked' | 'post_commented' | 'comment_liked' | 'comment_replied' |
                     'task_overtime_added' | 'task_board_taken' | 'task_board_submitted' | 'task_board_approved' | 'task_board_rejected' |
                     'coins_earned_hourly' | 'coins_earned_daily_login' | 'coins_earned_daily_checkin' | 'coins_earned_daily_board_post' | 'coins_earned_task_reward' | 'coins_spent_task_creation' |
                     'treasure_found' | 'photo_viewed' | 'note_viewed' | 'drift_bottle_found' | 'item_received' | 'item_shared' |
                     'friend_request' | 'friend_accepted' |
                     'level_upgraded' | 'system_announcement' | 'game_result' | 'task_frozen_auto_strict'
  title: string
  message: string
  priority: 'low' | 'normal' | 'high' | 'urgent'
  is_read: boolean
  read_at?: string
  created_at: string
  updated_at: string
  actor?: User
  target_url: string
  related_object_type?: string
  related_object_id?: string
  extra_data: Record<string, any>
  time_ago: string
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

// Multi-person Task API Request Types
export interface ParticipantReviewRequest {
  review_comment?: string
  reward_amount?: number
}

export interface TaskParticipantResponse {
  id: string
  username: string
  status: 'joined' | 'submitted' | 'approved' | 'rejected'
  reward_amount?: number
  review_comment?: string
}

export interface TaskSubmissionRequest {
  submission_text: string
  files?: File[]
  file_descriptions?: string[]
}

// Sun Bottle Response Interface
export interface SunBottleResponse {
  message: string
  unfrozen_tasks_count: number
  affected_users_count: number
  unfrozen_tasks: Array<{
    task_id: string
    task_title: string
    owner: string
  }>
  item_destroyed: boolean
}