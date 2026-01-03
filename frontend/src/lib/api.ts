import type {
  User, Post, Comment, LoginRequest, RegisterRequest, PaginatedResponse,
  StoreItem, UserInventory, Item, Purchase, Game, GameParticipant,
  DriftBottleItem, BuriedTreasure, GameSession, ExplorationZone, NotificationItem,
  SimplePasswordChangeRequest, EmailVerificationSendRequest, EmailVerificationSendResponse,
  EmailVerificationVerifyRequest, EmailVerificationVerifyResponse
} from '../types/index';

import { apiRequest } from './api-commons'
import { API_BASE_URL } from '../config/index.js';


export const authApi = {
  async login(credentials: LoginRequest): Promise<{ token: string; user: User }> {
    return apiRequest('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  },

  async register(userData: RegisterRequest): Promise<{ token: string; user: User }> {
    return apiRequest('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  async logout(): Promise<void> {
    return apiRequest('/auth/logout/', {
      method: 'POST',
    });
  },

  async getCurrentUser(): Promise<User> {
    return apiRequest('/auth/profile/');
  },

  async getUserById(userId: number): Promise<User> {
    return apiRequest(`/auth/users/${userId}/`);
  },

  async updateProfile(userData: Partial<User>): Promise<User> {
    return apiRequest('/auth/profile/', {
      method: 'PATCH',
      body: JSON.stringify(userData),
    });
  },

  async uploadAvatar(avatarFile: File): Promise<{ message: string; avatar_url: string }> {
    const formData = new FormData();
    formData.append('avatar', avatarFile);

    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/auth/profile/avatar/`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Token ${token}` }),
      },
      body: formData,
    });

    return handleResponse<{ message: string; avatar_url: string }>(response);
  },

  async changePasswordSimple(passwordData: SimplePasswordChangeRequest): Promise<{ message: string }> {
    return apiRequest('/auth/password/change-simple/', {
      method: 'POST',
      body: JSON.stringify(passwordData),
    });
  },

  // Email Verification API
  async sendEmailVerification(data: EmailVerificationSendRequest): Promise<EmailVerificationSendResponse> {
    return apiRequest('/auth/email/send-verification/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async verifyEmail(data: EmailVerificationVerifyRequest): Promise<EmailVerificationVerifyResponse> {
    return apiRequest('/auth/email/verify/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

export const postsApi = {
  async getPosts(params?: {
    type?: string;
    search?: string;
    user?: number;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Post>> {
    const query = new URLSearchParams();
    if (params?.type) query.append('type', params.type);
    if (params?.search) query.append('search', params.search);
    if (params?.user) query.append('user', params.user.toString());
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const queryString = query.toString();
    return apiRequest(`/posts/${queryString ? `?${queryString}` : ''}`);
  },

  async createPost(postData: {
    content: string;
    post_type: 'normal' | 'checkin';
    images?: File[];
  }): Promise<Post> {
    const formData = new FormData();
    formData.append('content', postData.content);
    formData.append('post_type', postData.post_type);

    if (postData.images) {
      postData.images.forEach((image) => {
        formData.append('images', image);
      });
    }

    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/posts/`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Token ${token}` }),
      },
      body: formData,
    });

    return handleResponse<Post>(response);
  },

  async likePost(postId: string): Promise<{ message: string; likes_count: number }> {
    return apiRequest(`/posts/${postId}/like/`, {
      method: 'POST',
    });
  },

  async unlikePost(postId: string): Promise<{ message: string; likes_count: number }> {
    return apiRequest(`/posts/${postId}/like/`, {
      method: 'DELETE',
    });
  },

  async deletePost(postId: string): Promise<{ message: string }> {
    return apiRequest(`/posts/${postId}/delete/`, {
      method: 'DELETE',
    });
  },

  async getPost(postId: string): Promise<Post> {
    return apiRequest(`/posts/${postId}/`);
  },

  async createComment(postId: string, commentData: {
    content: string;
    parent?: string;
    images?: File[];
  }): Promise<Comment> {
    const formData = new FormData();
    formData.append('content', commentData.content);

    if (commentData.parent) {
      formData.append('parent', commentData.parent);
    }

    if (commentData.images) {
      commentData.images.forEach((image) => {
        formData.append('images', image);
      });
    }

    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/posts/${postId}/comments/`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Token ${token}` }),
      },
      body: formData,
    });

    return handleResponse<Comment>(response);
  },

  async likeComment(commentId: string): Promise<{ message: string; likes_count: number }> {
    return apiRequest(`/posts/comments/${commentId}/like/`, {
      method: 'POST',
    });
  },

  async unlikeComment(commentId: string): Promise<{ message: string; likes_count: number }> {
    return apiRequest(`/posts/comments/${commentId}/like/`, {
      method: 'DELETE',
    });
  },

  async getPostComments(postId: string, params?: {
    page?: number;
    page_size?: number;
  }): Promise<{
    comments: Comment[];
    pagination: {
      page: number;
      page_size: number;
      total_pages: number;
      total_count: number;
      has_next: boolean;
      has_previous: boolean;
    };
  }> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const queryString = query.toString();
    return apiRequest(`/posts/${postId}/comments/list/${queryString ? `?${queryString}` : ''}`);
  },

  async getCommentReplies(commentId: string, params?: {
    page?: number;
    page_size?: number;
  }): Promise<{
    replies: Comment[];
    root_comment_id: string;
    pagination: {
      page: number;
      page_size: number;
      total_pages: number;
      total_count: number;
      has_next: boolean;
      has_previous: boolean;
    };
  }> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const queryString = query.toString();
    return apiRequest(`/posts/comments/${commentId}/replies/${queryString ? `?${queryString}` : ''}`);
  },

  async getStats(): Promise<{
    total_posts: number;
    posts_today: number;
    total_likes: number;
    total_comments: number;
    checkin_posts: number;
    verified_checkins: number;
  }> {
    return apiRequest('/posts/stats/');
  },

  async voteOnCheckinPost(postId: string, voteType: 'pass' | 'reject'): Promise<{
    message: string;
    vote_id: string;
    remaining_coins: number;
    total_coins_collected: number;
  }> {
    return apiRequest(`/posts/${postId}/vote/`, {
      method: 'POST',
      body: JSON.stringify({ vote_type: voteType }),
    });
  },
};

export const storeApi = {
  // Store items
  async getStoreItems(): Promise<StoreItem[]> {
    const response = await apiRequest<PaginatedResponse<StoreItem>>('/store/items/');
    return response.results || [];
  },

  // User inventory
  async getUserInventory(): Promise<UserInventory> {
    return apiRequest('/store/inventory/');
  },

  // Purchase item
  async purchaseItem(storeItemId: string, quantity: number = 1): Promise<{
    message: string;
    items: { id: string; type: string }[];
    remaining_coins: number;
    remaining_slots: number;
  }> {
    return apiRequest('/store/purchase/', {
      method: 'POST',
      body: JSON.stringify({ store_item_id: storeItemId, quantity }),
    });
  },

  // Photo upload
  async uploadPhotoToPaper(paperItemId: string, photo: File): Promise<{
    message: string;
    photo_item_id: string;
  }> {
    const formData = new FormData();
    formData.append('paper_item_id', paperItemId);
    formData.append('photo', photo);

    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/store/upload-photo/`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Token ${token}` }),
      },
      body: formData,
    });

    return handleResponse<{ message: string; photo_item_id: string }>(response);
  },

  // View photo
  async viewPhoto(photoId: string): Promise<Blob> {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/store/photo/${photoId}/`, {
      method: 'GET',
      headers: {
        ...(token && { Authorization: `Token ${token}` }),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.blob();
  },

  // Games
  async getGames(): Promise<Game[]> {
    return apiRequest('/store/games/');
  },

  async createGame(gameData: {
    game_type: 'time_wheel' | 'rock_paper_scissors' | 'exploration' | 'dice';
    bet_amount: number;
    max_players?: number;
    item_reward_id?: string; // For dice games - optional item reward from creator's inventory
  }): Promise<Game> {
    return apiRequest('/store/games/', {
      method: 'POST',
      body: JSON.stringify(gameData),
    });
  },

  async joinGame(gameId: string, action: Record<string, any> = {}): Promise<{
    message: string;
    participants?: number;
    max_participants?: number;
    winner?: string;
    loser?: string;
    results?: any[];
    // Dice game specific fields
    dice_result?: number;
    guess?: string;
    is_correct?: boolean;
    item_received?: any;
    creator_coins_change?: number;
    remaining_coins?: number;
  }> {
    return apiRequest(`/store/games/${gameId}/join/`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    });
  },

  // Time wheel game - New implementation with frontend calculation
  async playTimeWheel(data: {
    task_id: string;
    bet_amount: number;
    is_increase: boolean;
    time_change_minutes: number;
    base_time: number;
  }): Promise<{
    success: boolean;
    result: 'increase' | 'decrease';
    time_change_minutes: number;
    new_end_time: string | null;
    message: string;
    remaining_coins: number;
  }> {
    return apiRequest('/store/time-wheel/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async cancelGame(gameId: string): Promise<{
    message: string;
    refunded_amount: number;
    remaining_coins: number;
  }> {
    return apiRequest(`/store/games/${gameId}/cancel/`, {
      method: 'DELETE',
    });
  },

  // Drift bottles
  async createDriftBottle(data: {
    message: string;
    item_ids?: string[];
  }): Promise<{
    message: string;
    drift_bottle_id: string;
    expires_at: string;
  }> {
    return apiRequest('/store/drift-bottles/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Exploration
  async getAvailableZones(): Promise<{ zones: ExplorationZone[] }> {
    return apiRequest('/store/zones/');
  },

  async exploreZone(zoneName: string, cardPosition: number): Promise<{
    message: string;
    zone: string;
    difficulty: string;
    card_count: number;
    cards: {
      position: number;
      has_treasure: boolean;
      treasure_id?: string;
      location_hint?: string;
      difficulty?: string;
      item_type?: string;
      burier?: string;
      is_found?: boolean;
    }[];
    selected_position: number;
    found_item?: {
      id: string;
      type: string;
      properties: Record<string, any>;
    };
    treasure_count: number;
    cost: number;
    success: boolean;
  }> {
    return apiRequest('/store/explore-zone/', {
      method: 'POST',
      body: JSON.stringify({ zone_name: zoneName, card_position: cardPosition }),
    });
  },

  async findTreasure(treasureId: string): Promise<{
    message: string;
    item: {
      id: string;
      type: string;
      properties: Record<string, any>;
    };
    reward_to_burier: number;
    remaining_slots: number;
  }> {
    return apiRequest('/store/find-treasure/', {
      method: 'POST',
      body: JSON.stringify({ treasure_id: treasureId }),
    });
  },

  async buryItem(data: {
    item_id: string;
    location_zone: string;
    location_hint: string;
  }): Promise<{
    message: string;
    treasure_id: string;
    location_zone: string;
    difficulty: string;
    expires_at: string;
  }> {
    return apiRequest('/store/bury-item/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Get buried treasures
  async getBuriedTreasures(status?: string): Promise<BuriedTreasure[]> {
    const query = status ? `?status=${status}` : '';
    const response = await apiRequest<PaginatedResponse<BuriedTreasure>>(`/store/treasures/${query}`);
    return response.results || [];
  },

  // Discard item
  async discardItem(itemId: string): Promise<{
    message: string;
  }> {
    return apiRequest(`/store/discard-item/`, {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  // Share item
  async createShareLink(itemId: string): Promise<{
    message: string;
    share_url: string;
    share_id: string;
    expires_at: string;
  }> {
    return apiRequest('/store/share-item/', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  // Return item to original owner
  async returnItem(itemId: string): Promise<{
    message: string;
    item_id: string;
    original_owner: string;
  }> {
    return apiRequest(`/store/return-item/`, {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  // Claim shared item
  async claimSharedItem(shareToken: string): Promise<{
    message: string;
    item: {
      id: string;
      type: string;
      properties: Record<string, any>;
    };
    sharer: string;
    remaining_slots: number;
  }> {
    return apiRequest(`/store/claim/${shareToken}/`, {
      method: 'POST',
    });
  },

  // Universal Key
  async useUniversalKey(data: {
    task_id: string;
    universal_key_id: string;
  }): Promise<{
    message: string;
    task_id: string;
    task_title: string;
    previous_status: string;
    new_status: string;
    reward_coins: number;
    remaining_coins: number;
    completion_time: string;
  }> {
    return apiRequest('/store/use-universal-key/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Check task key ownership
  async checkTaskKeyOwnership(taskIds: string[]): Promise<{
    results: Array<{
      task_id: string;
      has_original_key: boolean;
      key_holder?: string;
      error?: string;
    }>;
  }> {
    return apiRequest('/store/check-task-key-ownership/', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds }),
    });
  },

  // Get task key holder
  async getTaskKeyHolder(taskId: string): Promise<{
    task_id: string;
    has_key: boolean;
    key_holder?: {
      id: number;
      username: string;
      is_current_user: boolean;
    };
    original_owner?: {
      id: number;
      username: string;
    };
    message?: string;
  }> {
    return apiRequest(`/store/task-key-holder/${taskId}/`);
  },

  // Treasury operations
  async depositTreasuryCoins(itemId: string, amount: number): Promise<{
    success: boolean;
    message: string;
    stored_coins: number;
    user_remaining_coins: number;
  }> {
    return apiRequest(`/store/treasury/${itemId}/deposit/`, {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  },

  async withdrawTreasuryCoins(itemId: string): Promise<{
    success: boolean;
    message: string;
    withdrawn_coins: number;
    user_total_coins: number;
    depositor_info?: {
      username: string;
      deposit_time: string;
    };
  }> {
    return apiRequest(`/store/treasury/${itemId}/withdraw/`, {
      method: 'POST',
    });
  },

  // Note management
  async viewNote(noteId: string): Promise<{
    content: string;
    created_at?: string;
    editor?: string;
    burn_after_reading: boolean;
    view_time: string;
  }> {
    return apiRequest(`/store/note/${noteId}/view/`, {
      method: 'GET',
    });
  },

  async editNote(noteId: string, content: string): Promise<{
    success: boolean;
    message: string;
    content: string;
    edited_at: string;
  }> {
    return apiRequest(`/store/note/${noteId}/edit/`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  // Lucky Charm
  async useLuckyCharm(itemId: string): Promise<{
    success: boolean;
    message: string;
    effect_description: string;
    boost_percentage: number;
  }> {
    return apiRequest('/store/use-lucky-charm/', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  // Energy Potion
  async useEnergyPotion(itemId: string): Promise<{
    success: boolean;
    message: string;
    effect_description: string;
    decay_reduction_percentage: number;
    duration_hours: number;
    expires_at: string;
  }> {
    return apiRequest('/store/use-energy-potion/', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },


  // Time Anchor
  async useTimeAnchor(data: {
    item_id: string;
    task_id: string;
    action: 'save' | 'restore';
    recreate_key?: boolean; // Request key recreation if it doesn't exist
  }): Promise<{
    success: boolean;
    message: string;
    task_title: string;
    saved_status?: string;
    saved_at?: string;
    can_restore?: boolean;
    old_status?: string;
    restored_status?: string;
    restored_end_time?: string;
    // Key return information for restore operations
    key_returned?: boolean;
    returned_key_id?: string;
    key_return_message?: string;
    key_recreated?: boolean; // Indicates if key was recreated
    // Timeline event information
    timeline_event_created?: boolean;
    timeline_event_id?: string;
  }> {
    return apiRequest('/store/use-time-anchor/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Exploration Compass
  async useExplorationCompass(data: {
    item_id: string;
    zone_name: string;
  }): Promise<{
    success: boolean;
    message: string;
    zone_name: string;
    zone_display_name: string;
    treasures: Array<{
      treasure_id: string;
      location_hint: string;
      difficulty: string;
      difficulty_display: string;
      item_type: string;
      item_display_name: string;
      item_icon: string;
      burier: {
        username: string;
        id: number;
      };
      buried_at: string;
      expires_at: string;
      exploration_hint: string;
    }>;
    treasure_count: number;
    compass_used_at: string;
  }> {
    return apiRequest('/store/use-exploration-compass/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },


  // Influence Crown
  async useInfluenceCrown(itemId: string): Promise<{
    success: boolean;
    message: string;
    effect_description: string;
    vote_multiplier: number;
    duration_hours: number;
    expires_at: string;
    activated_at: string;
  }> {
    return apiRequest('/store/use-influence-crown/', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },
};

// Tasks API
export const tasksApi = {
  async getTasks(params?: {
    task_type?: string;
    status?: string;
    my_tasks?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<any>> {
    const query = new URLSearchParams();
    if (params?.task_type) query.append('task_type', params.task_type);
    if (params?.status) query.append('status', params.status);
    if (params?.my_tasks) query.append('my_tasks', params.my_tasks.toString());
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const queryString = query.toString();
    return apiRequest(`/tasks/${queryString ? `?${queryString}` : ''}`);
  },

  async getTasksList(params?: {
    task_type?: string;
    status?: string;
    my_tasks?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<any[]> {
    const response = await this.getTasks(params);
    return response.results || [];
  },

  async getTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/`);
  },

  async getActiveLockTask(): Promise<any | null> {
    console.log('getActiveLockTask called')

    // Get current user to filter tasks
    let currentUser;
    try {
      currentUser = await authApi.getCurrentUser();
      console.log('Current user:', currentUser);
    } catch (error) {
      console.error('Failed to get current user:', error);
      return null;
    }

    const tasks = await tasksApi.getTasksList();
    console.log('All tasks:', tasks);

    // Filter for tasks belonging to current user AND active lock tasks
    const activeLockTask = tasks.find(task =>
      task.task_type === 'lock' &&
      task.status === 'active' &&
      task.user.id === currentUser.id
    ) || null;

    console.log('Found active lock task for current user:', activeLockTask);
    return activeLockTask;
  },

  async startTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/start/`, {
      method: 'POST'
    });
  },

  async completeTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/complete/`, {
      method: 'POST'
    });
  },

  async stopTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/stop/`, {
      method: 'POST'
    });
  },

  async addOvertime(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/overtime/`, {
      method: 'POST'
    });
  },

  async deleteTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/`, {
      method: 'DELETE'
    });
  },

  async takeTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/take/`, {
      method: 'POST'
    });
  },

  async submitTask(taskId: string, completionProof: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/submit/`, {
      method: 'POST',
      body: JSON.stringify({ completion_proof: completionProof })
    });
  },

  async approveTask(taskId: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/approve/`, {
      method: 'POST'
    });
  },

  async rejectTask(taskId: string, rejectReason?: string): Promise<any> {
    return apiRequest(`/tasks/${taskId}/reject/`, {
      method: 'POST',
      body: JSON.stringify({ reject_reason: rejectReason || '' })
    });
  },

  async voteTask(taskId: string, agree: boolean): Promise<any> {
    return apiRequest(`/tasks/${taskId}/vote/`, {
      method: 'POST',
      body: JSON.stringify({ agree })
    });
  },

  async checkAndCompleteExpiredTasks(): Promise<{
    message: string;
    completed_tasks: Array<{
      id: string;
      title: string;
      completed_at: string;
    }>;
  }> {
    return apiRequest('/tasks/check-expired/', {
      method: 'POST'
    });
  },

  async processHourlyRewards(): Promise<{
    message: string;
    rewards: Array<{
      task_id: string;
      task_title: string;
      user: string;
      hour_count: number;
      reward_amount: number;
    }>;
  }> {
    return apiRequest('/tasks/process-hourly-rewards/', {
      method: 'POST'
    });
  },

  async getTaskTimeline(taskId: string): Promise<{
    task_id: string;
    task_title: string;
    timeline_events: Array<{
      id: string;
      event_type: string;
      event_type_display: string;
      user: any;
      time_change_minutes: number | null;
      previous_end_time: string | null;
      new_end_time: string | null;
      description: string;
      metadata: any;
      created_at: string;
    }>;
  }> {
    return apiRequest(`/tasks/${taskId}/timeline/`);
  }
};

// Notifications API
export const notificationsApi = {
  async getNotifications(params?: {
    is_read?: string;
    type?: string;
    limit?: number;
    page?: number;
  }): Promise<PaginatedResponse<NotificationItem>> {
    const query = new URLSearchParams();
    if (params?.is_read !== undefined) query.append('is_read', params.is_read);
    if (params?.type) query.append('type', params.type);
    if (params?.limit) query.append('page_size', params.limit.toString());
    if (params?.page) query.append('page', params.page.toString());

    const queryString = query.toString();
    return apiRequest<PaginatedResponse<NotificationItem>>(`/auth/notifications/${queryString ? `?${queryString}` : ''}`);
  },

  // 保持向后兼容的简化方法
  async getNotificationsList(params?: {
    is_read?: string;
    type?: string;
    limit?: number;
    page?: number;
  }): Promise<NotificationItem[]> {
    const response = await this.getNotifications(params);
    return response.results || [];
  },

  async getNotificationStats(): Promise<{
    total_notifications: number;
    unread_notifications: number;
    unread_by_type: Record<string, { display_name: string; count: number }>;
    unread_by_priority: Record<string, { display_name: string; count: number }>;
  }> {
    return apiRequest('/auth/notifications/stats/');
  },

  async markAsRead(notificationId: string): Promise<{
    message: string;
    notification: NotificationItem;
  }> {
    return apiRequest(`/auth/notifications/${notificationId}/read/`, {
      method: 'POST'
    });
  },

  async markAllAsRead(): Promise<{
    message: string;
    marked_count: number;
  }> {
    return apiRequest('/auth/notifications/mark-all-read/', {
      method: 'POST'
    });
  },

  async deleteNotification(notificationId: string): Promise<{
    message: string;
  }> {
    return apiRequest(`/auth/notifications/${notificationId}/delete/`, {
      method: 'DELETE'
    });
  },

  async clearReadNotifications(): Promise<{
    message: string;
    cleared_count: number;
  }> {
    return apiRequest('/auth/notifications/clear-read/', {
      method: 'DELETE'
    });
  },

  async createNotification(data: {
    recipient_id: number;
    notification_type: string;
    title?: string;
    message?: string;
    priority?: string;
    related_object_type?: string;
    related_object_id?: string;
    extra_data?: Record<string, any>;
  }): Promise<{
    message: string;
    notification: NotificationItem;
  }> {
    return apiRequest('/auth/notifications/create/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
};

export { ApiError };
