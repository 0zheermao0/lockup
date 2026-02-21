import { apiRequest, ApiError } from './api-commons'
import { API_BASE_URL } from '../config/index';

export interface TelegramBindRequest {
  telegram_user_id: number;
  telegram_username?: string;
  telegram_chat_id?: number;
}

export interface TelegramStatus {
  is_bound: boolean;
  telegram_username?: string;
  bound_at?: string;
  notifications_enabled: boolean;
  can_receive_notifications: boolean;
  show_telegram_account?: boolean;
}

export interface TelegramGameResult {
  user_choice: string;
  user_choice_emoji: string;
  user_choice_name: string;
  bot_choice: string;
  bot_choice_emoji: string;
  bot_choice_name: string;
  result: 'user' | 'bot' | 'tie';
  message: string;
}

export interface TelegramTimeWheelResult {
  spin_id: string;
  selected_time: number;
  message: string;
  emoji: string;
}

export interface TelegramUser {
  id: number;
  username: string;
  level: number;
  active_tasks: Array<{
    id: string;
    title: string;
    difficulty: string;
    start_time: string;
    end_time: string;
  }>;
}

export interface TelegramOvertimeResult {
  message: string;
  task_title: string;
  minutes_added: number;
  new_end_time: string;
}

export interface TelegramTaskShareData {
  message_text: string;
  telegram_share_url: string;
  task_id: string;
  task_title: string;
  callback_data: string;
}

export interface TelegramTaskShareResult {
  message: string;
  share_data: TelegramTaskShareData;
}

export interface TelegramGameShareData {
  message_text: string;
  telegram_share_url: string;
  game_id: string;
  game_type: string;
  keyboard: any;
}

export interface TelegramGameShareResult {
  message: string;
  share_data: TelegramGameShareData;
}

export const telegramApi = {
  /**
   * 启动 Telegram 绑定流程 - 为自动绑定做准备
   */
  async initiateTelegramBinding(): Promise<{
    message: string;
    bot_url: string;
    binding_token: string;
    next_step: string;
  }> {
    return apiRequest('/telegram/initiate-binding/', {
      method: 'POST',
    });
  },

  /**
   * 绑定 Telegram 账户
   */
  async bindTelegram(bindData: TelegramBindRequest): Promise<{
    message: string;
    telegram_username?: string;
    bound_at: string;
  }> {
    return apiRequest('/telegram/bind/', {
      method: 'POST',
      body: JSON.stringify(bindData),
    });
  },

  /**
   * 解绑 Telegram 账户
   */
  async unbindTelegram(): Promise<{ message: string }> {
    return apiRequest('/telegram/unbind/', {
      method: 'POST',
    });
  },

  /**
   * 获取 Telegram 绑定状态
   */
  async getTelegramStatus(): Promise<TelegramStatus> {
    return apiRequest('/telegram/status/');
  },

  /**
   * 切换 Telegram 通知开关
   */
  async toggleTelegramNotifications(): Promise<{
    message: string;
    notifications_enabled: boolean;
  }> {
    return apiRequest('/telegram/toggle-notifications/', {
      method: 'POST',
    });
  },

  /**
   * 通过 Telegram 给任务加时
   */
  async addOvertimeViaTelegram(taskId: string, minutes?: number): Promise<TelegramOvertimeResult> {
    return apiRequest('/telegram/add-overtime/', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
        ...(minutes && { minutes }),
      }),
    });
  },

  /**
   * Telegram 猜拳游戏
   */
  async playRockPaperScissors(choice: 'rock' | 'paper' | 'scissors'): Promise<TelegramGameResult> {
    return apiRequest('/telegram/rock-paper-scissors/', {
      method: 'POST',
      body: JSON.stringify({ choice }),
    });
  },

  /**
   * Telegram 时间转盘游戏
   */
  async playTimeWheel(): Promise<TelegramTimeWheelResult> {
    return apiRequest('/telegram/time-wheel/', {
      method: 'POST',
    });
  },

  /**
   * 搜索用户以便给他们的任务加时
   */
  async searchUsersForOvertime(query: string): Promise<{ users: TelegramUser[] }> {
    const params = new URLSearchParams({ q: query });
    return apiRequest(`/telegram/search-users/?${params}`);
  },

  /**
   * 测试 Telegram 通知发送（开发用）
   */
  async testTelegramNotification(userId: number, title?: string, message?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return apiRequest('/telegram/test-notification/', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        ...(title && { title }),
        ...(message && { message }),
      }),
    });
  },

  /**
   * 生成 Telegram Bot 深度链接
   */
  generateDeepLink(userId: number): string {
    const botUsername = 'lock_up_bot'; // 与后端配置保持一致
    const bindToken = `bind_${userId}_${Date.now()}`;
    return `https://t.me/${botUsername}?start=${bindToken}`;
  },

  /**
   * 生成 One-Click 绑定链接
   */
  generateBindingLink(telegramUserId: number): string {
    const currentUrl = window.location.origin;
    return `${currentUrl}/profile?telegram_bind=${telegramUserId}`;
  },

  /**
   * 处理深度链接绑定
   */
  async handleDeepLinkBinding(telegramUserId: number, telegramUsername?: string): Promise<{
    message: string;
    telegram_username?: string;
    bound_at: string;
  }> {
    return this.bindTelegram({
      telegram_user_id: telegramUserId,
      telegram_username: telegramUsername,
    });
  },

  /**
   * 生成任务分享到Telegram的内容
   */
  async shareTaskToTelegram(taskId: string): Promise<TelegramTaskShareResult> {
    return apiRequest('/telegram/share-task/', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
      }),
    });
  },

  /**
   * 直接打开Telegram分享任务（使用 deeplink 方式）
   * 通过 via bot 方式分享，支持 inline 按钮
   */
  async shareTaskDirectly(taskId: string): Promise<{ deeplink_url: string }> {
    try {
      const shareResult = await this.shareTaskToTelegram(taskId);

      // 返回 deeplink URL，让调用者决定如何打开
      // deeplink 格式: https://t.me/{bot_username}?start=share_{task_id}
      return {
        deeplink_url: shareResult.share_data.deeplink_url || shareResult.share_data.telegram_share_url
      };
    } catch (error) {
      console.error('Error sharing task to Telegram:', error);
      throw error;
    }
  },

  /**
   * 生成游戏分享到Telegram的内容
   */
  async shareGameToTelegram(gameId: string): Promise<TelegramGameShareResult> {
    return apiRequest('/telegram/share-game/', {
      method: 'POST',
      body: JSON.stringify({
        game_id: gameId,
      }),
    });
  },

  /**
   * 直接分享游戏到Telegram
   */
  async shareGameDirectly(gameId: string): Promise<void> {
    try {
      const shareResult = await this.shareGameToTelegram(gameId);

      // 直接打开Telegram分享链接
      window.open(shareResult.share_data.telegram_share_url, '_blank');
    } catch (error) {
      console.error('Error sharing game to Telegram:', error);
      throw error;
    }
  }
};

export { ApiError };