<template>
  <div class="inventory-view">
    <!-- Header -->
    <header class="inventory-header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">
          ← 返回
        </button>
        <h1 class="inventory-title">🎒 物品背包</h1>
        <div class="header-stats">
          <div class="capacity-display">
            <span class="capacity-text">容量</span>
            <span class="capacity-amount">{{ inventory?.used_slots || 0 }}/{{ inventory?.max_slots || 6 }}</span>
          </div>
          <router-link to="/store" class="store-btn">
            🛍️ 返回商店
          </router-link>
        </div>
      </div>
    </header>

    <div class="container">

      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <div class="loading-box">
          <div class="loading-spinner"></div>
          <p class="loading-text">加载背包中...</p>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <div class="error-box">
          <h3 class="error-title">❌ 加载失败</h3>
          <p class="error-message">{{ error }}</p>
          <button @click="loadInventory" class="retry-btn">🔄 重试</button>
        </div>
      </div>

      <!-- Inventory grid -->
      <div v-else class="inventory-content">
        <div class="inventory-section">
          <h2 class="section-title">物品栏位</h2>

          <!-- Items grid -->
          <div class="inventory-grid">
            <!-- Occupied slots -->
            <div
              v-for="item in inventory?.items || []"
              :key="item.id"
              class="inventory-slot occupied"
              @click="selectItem(item)"
              :class="{ 'selected': selectedItem?.id === item.id }"
            >
              <div class="slot-content">
                <span class="item-icon">{{ item.item_type.icon }}</span>
                <span class="item-name">{{ item.item_type.display_name }}</span>
                <span class="item-status">{{ getStatusText(item.status) }}</span>
              </div>
            </div>

            <!-- Empty slots -->
            <div
              v-for="n in (inventory?.available_slots || 0)"
              :key="`empty-${n}`"
              class="inventory-slot empty"
            >
              <div class="slot-content">
                <span class="empty-text">空槽</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Item details panel -->
        <div v-if="selectedItem" class="item-details-panel">
          <div class="panel-header">
            <div class="item-info">
              <h3 class="item-title">
                <span class="item-title-icon">{{ selectedItem.item_type.icon }}</span>
                <span class="item-title-text">{{ selectedItem.item_type.display_name }}</span>
              </h3>
              <p class="item-description">{{ selectedItem.item_type.description }}</p>
              <div class="item-meta">
                <p class="meta-item">
                  <span class="meta-label">状态:</span>
                  <span class="meta-value">{{ getStatusText(selectedItem.status) }}</span>
                </p>
                <p class="meta-item">
                  <span class="meta-label">创建时间:</span>
                  <span class="meta-value">{{ formatDate(selectedItem.created_at) }}</span>
                </p>
                <!-- 显示原始所有者（对于钥匙物品始终显示） -->
                <p v-if="selectedItem.original_creator || selectedItem.original_owner || selectedItem.item_type.name === 'key'" class="meta-item">
                  <span class="meta-label">原始所有者:</span>
                  <button @click="viewOwnerProfile(selectedItem.original_owner || selectedItem.original_creator)" class="owner-link" v-if="selectedItem.original_owner || selectedItem.original_creator">
                    {{ (selectedItem.original_owner || selectedItem.original_creator)?.username }}
                  </button>
                  <span v-else class="no-owner">未知</span>
                </p>

                <!-- 显示当前持有者（如果不同于原始所有者） -->
                <p v-if="selectedItem.owner && (selectedItem.original_owner || selectedItem.original_creator) && selectedItem.owner.id !== (selectedItem.original_owner || selectedItem.original_creator)?.id" class="meta-item">
                  <span class="meta-label">当前持有者:</span>
                  <button @click="viewOwnerProfile(selectedItem.owner)" class="owner-link">
                    {{ selectedItem.owner.username }}
                  </button>
                </p>
              </div>
            </div>
            <button @click="selectedItem = null" class="close-btn">
              ✕
            </button>
          </div>

          <!-- Item properties (only show for items other than keys, photos, treasury, and notes) -->
          <div v-if="Object.keys(selectedItem.properties).length > 0 && !['key', 'photo', 'little_treasury', 'note'].includes(selectedItem.item_type.name)" class="properties-section">
            <h4 class="properties-title">物品属性</h4>
            <div class="properties-content">
              <pre class="properties-json">{{ JSON.stringify(selectedItem.properties, null, 2) }}</pre>
            </div>
          </div>

          <!-- Item actions -->
          <div class="action-buttons">
            <!-- Photo paper upload -->
            <div v-if="selectedItem.item_type.name === 'photo_paper' && selectedItem.status === 'available'">
              <input
                type="file"
                ref="photoInput"
                accept="image/*"
                @change="handlePhotoUpload"
                class="hidden"
              >
              <button @click="triggerPhotoInput" class="action-btn primary">
                📸 上传照片
              </button>
            </div>

            <!-- Photo view -->
            <button
              v-if="selectedItem.item_type.name === 'photo' && selectedItem.status === 'available'"
              @click="viewPhoto(selectedItem)"
              class="action-btn primary"
            >
              👁️ 查看照片
            </button>

            <!-- Note edit -->
            <button
              v-if="selectedItem.item_type.name === 'note' && selectedItem.status === 'available' && (!selectedItem.properties?.content || selectedItem.properties.content.trim() === '')"
              @click="openNoteEditModal"
              class="action-btn primary"
            >
              ✏️ 编写纸条
            </button>

            <!-- Note edit (existing content) -->
            <button
              v-if="selectedItem.item_type.name === 'note' && selectedItem.status === 'available' && selectedItem.properties?.content && selectedItem.properties.content.trim() !== ''"
              @click="openNoteEditModal"
              class="action-btn secondary"
            >
              ✏️ 编辑纸条
            </button>

            <!-- Note view -->
            <button
              v-if="selectedItem.item_type.name === 'note' && selectedItem.status === 'available' && selectedItem.properties?.content && selectedItem.properties.content.trim() !== ''"
              @click="openNoteViewModal(); viewNote()"
              class="action-btn primary"
            >
              👁️ 查看纸条
            </button>

            <!-- Share item -->
            <button
              v-if="canShareItem(selectedItem)"
              @click="shareItem"
              class="action-btn secondary"
              :disabled="sharingItem"
            >
              <span v-if="sharingItem">分享中...</span>
              <span v-else>🔗 分享物品</span>
            </button>

            <!-- Bury item -->
            <button
              v-if="canBuryItem(selectedItem)"
              @click="showBuryModal = true"
              class="action-btn secondary"
            >
              ⛏️ 掩埋物品
            </button>

            <!-- Universal Key usage -->
            <button
              v-if="canUseUniversalKey(selectedItem)"
              @click="openUniversalKeyModal"
              class="action-btn universal-key"
              :disabled="usingUniversalKey"
            >
              <span v-if="usingUniversalKey">使用中...</span>
              <span v-else>🗝️ 使用万能钥匙</span>
            </button>

            <!-- Treasury Item usage -->
            <button
              v-if="canUseTreasury(selectedItem)"
              @click="openTreasuryModal"
              class="action-btn primary"
            >
              💰 管理小金库
            </button>

            <!-- Detection Radar usage -->
            <button
              v-if="canUseDetectionRadar(selectedItem)"
              @click="openDetectionRadarModal"
              class="action-btn radar"
              :disabled="usingDetectionRadar"
            >
              <span v-if="usingDetectionRadar">探测中...</span>
              <span v-else>🎯 使用探测雷达</span>
            </button>

            <!-- Blizzard Bottle usage -->
            <button
              v-if="canUseBlizzardBottle(selectedItem)"
              @click="openBlizzardBottleModal"
              class="action-btn blizzard"
              :disabled="usingBlizzardBottle"
            >
              <span v-if="usingBlizzardBottle">释放中...</span>
              <span v-else>🌨️ 使用暴雪瓶</span>
            </button>

            <!-- Sun Bottle usage -->
            <button
              v-if="canUseSunBottle(selectedItem)"
              @click="openSunBottleModal"
              class="action-btn sun"
              :disabled="usingSunBottle"
            >
              <span v-if="usingSunBottle">使用中...</span>
              <span v-else>☀️ 使用太阳瓶</span>
            </button>

            <!-- Discard item -->
            <button
              v-if="canDiscardItem(selectedItem)"
              @click="showDiscardModal = true"
              class="action-btn danger"
            >
              🗑️ 丢弃物品
            </button>
          </div>
        </div>

        <!-- Empty inventory message -->
        <div v-if="!inventory?.items || inventory.items.length === 0" class="empty-inventory">
          <div class="empty-box">
            <h3 class="empty-title">🎒 背包空空如也</h3>
            <p class="empty-message">快去商店购买一些物品吧！</p>
            <router-link to="/store" class="empty-action-btn">🛍️ 去商店看看</router-link>
          </div>
        </div>
      </div>

      <!-- Photo upload modal -->
      <div v-if="uploadingPhoto" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <h3 class="text-lg font-semibold mb-4">上传照片中...</h3>
          <div class="flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>

      <!-- Photo viewer modal -->
      <div v-if="viewingPhoto" class="photo-viewer-overlay" @click="closePhotoViewer">
        <div class="photo-viewer-content" @click.stop>
          <div class="photo-container">
            <img :src="photoUrl" class="photo-image" />
            <div class="photo-timer">
              <div class="timer-display">
                <span class="timer-icon">⏱️</span>
                <span class="timer-text">{{ photoTimeRemaining }}s</span>
              </div>
              <div class="timer-bar">
                <div
                  class="timer-progress"
                  :style="{ width: `${(photoTimeRemaining / 5) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
          <div class="photo-hint">
            <p class="hint-text">🔥 阅后即焚 - {{ photoTimeRemaining }}秒后自动销毁</p>
            <p class="hint-action">点击任意位置立即关闭</p>
          </div>
        </div>
      </div>

      <!-- Share success modal -->
      <div v-if="showShareModal" class="modal-overlay">
        <div class="share-modal">
          <div class="share-modal-header">
            <div class="share-success-badge">
              <span class="success-icon">🎉</span>
              <h3 class="share-modal-title">分享成功!</h3>
            </div>
            <button @click="closeShareModal" class="share-modal-close">×</button>
          </div>

          <div class="share-modal-body">
            <!-- Item preview card -->
            <div class="shared-item-preview">
              <div class="item-preview-icon">{{ sharedItem?.item_type?.icon }}</div>
              <div class="item-preview-details">
                <h4 class="item-preview-name">{{ sharedItem?.item_type?.display_name }}</h4>
                <p class="item-preview-description">已准备好分享给他人</p>
              </div>
            </div>

            <!-- Success message -->
            <div class="share-success-message">
              <h4 class="success-title">🔗 分享链接已生成</h4>
              <p class="success-description">
                任何人点击此链接都可以获取您的物品！
              </p>
              <div class="success-warning">
                <span class="warning-icon">⚠️</span>
                <span class="warning-text">注意：只有第一个点击的人能获得物品</span>
              </div>
              <!-- Expiration info -->
              <div v-if="shareExpiresAt" class="expiration-info">
                <div class="expiration-badge">
                  <span class="expiration-icon">⏰</span>
                  <span class="expiration-text">{{ formatExpireTime(shareExpiresAt) }}</span>
                </div>
                <p class="expiration-note">链接将在24小时后失效</p>
              </div>
            </div>

            <!-- Share link section -->
            <div class="share-link-section">
              <label class="share-link-label">分享链接</label>
              <div class="share-link-container">
                <div class="share-link-input-wrapper">
                  <input
                    ref="shareLinkInput"
                    v-model="shareLink"
                    readonly
                    class="share-link-input"
                    @click="selectShareLink"
                  >
                </div>
                <button
                  @click="copyShareLink"
                  class="share-copy-btn"
                  :class="{ 'copying': copyingLink, 'copied': linkCopied }"
                  :disabled="copyingLink"
                >
                  <span v-if="copyingLink">复制中...</span>
                  <span v-else-if="linkCopied">✅ 已复制!</span>
                  <span v-else>📋 复制链接</span>
                </button>
              </div>
            </div>
          </div>

          <div class="share-modal-footer">
            <button @click="closeShareModal" class="share-close-btn">完成</button>
          </div>
        </div>
      </div>

      <!-- Bury item modal -->
      <div v-if="showBuryModal" class="modal-overlay">
        <div class="action-modal">
          <div class="modal-header">
            <h3 class="modal-title">⛏️ 掩埋物品</h3>
            <button @click="closeBuryModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">掩埋区域</label>
              <select v-model="buryData.location_zone" class="form-select">
                <option value="">选择区域</option>
                <option value="forest">🌲 神秘森林</option>
                <option value="mountain">🏔️ 雾山</option>
                <option value="beach">🏖️ 月光海滩</option>
                <option value="desert">🏜️ 沙漠绿洲</option>
                <option value="cave">🕳️ 深邃洞穴</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">寻找提示</label>
              <input
                v-model="buryData.location_hint"
                placeholder="留下寻找提示..."
                class="form-input"
                maxlength="200"
              >
              <div class="char-counter">{{ buryData.location_hint.length }}/200</div>
            </div>


            <div v-if="selectedItem" class="item-info-section">
              <h4 class="info-title">📦 掩埋物品</h4>
              <div class="item-info-card">
                <span class="item-icon">{{ selectedItem.item_type.icon }}</span>
                <div class="item-details">
                  <span class="item-name">{{ selectedItem.item_type.display_name }}</span>
                  <span class="item-description">{{ selectedItem.item_type.description }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeBuryModal" class="modal-btn secondary">取消</button>
            <button
              @click="buryItem"
              class="modal-btn primary"
              :disabled="!buryData.location_zone || !buryData.location_hint.trim() || buryingItem"
            >
              <span v-if="buryingItem">掩埋中...</span>
              <span v-else>掩埋物品</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Discard item modal -->
      <div v-if="showDiscardModal" class="modal-overlay">
        <div class="action-modal">
          <div class="modal-header">
            <h3 class="modal-title">🗑️ 丢弃物品</h3>
            <button @click="closeDiscardModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">⚠️</div>
              <div class="warning-content">
                <h4 class="warning-title">确认丢弃</h4>
                <p class="warning-message">
                  你确定要丢弃 <strong>{{ selectedItem?.item_type.display_name }}</strong> 吗？
                </p>
                <p class="warning-note">
                  此操作不可撤销，物品将永久消失！
                </p>
              </div>
            </div>

            <div v-if="selectedItem?.properties && Object.keys(selectedItem.properties).length > 0" class="item-details">
              <h4 class="details-title">物品详情</h4>
              <div class="details-content">
                <pre class="details-json">{{ JSON.stringify(selectedItem.properties, null, 2) }}</pre>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeDiscardModal" class="modal-btn secondary">取消</button>
            <button @click="discardItem" class="modal-btn danger" :disabled="discardingItem">
              <span v-if="discardingItem">丢弃中...</span>
              <span v-else>确认丢弃</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Universal Key modal -->
      <div v-if="showUniversalKeyModal" class="modal-overlay" @click="closeUniversalKeyModal">
        <div class="action-modal" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">🗝️ 使用万能钥匙</h3>
            <button @click="closeUniversalKeyModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">⚠️</div>
              <div class="warning-content">
                <h4 class="warning-title">重要提醒</h4>
                <p class="warning-message">
                  万能钥匙可以直接完成任何状态的带锁任务，并获得正常的完成奖励。
                </p>
                <p class="warning-note">
                  使用后钥匙将被销毁，请谨慎选择！
                </p>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">选择要完成的任务</label>

              <div v-if="availableTasks.length === 0" class="no-tasks-message">
                <p>暂无可完成的带锁任务</p>
                <p class="hint">只能完成自己的活跃状态或投票状态的带锁任务</p>
              </div>

              <div v-else class="tasks-list">
                <div
                  v-for="task in availableTasks"
                  :key="task.id"
                  class="task-item"
                  :class="{ 'selected': selectedTaskId === task.id }"
                  @click="selectedTaskId = task.id"
                >
                  <div class="task-info">
                    <h4 class="task-title">{{ task.title }}</h4>
                    <p class="task-meta">
                      <span class="task-difficulty">{{ getDifficultyText(task.difficulty) }}</span>
                      <span class="task-status">{{ getStatusText(task.status) }}</span>
                    </p>
                    <p v-if="task.description" class="task-description">{{ stripHtmlAndTruncate(task.description, 120) }}</p>
                  </div>
                  <div class="task-rewards">
                    <!-- Reward points display removed as requested -->
                  </div>
                </div>
              </div>
            </div>

            <div v-if="selectedItem" class="item-info-section">
              <h4 class="info-title">🗝️ 使用物品</h4>
              <div class="item-info-card">
                <span class="item-icon">{{ selectedItem.item_type.icon }}</span>
                <div class="item-details">
                  <span class="item-name">{{ selectedItem.item_type.display_name }}</span>
                  <span class="item-description">{{ selectedItem.item_type.description }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeUniversalKeyModal" class="modal-btn secondary">取消</button>
            <button
              @click="useUniversalKey"
              class="modal-btn primary"
              :disabled="!selectedTaskId || usingUniversalKey"
            >
              <span v-if="usingUniversalKey">使用中...</span>
              <span v-else>使用万能钥匙</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Treasury Item modal -->
      <TreasuryItemModal
        :is-visible="showTreasuryModal"
        :treasury-item="selectedTreasuryItem"
        @close="closeTreasuryModal"
        @success="handleTreasurySuccess"
      />

      <!-- Detection Radar Modal -->
      <div v-if="showDetectionRadarModal" class="modal-overlay" @click.self="closeDetectionRadarModal">
        <div class="action-modal detection-radar-modal">
          <div class="modal-header">
            <h3 class="modal-title">🎯 使用探测雷达</h3>
            <button @click="closeDetectionRadarModal" class="modal-close">×</button>
          </div>

          <div v-if="!detectionResults" class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">🎯</div>
              <div class="warning-content">
                <h4 class="warning-title">探测雷达</h4>
                <p class="warning-message">
                  可以揭示您自己的带锁任务的隐藏时间信息。
                </p>
                <p class="warning-note">
                  ⚠️ 使用后物品将被自动销毁，请谨慎使用！
                </p>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeDetectionRadarModal" class="modal-btn secondary">
                取消
              </button>
              <button
                @click="useDetectionRadar"
                class="modal-btn primary"
                :disabled="usingDetectionRadar"
              >
                {{ usingDetectionRadar ? '探测中...' : '🎯 开始探测' }}
              </button>
            </div>
          </div>

          <div v-else class="modal-body">
            <div class="detection-results-section">
              <h4 class="info-title">📊 探测结果</h4>

              <div class="detection-results-grid">
                <div class="detection-result-card">
                  <div class="result-header">
                    <span class="result-icon">📝</span>
                    <span class="result-label">任务标题</span>
                  </div>
                  <div class="result-content">{{ detectionResults.task_title }}</div>
                </div>

                <div class="detection-result-card">
                  <div class="result-header">
                    <span class="result-icon">📊</span>
                    <span class="result-label">任务状态</span>
                  </div>
                  <div class="result-content">{{ detectionResults.status_text }}</div>
                </div>

                <div class="detection-result-card highlight">
                  <div class="result-header">
                    <span class="result-icon">⏰</span>
                    <span class="result-label">剩余时间</span>
                  </div>
                  <div class="result-content time-display">{{ formatTimeRemaining(detectionResults.time_remaining_ms) }}</div>
                </div>

                <div v-if="detectionResults.is_frozen" class="detection-result-card frozen">
                  <div class="result-header">
                    <span class="result-icon">❄️</span>
                    <span class="result-label">冻结状态</span>
                  </div>
                  <div class="result-content">任务已冻结</div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeDetectionRadarModal" class="modal-btn primary">
                确定
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Blizzard Bottle Modal -->
      <div v-if="showBlizzardBottleModal" class="modal-overlay" @click.self="closeBlizzardBottleModal">
        <div class="action-modal blizzard-bottle-modal">
          <div class="modal-header">
            <h3 class="modal-title">🌨️ 使用暴雪瓶</h3>
            <button @click="closeBlizzardBottleModal" class="modal-close">×</button>
          </div>

          <div v-if="!blizzardResults" class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">🌨️</div>
              <div class="warning-content">
                <h4 class="warning-title">暴雪瓶</h4>
                <p class="warning-message">
                  将冻结当前所有处于带锁状态的用户任务！这是一个全局效果，会影响所有正在进行的带锁任务。
                </p>
                <p class="warning-note">
                  ⚠️ 使用后物品将被自动销毁，此操作不可撤销！
                </p>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeBlizzardBottleModal" class="modal-btn secondary">
                取消
              </button>
              <button
                @click="useBlizzardBottle"
                class="modal-btn danger"
                :disabled="usingBlizzardBottle"
              >
                {{ usingBlizzardBottle ? '释放中...' : '🌨️ 释放暴雪' }}
              </button>
            </div>
          </div>

          <div v-else class="modal-body">
            <div class="blizzard-results-section">
              <h4 class="info-title">🌨️ 暴雪释放结果</h4>

              <div class="blizzard-results-grid">
                <div class="blizzard-result-card">
                  <div class="result-header">
                    <span class="result-icon">❄️</span>
                    <span class="result-label">冻结任务数</span>
                  </div>
                  <div class="result-content">{{ blizzardResults.frozen_tasks_count }}</div>
                </div>

                <div class="blizzard-result-card">
                  <div class="result-header">
                    <span class="result-icon">👥</span>
                    <span class="result-label">影响用户数</span>
                  </div>
                  <div class="result-content">{{ blizzardResults.affected_users_count }}</div>
                </div>

                <div v-if="blizzardResults.frozen_tasks && blizzardResults.frozen_tasks.length > 0" class="frozen-tasks-list">
                  <h5 class="tasks-title">被冻结的任务：</h5>
                  <div class="task-list">
                    <div
                      v-for="task in blizzardResults.frozen_tasks"
                      :key="task.task_id"
                      class="frozen-task-item"
                    >
                      <span class="task-title">{{ task.task_title }}</span>
                      <span class="task-owner">{{ task.owner }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeBlizzardBottleModal" class="modal-btn primary">
                确定
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Sun Bottle Modal -->
      <div v-if="showSunBottleModal" class="modal-overlay" @click.self="closeSunBottleModal">
        <div class="action-modal sun-bottle-modal">
          <div class="modal-header">
            <h3 class="modal-title">☀️ 使用太阳瓶</h3>
            <button @click="closeSunBottleModal" class="modal-close">×</button>
          </div>

          <div v-if="!sunBottleResults" class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">☀️</div>
              <div class="warning-content">
                <h4 class="warning-title">太阳瓶</h4>
                <p class="warning-message">
                  将解冻当前所有被冻结的带锁任务！这是一个全局效果，会恢复所有被冻结任务的倒计时。
                </p>
                <p class="warning-note">
                  ⚠️ 使用后物品将被自动销毁，此操作不可撤销！
                </p>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeSunBottleModal" class="modal-btn secondary">
                取消
              </button>
              <button
                @click="useSunBottle"
                class="modal-btn primary"
                :disabled="usingSunBottle"
              >
                {{ usingSunBottle ? '释放中...' : '☀️ 释放阳光' }}
              </button>
            </div>
          </div>

          <div v-else class="modal-body">
            <div class="sun-results-section">
              <h4 class="info-title">☀️ 太阳瓶使用结果</h4>

              <div class="sun-results-grid">
                <div class="sun-result-card">
                  <div class="result-header">
                    <span class="result-icon">🔥</span>
                    <span class="result-label">解冻任务数</span>
                  </div>
                  <div class="result-content">{{ sunBottleResults.unfrozen_tasks_count }}</div>
                </div>

                <div class="sun-result-card">
                  <div class="result-header">
                    <span class="result-icon">👥</span>
                    <span class="result-label">影响用户数</span>
                  </div>
                  <div class="result-content">{{ sunBottleResults.affected_users_count }}</div>
                </div>

                <div v-if="sunBottleResults.unfrozen_tasks && sunBottleResults.unfrozen_tasks.length > 0" class="unfrozen-tasks-list">
                  <h5 class="tasks-title">被解冻的任务：</h5>
                  <div class="task-list">
                    <div
                      v-for="task in sunBottleResults.unfrozen_tasks"
                      :key="task.task_id"
                      class="unfrozen-task-item"
                    >
                      <span class="task-title">{{ task.task_title }}</span>
                      <span class="task-owner">{{ task.owner }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeSunBottleModal" class="modal-btn primary">
                确定
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Note Edit Modal -->
      <div v-if="showNoteEditModal" class="modal-overlay" @click.self="closeNoteEditModal">
        <div class="action-modal note-edit-modal">
          <div class="modal-header">
            <h3 class="modal-title">✏️ 编辑纸条</h3>
            <button @click="closeNoteEditModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">纸条内容</label>
              <textarea
                v-model="noteContent"
                placeholder="请输入纸条内容（最多30个字符）..."
                class="form-textarea note-textarea"
                maxlength="30"
                rows="3"
              ></textarea>
              <div class="char-counter">{{ noteContent.length }}/30</div>
            </div>

            <div class="warning-section">
              <div class="warning-icon">⚠️</div>
              <div class="warning-content">
                <h4 class="warning-title">重要提醒</h4>
                <p class="warning-message">
                  纸条一旦被查看将自动销毁，请谨慎分享！
                </p>
                <p class="warning-note">
                  查看者有30秒阅读时间，阅读后纸条永久消失。
                </p>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeNoteEditModal" class="modal-btn secondary">
              取消
            </button>
            <button
              @click="saveNoteContent"
              class="modal-btn primary"
              :disabled="!noteContent.trim() || editingNote"
            >
              {{ editingNote ? '保存中...' : '保存纸条' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Note View Modal -->
      <div v-if="showNoteViewModal" class="note-viewer-overlay" @click="closeNoteViewModal">
        <div class="note-viewer-content" @click.stop>
          <div class="note-container">
            <div class="note-content">
              <div class="note-icon">📝</div>
              <div class="note-text">{{ noteContent }}</div>
            </div>
            <div class="note-timer">
              <div class="timer-display">
                <span class="timer-icon">⏱️</span>
                <span class="timer-text">{{ noteTimeRemaining }}s</span>
              </div>
              <div class="timer-bar">
                <div
                  class="timer-progress"
                  :style="{ width: `${(noteTimeRemaining / 30) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
          <div class="note-hint">
            <p class="hint-text">🔥 阅后即焚 - {{ noteTimeRemaining }}秒后自动销毁</p>
            <p class="hint-action">点击任意位置立即关闭</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeApi, tasksApi } from '../lib/api'
import { tasksApi as tasksApiDetailed } from '../lib/api-tasks'
import { smartGoBack } from '../utils/navigation'
import type { UserInventory, Item } from '../types'
import TreasuryItemModal from '../components/TreasuryItemModal.vue'

// Router
const router = useRouter()

// Reactive data
const inventory = ref<UserInventory | null>(null)
const selectedItem = ref<Item | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Photo related
const uploadingPhoto = ref(false)
const viewingPhoto = ref(false)
const photoUrl = ref('')
const photoAutoCloseTimer = ref<number | null>(null)
const photoTimeRemaining = ref(5)
const photoInput = ref<HTMLInputElement>()

// Share item
const showShareModal = ref(false)
const shareLink = ref('')
const shareExpiresAt = ref('')
const sharingItem = ref(false)
const copyingLink = ref(false)
const linkCopied = ref(false)
const shareLinkInput = ref<HTMLInputElement>()
const sharedItem = ref<Item | null>(null)

// Bury item
const showBuryModal = ref(false)
const buryingItem = ref(false)
const buryData = ref({
  location_zone: '',
  location_hint: ''
})

// Discard item
const showDiscardModal = ref(false)
const discardingItem = ref(false)

// Universal Key
const showUniversalKeyModal = ref(false)
const usingUniversalKey = ref(false)
const availableTasks = ref<any[]>([])
const selectedTaskId = ref<string>('')

// Treasury Item
const showTreasuryModal = ref(false)
const selectedTreasuryItem = ref<Item | null>(null)

// Detection Radar
const showDetectionRadarModal = ref(false)
const usingDetectionRadar = ref(false)
const detectionResults = ref<any>(null)

// Blizzard Bottle
const showBlizzardBottleModal = ref(false)
const usingBlizzardBottle = ref(false)
const blizzardResults = ref<any>(null)

// Sun Bottle
const showSunBottleModal = ref(false)
const usingSunBottle = ref(false)
const sunBottleResults = ref<any>(null)

// Note management
const showNoteEditModal = ref(false)
const showNoteViewModal = ref(false)
const noteContent = ref('')
const noteTimeRemaining = ref(30)
const noteAutoCloseTimer = ref<number | null>(null)
const editingNote = ref(false)
const viewingNote = ref(false)

// Methods
const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
}

const loadInventory = async () => {
  try {
    loading.value = true
    error.value = null
    inventory.value = await storeApi.getUserInventory()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载背包失败'
  } finally {
    loading.value = false
  }
}

const selectItem = (item: Item) => {
  selectedItem.value = selectedItem.value?.id === item.id ? null : item
}

const getStatusText = (status: string): string => {
  const statusMap = {
    'available': '可用',
    'used': '已使用',
    'expired': '已过期',
    'in_drift_bottle': '漂流中',
    'buried': '已掩埋'
  }
  return statusMap[status as keyof typeof statusMap] || status
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatExpireTime = (dateString: string): string => {
  if (!dateString) return ''
  const expireDate = new Date(dateString)
  const now = new Date()
  const diffMs = expireDate.getTime() - now.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

  if (diffMs <= 0) {
    return '已过期'
  } else if (diffHours >= 24) {
    return `${Math.floor(diffHours / 24)}天后过期`
  } else if (diffHours > 0) {
    return `${diffHours}小时${diffMinutes}分钟后过期`
  } else {
    return `${diffMinutes}分钟后过期`
  }
}

const getDifficultyText = (difficulty: string): string => {
  const difficultyMap = {
    'easy': '简单',
    'normal': '普通',
    'hard': '困难',
    'hell': '地狱'
  }
  return difficultyMap[difficulty as keyof typeof difficultyMap] || difficulty
}

const stripHtmlAndTruncate = (html: string, maxLength: number = 120): string => {
  if (!html) return ''

  // Create a temporary div to strip HTML tags
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  const textContent = tempDiv.textContent || tempDiv.innerText || ''

  // Truncate text if it's too long
  if (textContent.length <= maxLength) {
    return textContent
  }

  return textContent.slice(0, maxLength) + '...'
}

const getTaskReward = (difficulty: string): number => {
  const rewardMap = {
    'easy': 10,
    'normal': 20,
    'hard': 30,
    'hell': 50
  }
  return rewardMap[difficulty as keyof typeof rewardMap] || 10
}

const triggerPhotoInput = () => {
  photoInput.value?.click()
}

const handlePhotoUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !selectedItem.value) return

  try {
    uploadingPhoto.value = true
    await storeApi.uploadPhotoToPaper(selectedItem.value.id, file)
    await loadInventory()
    selectedItem.value = null
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传照片失败'
  } finally {
    uploadingPhoto.value = false
  }
}

const viewPhoto = async (item: Item) => {
  try {
    const blob = await storeApi.viewPhoto(item.id)
    photoUrl.value = URL.createObjectURL(blob)
    viewingPhoto.value = true

    // Start 5-second auto-close timer
    photoTimeRemaining.value = 5
    startPhotoAutoCloseTimer()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '查看照片失败'
  }
}

const startPhotoAutoCloseTimer = () => {
  if (photoAutoCloseTimer.value) {
    clearInterval(photoAutoCloseTimer.value)
  }

  photoAutoCloseTimer.value = window.setInterval(() => {
    photoTimeRemaining.value--

    if (photoTimeRemaining.value <= 0) {
      closePhotoViewer()
    }
  }, 1000)
}

const closePhotoViewer = () => {
  viewingPhoto.value = false

  // Clear timer
  if (photoAutoCloseTimer.value) {
    clearInterval(photoAutoCloseTimer.value)
    photoAutoCloseTimer.value = null
  }

  if (photoUrl.value) {
    URL.revokeObjectURL(photoUrl.value)
    photoUrl.value = ''
  }

  // Reset timer
  photoTimeRemaining.value = 5

  // Refresh inventory as photo might be burned after reading
  loadInventory()
}

const canShareItem = (item: Item): boolean => {
  return item.status === 'available' && ['photo', 'note', 'key', 'little_treasury'].includes(item.item_type.name)
}

const canBuryItem = (item: Item): boolean => {
  return item.status === 'available' && ['photo', 'key', 'note'].includes(item.item_type.name)
}

const canDiscardItem = (item: Item): boolean => {
  return item.status === 'available'
}

const canUseUniversalKey = (item: Item): boolean => {
  // Check if this is a Universal Key using the backend-provided flag
  return item.item_type.name === 'key' &&
         item.status === 'available' &&
         item.is_universal_key === true
}

const canUseTreasury = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'little_treasury'
}

const canUseDetectionRadar = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'detection_radar'
}

const canUseBlizzardBottle = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'blizzard_bottle'
}

const canUseSunBottle = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'sun_bottle'
}

const shareItem = async () => {
  if (!selectedItem.value) return

  try {
    sharingItem.value = true
    // 保存被分享的物品信息
    sharedItem.value = selectedItem.value
    const response = await storeApi.createShareLink(selectedItem.value.id)
    shareLink.value = response.share_url
    shareExpiresAt.value = response.expires_at
    showShareModal.value = true
    selectedItem.value = null
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建分享链接失败'
    sharedItem.value = null
  } finally {
    sharingItem.value = false
  }
}

const closeShareModal = () => {
  showShareModal.value = false
  shareLink.value = ''
  shareExpiresAt.value = ''
  linkCopied.value = false
  sharedItem.value = null
}

const selectShareLink = () => {
  shareLinkInput.value?.select()
}

const copyShareLink = async () => {
  try {
    copyingLink.value = true
    await navigator.clipboard.writeText(shareLink.value)
    linkCopied.value = true
    setTimeout(() => {
      linkCopied.value = false
    }, 2000)
  } catch (err) {
    // Fallback for older browsers
    shareLinkInput.value?.select()
    document.execCommand('copy')
    linkCopied.value = true
    setTimeout(() => {
      linkCopied.value = false
    }, 2000)
  } finally {
    copyingLink.value = false
  }
}

const buryItem = async () => {
  if (!selectedItem.value || !buryData.value.location_zone || !buryData.value.location_hint.trim()) return

  try {
    buryingItem.value = true
    await storeApi.buryItem({
      item_id: selectedItem.value.id,
      location_zone: buryData.value.location_zone,
      location_hint: buryData.value.location_hint
    })
    await loadInventory()
    closeBuryModal()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '掩埋物品失败'
  } finally {
    buryingItem.value = false
  }
}

const closeBuryModal = () => {
  showBuryModal.value = false
  buryData.value = {
    location_zone: '',
    location_hint: ''
  }
  selectedItem.value = null
}

const discardItem = async () => {
  if (!selectedItem.value) return

  try {
    discardingItem.value = true
    await storeApi.discardItem(selectedItem.value.id)
    await loadInventory()
    closeDiscardModal()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '丢弃物品失败'
  } finally {
    discardingItem.value = false
  }
}

const closeDiscardModal = () => {
  showDiscardModal.value = false
  selectedItem.value = null
}

const loadAvailableTasks = async () => {
  try {
    // Clear any previous errors
    error.value = null

    // Load user's active lock tasks
    const tasks = await tasksApi.getTasksList({
      task_type: 'lock',
      status: 'active',
      my_tasks: true
    })

    // Also include voting tasks as they can be completed with universal key
    const votingTasks = await tasksApi.getTasksList({
      task_type: 'lock',
      status: 'voting',
      my_tasks: true
    })

    const allTasks = [...tasks, ...votingTasks]

    // For Universal Key, we don't need to check original key ownership
    // Universal Key can complete any of the user's own tasks regardless of key ownership
    availableTasks.value = allTasks

    // Auto-select the first available task when modal opens
    if (allTasks.length > 0) {
      selectedTaskId.value = allTasks[0].id
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载任务列表失败'
    availableTasks.value = []
  }
}

const useUniversalKey = async () => {
  if (!selectedItem.value || !selectedTaskId.value) return

  try {
    usingUniversalKey.value = true
    const response = await storeApi.useUniversalKey({
      task_id: selectedTaskId.value,
      universal_key_id: selectedItem.value.id
    })

    // Refresh inventory to remove the used key
    await loadInventory()

    // Show success message
    alert(`${response.message}\n获得奖励：${response.reward_coins} 积分`)

    // Close modal and reset selection
    closeUniversalKeyModal()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '使用万能钥匙失败'
  } finally {
    usingUniversalKey.value = false
  }
}

const openUniversalKeyModal = async () => {
  showUniversalKeyModal.value = true
  // Auto-load tasks when modal opens
  await loadAvailableTasks()
}

const closeUniversalKeyModal = () => {
  showUniversalKeyModal.value = false
  selectedTaskId.value = ''
  availableTasks.value = []
  selectedItem.value = null
}

const viewOwnerProfile = (owner: any) => {
  // Navigate to user profile page
  if (owner && owner.id) {
    router.push(`/profile/${owner.id}`)
  }
}

const openTreasuryModal = () => {
  if (!selectedItem.value) return
  selectedTreasuryItem.value = selectedItem.value
  showTreasuryModal.value = true
}

const closeTreasuryModal = () => {
  showTreasuryModal.value = false
  selectedTreasuryItem.value = null
  selectedItem.value = null
}

const handleTreasurySuccess = async () => {
  // Refresh inventory after successful treasury operation
  await loadInventory()
}

const openDetectionRadarModal = () => {
  if (!selectedItem.value) return
  showDetectionRadarModal.value = true
}

const closeDetectionRadarModal = () => {
  showDetectionRadarModal.value = false
  detectionResults.value = null
  selectedItem.value = null
}

const useDetectionRadar = async () => {
  if (!selectedItem.value) return

  try {
    usingDetectionRadar.value = true

    // Get user's own active lock tasks with hidden time
    const tasks = await tasksApiDetailed.getTasksList({
      task_type: 'lock',
      status: 'active',
      my_tasks: true
    })

    // Also include voting tasks
    const votingTasks = await tasksApiDetailed.getTasksList({
      task_type: 'lock',
      status: 'voting',
      my_tasks: true
    })

    const allTasks = [...tasks, ...votingTasks]
    const hiddenTimeTasks = allTasks.filter(task => task.time_display_hidden)

    if (hiddenTimeTasks.length === 0) {
      alert('您没有时间被隐藏的带锁任务')
      return
    }

    // For simplicity, use the first hidden time task
    // In a more complete implementation, you might show a task selection modal
    const targetTask = hiddenTimeTasks[0]

    // Call the detection radar API
    const response = await tasksApiDetailed.useDetectionRadar(targetTask.id)

    // Set the detection results from the API response
    detectionResults.value = {
      task_title: response.revealed_data.task_title,
      status_text: response.revealed_data.status_text,
      time_remaining_ms: response.revealed_data.time_remaining_ms,
      is_frozen: response.revealed_data.is_frozen
    }

    // Refresh inventory after successful use (item should be destroyed)
    await loadInventory()

    // Clear selected item since it was destroyed
    selectedItem.value = null

  } catch (error) {
    console.error('Error using detection radar:', error)
    const errorMessage = error instanceof Error ? error.message : '使用探测雷达失败，请重试'
    alert(errorMessage)
  } finally {
    usingDetectionRadar.value = false
  }
}

const formatTimeRemaining = (milliseconds: number): string => {
  if (milliseconds <= 0) return '已结束'

  const hours = Math.floor(milliseconds / (1000 * 60 * 60))
  const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000)

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

const openBlizzardBottleModal = () => {
  if (!selectedItem.value) return
  showBlizzardBottleModal.value = true
}

const closeBlizzardBottleModal = () => {
  showBlizzardBottleModal.value = false
  blizzardResults.value = null
  selectedItem.value = null
}

const useBlizzardBottle = async () => {
  if (!selectedItem.value) return

  try {
    usingBlizzardBottle.value = true

    // Call the blizzard bottle API
    const response = await tasksApiDetailed.useBlizzardBottle()

    // Set the blizzard results from the API response
    blizzardResults.value = {
      frozen_tasks_count: response.frozen_tasks_count,
      affected_users_count: response.affected_users_count,
      frozen_tasks: response.frozen_tasks,
      item_destroyed: response.item_destroyed
    }

    // Refresh inventory after successful use (item should be destroyed)
    await loadInventory()

    // Clear selected item since it was destroyed
    selectedItem.value = null

  } catch (error) {
    console.error('Error using blizzard bottle:', error)
    const errorMessage = error instanceof Error ? error.message : '使用暴雪瓶失败，请重试'
    alert(errorMessage)
  } finally {
    usingBlizzardBottle.value = false
  }
}

const openSunBottleModal = () => {
  if (!selectedItem.value) return
  showSunBottleModal.value = true
}

const closeSunBottleModal = () => {
  showSunBottleModal.value = false
  sunBottleResults.value = null
  selectedItem.value = null
}

const useSunBottle = async () => {
  if (!selectedItem.value) return

  try {
    usingSunBottle.value = true

    // Call the sun bottle API
    const response = await tasksApiDetailed.useSunBottle()

    // Set the sun bottle results from the API response
    sunBottleResults.value = {
      unfrozen_tasks_count: response.unfrozen_tasks_count,
      affected_users_count: response.affected_users_count,
      unfrozen_tasks: response.unfrozen_tasks,
      item_destroyed: response.item_destroyed
    }

    // Refresh inventory after successful use (item should be destroyed)
    await loadInventory()

    // Clear selected item since it was destroyed
    selectedItem.value = null

  } catch (error) {
    console.error('Error using sun bottle:', error)
    const errorMessage = error instanceof Error ? error.message : '使用太阳瓶失败，请重试'
    alert(errorMessage)
  } finally {
    usingSunBottle.value = false
  }
}

// Note management functions
const openNoteEditModal = () => {
  if (!selectedItem.value) return

  // Load existing content if available
  noteContent.value = selectedItem.value.properties?.content || ''
  showNoteEditModal.value = true
}

const closeNoteEditModal = () => {
  showNoteEditModal.value = false
  noteContent.value = ''
  editingNote.value = false
}

const saveNoteContent = async () => {
  if (!selectedItem.value || !noteContent.value.trim()) return

  try {
    editingNote.value = true
    await storeApi.editNote(selectedItem.value.id, noteContent.value.trim())

    // Refresh inventory to get updated note
    await loadInventory()

    // Close modal
    closeNoteEditModal()

    // Clear selected item to refresh the view
    selectedItem.value = null

  } catch (error) {
    console.error('Error editing note:', error)
    const errorMessage = error instanceof Error ? error.message : '编辑纸条失败，请重试'
    alert(errorMessage)
  } finally {
    editingNote.value = false
  }
}

const openNoteViewModal = () => {
  if (!selectedItem.value) return
  showNoteViewModal.value = true
}

const closeNoteViewModal = () => {
  showNoteViewModal.value = false
  viewingNote.value = false

  // Clear timer
  if (noteAutoCloseTimer.value) {
    clearInterval(noteAutoCloseTimer.value)
    noteAutoCloseTimer.value = null
  }

  // Reset timer
  noteTimeRemaining.value = 30

  // Refresh inventory as note might be destroyed after reading
  loadInventory()

  // Clear selected item
  selectedItem.value = null
}

const viewNote = async () => {
  if (!selectedItem.value) return

  try {
    viewingNote.value = true

    // Call the view note API
    const response = await storeApi.viewNote(selectedItem.value.id)
    noteContent.value = response.content

    // Start 30-second auto-close timer
    noteTimeRemaining.value = 30
    startNoteAutoCloseTimer()

  } catch (error) {
    console.error('Error viewing note:', error)
    const errorMessage = error instanceof Error ? error.message : '查看纸条失败，请重试'
    alert(errorMessage)
    closeNoteViewModal()
  } finally {
    viewingNote.value = false
  }
}

const startNoteAutoCloseTimer = () => {
  if (noteAutoCloseTimer.value) {
    clearInterval(noteAutoCloseTimer.value)
  }

  noteAutoCloseTimer.value = window.setInterval(() => {
    noteTimeRemaining.value--

    if (noteTimeRemaining.value <= 0) {
      closeNoteViewModal()
    }
  }, 1000)
}

// Lifecycle
onMounted(() => {
  loadInventory()
})
</script>

<style scoped>
/* Neo-Brutalism Inventory Design */
.inventory-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header */
.inventory-header {
  background: white;
  border-bottom: 4px solid #000;
  padding: 1.5rem 0;
  box-shadow: 0 4px 0 #000;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.back-btn {
  background: #dc3545;
  color: white;
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.back-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.inventory-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.capacity-display {
  background: #17a2b8;
  color: white;
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 4px 4px 0 #000;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.capacity-text {
  font-size: 0.875rem;
}

.capacity-amount {
  font-size: 1.25rem;
}

.store-btn {
  background: #007bff;
  color: white;
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.store-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

/* Loading State */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.loading-box {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #000;
}

.loading-spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

/* Error State */
.error-state {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.error-box {
  background: #f8d7da;
  border: 4px solid #dc3545;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #dc3545;
  max-width: 500px;
}

.error-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #dc3545;
}

.error-message {
  margin: 0 0 2rem 0;
  color: #721c24;
}

.retry-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Inventory Content */
.inventory-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.inventory-section {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
}

/* Inventory Grid */
.inventory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

/* Inventory Slots */
.inventory-slot {
  aspect-ratio: 1;
  border: 4px solid #000;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.inventory-slot.occupied {
  background: white;
  box-shadow: 4px 4px 0 #000;
}

.inventory-slot.occupied:hover {
  transform: translate(-2px, -2px);
  box-shadow: 8px 8px 0 #000;
}

.inventory-slot.occupied.selected {
  background: #007bff;
  color: white;
  border-color: #000;
  box-shadow: 8px 8px 0 #000;
  transform: translate(-2px, -2px);
}

.inventory-slot.empty {
  background: #f8f9fa;
  border-style: dashed;
  border-color: #666;
  box-shadow: inset 2px 2px 0 #ddd;
}

.slot-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  text-align: center;
}

.item-icon {
  font-size: 2rem;
  display: block;
}

.item-name {
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  line-height: 1.2;
}

.item-status {
  font-size: 0.625rem;
  font-weight: 700;
  color: #666;
  text-transform: uppercase;
}

.inventory-slot.occupied.selected .item-status {
  color: #cce7ff;
}

.empty-text {
  font-size: 0.875rem;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Item Details Panel */
.item-details-panel {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.item-info {
  flex: 1;
}

.item-title {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0 0 1rem 0;
}

.item-title-icon {
  font-size: 3rem;
}

.item-title-text {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
}

.item-description {
  color: #333;
  line-height: 1.5;
  margin: 0 0 1rem 0;
  font-weight: 500;
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.875rem;
}

.meta-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
}

.meta-value {
  font-weight: 700;
  color: #000;
}

.owner-link {
  background: #17a2b8;
  color: white;
  border: 2px solid #000;
  padding: 0.25rem 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.75rem;
}

.owner-link:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
  background: #138496;
}

.no-owner {
  color: #999;
  font-style: italic;
  font-weight: 600;
}

.close-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 0.75rem;
  font-weight: 900;
  font-size: 1.25rem;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.close-btn:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

/* Properties Section */
.properties-section {
  margin-bottom: 1.5rem;
}

.properties-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.properties-content {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1rem;
}

.properties-json {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  margin: 0;
  white-space: pre-wrap;
  color: #333;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #28a745;
  color: white;
}

.action-btn.secondary {
  background: #6c757d;
  color: white;
}

.action-btn.danger {
  background: #dc3545;
  color: white;
}

.action-btn.universal-key {
  background: #ffc107;
  color: #000;
  border-color: #000;
}

.action-btn.universal-key:hover {
  background: #e0a800;
  color: #000;
}

.action-btn.radar {
  background: #17a2b8;
  color: white;
  border-color: #000;
}

.action-btn.radar:hover {
  background: #138496;
  color: white;
}

.action-btn.blizzard {
  background: #6f42c1;
  color: white;
  border-color: #000;
}

.action-btn.blizzard:hover {
  background: #5a32a3;
  color: white;
}

.action-btn.sun {
  background: #ff8c00;
  color: white;
  border-color: #000;
}

.action-btn.sun:hover {
  background: #ff7700;
  color: white;
}

.action-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Empty Inventory */
.empty-inventory {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.empty-box {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #000;
  max-width: 500px;
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.empty-message {
  margin: 0 0 2rem 0;
  color: #666;
  font-weight: 500;
}

.empty-action-btn {
  background: #007bff;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  display: inline-block;
}

.empty-action-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  overflow-y: auto;
}

/* Loading Modal */
.loading-modal {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 12px 12px 0 #000;
  max-width: 400px;
  width: 100%;
}

/* Action Modal */
.action-modal {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 12px 12px 0 #000;
  max-width: 500px;
  width: 100%;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
}

/* Modal Form */
.modal-form {
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 0.5rem;
  color: #000;
  font-size: 0.875rem;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  border: 3px solid #000;
  padding: 0.75rem;
  font-weight: 700;
  background: white;
  color: #000;
}

.form-textarea {
  height: 100px;
  resize: none;
  font-family: inherit;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  box-shadow: 0 0 0 3px #007bff;
}

.char-counter {
  font-size: 0.75rem;
  font-weight: 700;
  color: #666;
  margin-top: 0.5rem;
  text-align: right;
}

/* Modal Actions */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.modal-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.modal-btn.primary {
  background: #28a745;
  color: white;
}

.modal-btn.secondary {
  background: #6c757d;
  color: white;
}

.modal-btn:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.modal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-btn.danger {
  background: #dc3545;
  color: white;
}

/* Modal close button */
.modal-close {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  font-size: 1.5rem;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Modal header layout */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  position: relative;
}

/* Warning Section */
.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: #f8d7da;
  border: 3px solid #dc3545;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #dc3545;
}

.warning-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 1.1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #721c24;
}

.warning-message {
  font-weight: 700;
  color: #721c24;
  margin: 0 0 0.5rem 0;
}

.warning-note {
  font-size: 0.875rem;
  font-weight: 600;
  color: #856404;
  margin: 0;
}

/* Item Details */
.item-details {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.details-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.details-content {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
}

.details-json {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  margin: 0;
  white-space: pre-wrap;
  color: #333;
}

/* Form Elements */
.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 0.5rem;
  color: #000;
  font-size: 0.875rem;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  border: 3px solid #000;
  padding: 0.75rem;
  font-weight: 700;
  background: white;
  color: #000;
}

.form-input {
  height: auto;
}

.form-select {
  height: auto;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23000' stroke-linecap='round' stroke-linejoin='round' stroke-width='3' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.75rem center;
  background-repeat: no-repeat;
  background-size: 1rem 1rem;
  padding-right: 2.5rem;
}

.form-textarea {
  height: 100px;
  resize: none;
  font-family: inherit;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  box-shadow: 0 0 0 3px #007bff;
}

.char-counter {
  font-size: 0.75rem;
  font-weight: 700;
  color: #666;
  margin-top: 0.5rem;
  text-align: right;
}

/* Item Info Section */
.item-info-section {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 1.5rem;
  margin-top: 1.5rem;
  box-shadow: 4px 4px 0 #17a2b8;
}

.info-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.item-info-card {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 3px 3px 0 #000;
}

.item-info-card .item-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.item-info-card .item-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-info-card .item-name {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #000;
  font-size: 0.875rem;
}

.item-info-card .item-description {
  font-size: 0.75rem;
  color: #666;
  font-weight: 600;
}

/* Photo Viewer */
.photo-viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.photo-viewer-content {
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.photo-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.photo-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border: 4px solid white;
  box-shadow: 8px 8px 0 rgba(255, 255, 255, 0.3);
}

.photo-timer {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: #dc3545;
  border: 3px solid white;
  padding: 0.75rem 1rem;
  box-shadow: 4px 4px 0 rgba(255, 255, 255, 0.8);
  min-width: 120px;
}

.timer-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.timer-icon {
  font-size: 1.25rem;
}

.timer-text {
  color: white;
  font-weight: 900;
  font-size: 1.25rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timer-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border: 2px solid white;
  overflow: hidden;
}

.timer-progress {
  height: 100%;
  background: white;
  transition: width 1s linear;
}

.photo-hint {
  background: rgba(0, 0, 0, 0.8);
  border: 3px solid white;
  padding: 1.5rem 2rem;
  text-align: center;
  box-shadow: 8px 8px 0 rgba(255, 255, 255, 0.3);
  max-width: 500px;
}

.hint-text {
  color: white;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
}

.hint-action {
  color: rgba(255, 255, 255, 0.8);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
  font-size: 0.875rem;
}

/* Hidden input */
.hidden {
  display: none;
}

/* Share Modal - Neo-Brutalism Style */
.share-modal {
  background: white;
  border: 4px solid #000;
  box-shadow: 16px 16px 0 #000;
  max-width: 600px;
  width: 100%;
  transform: rotate(-1deg);
  animation: shareModalEnter 0.3s ease-out;
}

@keyframes shareModalEnter {
  0% {
    transform: rotate(-1deg) scale(0.8);
    opacity: 0;
  }
  100% {
    transform: rotate(-1deg) scale(1);
    opacity: 1;
  }
}

.share-modal-header {
  background: #28a745;
  border-bottom: 4px solid #000;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.share-success-badge {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.success-icon {
  font-size: 2rem;
  animation: bounce 0.6s ease-in-out infinite alternate;
}

@keyframes bounce {
  0% { transform: translateY(0px); }
  100% { transform: translateY(-8px); }
}

.share-modal-title {
  font-size: 1.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: white;
  text-shadow: 2px 2px 0 #000;
}

.share-modal-close {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  font-size: 1.5rem;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.share-modal-close:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.share-modal-body {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Shared Item Preview */
.shared-item-preview {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 6px 6px 0 #17a2b8;
  transform: rotate(1deg);
}

.item-preview-icon {
  font-size: 3rem;
  flex-shrink: 0;
  background: white;
  border: 3px solid #000;
  width: 4rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3px 3px 0 #000;
}

.item-preview-details {
  flex: 1;
}

.item-preview-name {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.item-preview-description {
  font-size: 1rem;
  font-weight: 700;
  color: #17a2b8;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Success Message Section */
.share-success-message {
  text-align: center;
}

.success-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.success-description {
  font-size: 1.1rem;
  font-weight: 700;
  color: #666;
  margin: 0 0 1.5rem 0;
  line-height: 1.4;
}

.success-warning {
  background: #fff3cd;
  border: 3px solid #ffc107;
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  box-shadow: 4px 4px 0 #ffc107;
  transform: rotate(-0.5deg);
}

.warning-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.warning-text {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #856404;
  font-size: 0.875rem;
}

/* Expiration Info */
.expiration-info {
  margin-top: 1.5rem;
  text-align: center;
}

.expiration-badge {
  background: #e8f5e8;
  border: 3px solid #28a745;
  padding: 0.75rem 1.5rem;
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  box-shadow: 3px 3px 0 #28a745;
  transform: rotate(0.5deg);
  margin-bottom: 1rem;
}

.expiration-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.expiration-text {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #155724;
  font-size: 0.875rem;
}

.expiration-note {
  font-size: 0.875rem;
  font-weight: 600;
  color: #666;
  margin: 0;
  font-style: italic;
}

/* Share Link Section */
.share-link-section {
  background: #f8f9fa;
  border: 3px solid #6c757d;
  padding: 1.5rem;
  box-shadow: 6px 6px 0 #6c757d;
  transform: rotate(0.5deg);
}

.share-link-label {
  display: block;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 1rem;
  color: #000;
  font-size: 1rem;
}

.share-link-container {
  display: flex;
  gap: 1rem;
  align-items: stretch;
}

.share-link-input-wrapper {
  flex: 1;
  position: relative;
}

.share-link-input {
  width: 100%;
  border: 3px solid #000;
  padding: 0.875rem 1rem;
  font-weight: 700;
  background: white;
  color: #000;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  box-shadow: inset 2px 2px 0 rgba(0, 0, 0, 0.1);
}

.share-link-input:focus {
  outline: none;
  box-shadow: inset 2px 2px 0 rgba(0, 0, 0, 0.1), 0 0 0 3px #007bff;
}

.share-copy-btn {
  background: #007bff;
  color: white;
  border: 3px solid #000;
  padding: 0.875rem 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: 140px;
}

.share-copy-btn:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.share-copy-btn.copying {
  background: #ffc107;
  color: #000;
}

.share-copy-btn.copied {
  background: #28a745;
  color: white;
}

.share-copy-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Share Modal Footer */
.share-modal-footer {
  background: #f8f9fa;
  border-top: 4px solid #000;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: center;
}

.share-close-btn {
  background: #6c757d;
  color: white;
  border: 3px solid #000;
  padding: 1rem 3rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  cursor: pointer;
  box-shadow: 6px 6px 0 #000;
  transition: all 0.2s ease;
  font-size: 1.1rem;
}

.share-close-btn:hover {
  transform: translate(3px, 3px);
  box-shadow: 3px 3px 0 #000;
  background: #5a6268;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .inventory-header {
    padding: 1rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .inventory-title {
    font-size: 1.5rem;
  }

  .inventory-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 0.75rem;
  }

  .inventory-section {
    padding: 1.5rem;
  }

  .item-details-panel {
    padding: 1.5rem;
  }

  .panel-header {
    flex-direction: column;
    gap: 1rem;
  }

  .item-title {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .action-buttons {
    flex-direction: column;
  }

  .modal-actions {
    flex-direction: column;
    gap: 0.75rem;
  }

  /* Share Modal Mobile Styles */
  .share-modal {
    margin: 1rem;
    max-width: calc(100vw - 2rem);
    max-height: calc(100vh - 2rem);
    box-shadow: 8px 8px 0 #000;
    overflow-y: auto;
  }

  .share-modal-header {
    padding: 1rem 1.5rem;
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .share-modal-title {
    font-size: 1.25rem;
    letter-spacing: 1px;
  }

  .share-modal-close {
    width: 2.5rem;
    height: 2.5rem;
    font-size: 1.25rem;
  }

  .share-modal-body {
    padding: 1.5rem;
    gap: 1.5rem;
  }

  .shared-item-preview {
    padding: 1rem;
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .item-preview-icon {
    font-size: 2.5rem;
    width: 3.5rem;
    height: 3.5rem;
  }

  .item-preview-name {
    font-size: 1rem;
  }

  .success-title {
    font-size: 1.25rem;
  }

  .success-description {
    font-size: 1rem;
  }

  .success-warning {
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }

  .share-link-container {
    flex-direction: column;
    gap: 0.75rem;
  }

  .share-copy-btn {
    width: 100%;
    min-width: auto;
    padding: 1rem;
  }

  .share-modal-footer {
    padding: 1rem 1.5rem;
  }

  .share-close-btn {
    padding: 0.875rem 2rem;
    font-size: 1rem;
    letter-spacing: 1px;
  }

  /* Expiration Info Mobile Styles */
  .expiration-info {
    margin-top: 1rem;
  }

  .expiration-badge {
    padding: 0.5rem 1rem;
    margin-bottom: 0.75rem;
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }

  .expiration-icon {
    font-size: 1rem;
  }

  .expiration-text {
    font-size: 0.75rem;
  }

  .expiration-note {
    font-size: 0.75rem;
  }
}

/* Universal Key Modal Specific Styles */
.form-button {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  background: white;
  color: #000;
}

.form-button.secondary {
  background: #6c757d;
  color: white;
}

.form-button:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.no-tasks-message {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border: 3px solid #6c757d;
  box-shadow: 4px 4px 0 #6c757d;
}

.no-tasks-message p {
  margin: 0.5rem 0;
  font-weight: 700;
}

.no-tasks-message .hint {
  font-size: 0.875rem;
  color: #666;
  font-weight: 600;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 300px;
  overflow-y: auto;
}

.task-item {
  border: 3px solid #000;
  background: white;
  padding: 1rem;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.task-item:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.task-item.selected {
  background: #007bff;
  color: white;
  border-color: #000;
}

.task-info {
  flex: 1;
}

.task-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
}

.task-meta {
  display: flex;
  gap: 1rem;
  margin: 0 0 0.5rem 0;
}

.task-difficulty,
.task-status {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.25rem 0.5rem;
  border: 2px solid #000;
  background: white;
  color: #000;
}

.task-item.selected .task-difficulty,
.task-item.selected .task-status {
  background: #cce7ff;
  color: #000;
}

.task-description {
  font-size: 0.875rem;
  line-height: 1.4;
  margin: 0;
  font-weight: 600;
}

.task-item.selected .task-description {
  color: #cce7ff;
}

.task-rewards {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.reward-coins {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  color: #28a745;
  background: white;
  padding: 0.5rem;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
}

.task-item.selected .reward-coins {
  background: #cce7ff;
  color: #28a745;
}

/* Detection Radar Modal Styles */
.detection-radar-modal {
  max-width: 600px;
  width: 100%;
}

.detection-results-section {
  background: #f8f9fa;
  border: 3px solid #17a2b8;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #17a2b8;
}

.detection-results-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.detection-result-card {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.detection-result-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.detection-result-card.highlight {
  background: #e8f5e8;
  border-color: #28a745;
  box-shadow: 3px 3px 0 #28a745;
}

.detection-result-card.highlight:hover {
  box-shadow: 4px 4px 0 #28a745;
}

.detection-result-card.frozen {
  background: #e1f5fe;
  border-color: #17a2b8;
  box-shadow: 3px 3px 0 #17a2b8;
}

.detection-result-card.frozen:hover {
  box-shadow: 4px 4px 0 #17a2b8;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #eee;
}

.result-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.result-label {
  font-size: 0.875rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
}

.result-content {
  font-size: 1rem;
  font-weight: 700;
  color: #000;
  line-height: 1.3;
}

.result-content.time-display {
  font-size: 1.25rem;
  font-weight: 900;
  color: #28a745;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.1);
}

.detection-result-card.highlight .result-content.time-display {
  color: #155724;
  background: linear-gradient(45deg, #28a745, #20c997);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
}

/* Responsive Design for Detection Radar */
@media (max-width: 768px) {
  .detection-radar-modal {
    margin: 1rem;
    max-width: calc(100vw - 2rem);
  }

  .detection-results-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .detection-result-card {
    padding: 0.75rem;
  }

  .result-header {
    margin-bottom: 0.5rem;
    padding-bottom: 0.25rem;
  }

  .result-icon {
    font-size: 1rem;
  }

  .result-label {
    font-size: 0.75rem;
  }

  .result-content {
    font-size: 0.875rem;
  }

  .result-content.time-display {
    font-size: 1rem;
  }
}

/* Blizzard Bottle Modal Styles */
.blizzard-bottle-modal {
  max-width: 600px;
  width: 100%;
}

.blizzard-results-section {
  background: #e8f4f8;
  border: 3px solid #6f42c1;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #6f42c1;
}

.blizzard-results-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.blizzard-result-card {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.blizzard-result-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.frozen-tasks-list {
  grid-column: 1 / -1;
  margin-top: 1rem;
}

.tasks-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.frozen-task-item {
  background: #f8f9fa;
  border: 2px solid #6f42c1;
  padding: 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 2px 2px 0 #6f42c1;
}

.task-title {
  font-weight: 700;
  color: #000;
  flex: 1;
}

.task-owner {
  font-size: 0.875rem;
  font-weight: 600;
  color: #6f42c1;
  background: white;
  padding: 0.25rem 0.5rem;
  border: 1px solid #6f42c1;
}

/* Responsive Design for Blizzard Bottle */
@media (max-width: 768px) {
  .blizzard-bottle-modal {
    margin: 1rem;
    max-width: calc(100vw - 2rem);
  }

  .blizzard-results-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .blizzard-result-card {
    padding: 0.75rem;
  }

  .frozen-task-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .task-owner {
    align-self: flex-end;
  }
}

/* Sun Bottle Modal Styles */
.sun-bottle-modal {
  max-width: 600px;
  width: 100%;
}

.sun-results-section {
  background: #fff8dc;
  border: 3px solid #ff8c00;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #ff8c00;
}

.sun-results-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.sun-result-card {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.sun-result-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.unfrozen-tasks-list {
  grid-column: 1 / -1;
  margin-top: 1rem;
}

.unfrozen-task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: white;
  border: 2px solid #000;
  margin-bottom: 0.5rem;
  box-shadow: 2px 2px 0 #000;
  gap: 1rem;
}

.unfrozen-task-item:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

/* Responsive Design for Sun Bottle */
@media (max-width: 768px) {
  .sun-bottle-modal {
    margin: 1rem;
    max-width: calc(100vw - 2rem);
  }

  .sun-results-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .sun-result-card {
    padding: 0.75rem;
  }

  .unfrozen-task-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .task-owner {
    align-self: flex-end;
  }
}

/* Note Modal Styles */
.note-edit-modal {
  max-width: 500px;
  width: 100%;
}

.note-textarea {
  min-height: 100px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
}

/* Note Viewer Styles */
.note-viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.note-viewer-content {
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.note-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 rgba(255, 255, 255, 0.3);
  min-width: 400px;
  min-height: 200px;
}

.note-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  flex: 1;
  justify-content: center;
  text-align: center;
}

.note-icon {
  font-size: 3rem;
}

.note-text {
  font-size: 1.25rem;
  font-weight: 700;
  color: #000;
  line-height: 1.5;
  max-width: 300px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.note-timer {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: #dc3545;
  border: 3px solid #000;
  padding: 0.75rem 1rem;
  box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.8);
  min-width: 120px;
}

.timer-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.timer-icon {
  font-size: 1.25rem;
  color: white;
}

.timer-text {
  color: white;
  font-weight: 900;
  font-size: 1.25rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timer-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border: 2px solid #000;
  overflow: hidden;
}

.timer-progress {
  height: 100%;
  background: white;
  transition: width 1s linear;
}

.note-hint {
  background: rgba(0, 0, 0, 0.8);
  border: 3px solid white;
  padding: 1.5rem 2rem;
  text-align: center;
  box-shadow: 8px 8px 0 rgba(255, 255, 255, 0.3);
  max-width: 500px;
}

.hint-text {
  color: white;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
}

.hint-action {
  color: rgba(255, 255, 255, 0.8);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
  font-size: 0.875rem;
}

/* Mobile Responsive for Note Modals */
@media (max-width: 768px) {
  .note-edit-modal {
    margin: 1rem;
    max-width: calc(100vw - 2rem);
  }

  .note-container {
    min-width: 300px;
    padding: 1.5rem;
  }

  .note-text {
    font-size: 1rem;
    max-width: 250px;
  }

  .note-timer {
    padding: 0.5rem 0.75rem;
    min-width: 100px;
  }

  .timer-text {
    font-size: 1rem;
  }

  .note-hint {
    padding: 1rem 1.5rem;
    margin: 0 1rem;
  }

  .hint-text {
    font-size: 1rem;
  }

  .hint-action {
    font-size: 0.75rem;
  }
}
</style>