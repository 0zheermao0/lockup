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
            🛍️ 商店
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
              :class="{
                'in-game': item.status === 'in_game'
              }"
            >
              <div class="slot-content">
                <span class="item-icon">{{ item.item_type.icon }}</span>
                <span class="item-name">{{ item.item_type.display_name }}</span>
                <span class="item-status">{{ getStatusText(item.status) }}</span>
              </div>
            </div>

            <!-- Empty slots (使用 Math.max 确保不会出现负数，防止背包溢出时报错) -->
            <div
              v-for="n in Math.max(0, inventory?.available_slots || 0)"
              :key="`empty-${n}`"
              class="inventory-slot empty"
            >
              <div class="slot-content">
                <span class="empty-text">空槽</span>
              </div>
            </div>

            <!-- Overflow items (当背包溢出时显示) -->
            <div
              v-if="(inventory?.used_slots || 0) > (inventory?.max_slots || 6)"
              class="inventory-slot overflow-info"
            >
              <div class="slot-content">
                <span class="overflow-icon">⚠️</span>
                <span class="overflow-text">背包已满</span>
                <span class="overflow-count">{{ (inventory?.used_slots || 0) - (inventory?.max_slots || 6) }} 个物品溢出</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Item details toast -->
        <NotificationToast
          v-if="selectedItem"
          :is-visible="!!selectedItem"
          type="info"
          :title="`${selectedItem.item_type.icon} ${selectedItem.item_type.display_name}`"
          :message="selectedItem.item_type.description"
          @close="selectedItem = null"
          :show-actions="false"
        >
          <!-- Custom content slot -->
          <template #default>
            <div class="item-toast-content">
              <!-- Item meta info -->
              <div class="item-meta">
                <p class="meta-item">
                  <span class="meta-label">状态:</span>
                  <span class="meta-value">{{ getStatusText(selectedItem.status) }}</span>
                </p>
                <!-- In-game status special notice -->
                <div v-if="selectedItem.status === 'in_game'" class="in-game-notice">
                  <div class="notice-icon">🎮</div>
                  <div class="notice-content">
                    <p class="notice-title">物品已预留为游戏奖品</p>
                    <p class="notice-text">此物品已被设置为掷骰子游戏的奖励，游戏结算前无法使用或处置。</p>
                  </div>
                </div>
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

              <!-- Item properties (only show for items other than keys, photos, treasury, notes, and time_anchor) -->
              <div v-if="Object.keys(selectedItem.properties).length > 0 && !['key', 'photo', 'little_treasury', 'note', 'time_anchor'].includes(selectedItem.item_type.name)" class="properties-section">
                <h4 class="properties-title">物品属性</h4>
                <div class="properties-content">
                  <pre class="properties-json">{{ JSON.stringify(selectedItem.properties, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </template>

          <!-- Custom actions slot -->
          <template #actions>
            <!-- Photo paper upload -->
            <div v-if="selectedItem.item_type.name === 'photo_paper' && selectedItem.status === 'available'">
              <input
                type="file"
                ref="photoInput"
                accept="image/*"
                @change="handlePhotoUpload"
                class="hidden"
              >
              <button
                @click.stop.prevent="triggerPhotoInput"
                @touchstart.prevent
                class="action-btn primary"
              >
                📸 上传照片
              </button>
            </div>

            <!-- Photo view -->
            <button
              v-if="selectedItem.item_type.name === 'photo' && selectedItem.status === 'available'"
              @click.stop.prevent="handleItemAction('photo_view', selectedItem)"
              @touchstart.prevent
              class="action-btn primary"
            >
              👁️ 查看照片
            </button>

            <!-- Note edit -->
            <button
              v-if="selectedItem.item_type.name === 'note' && selectedItem.status === 'available' && (!selectedItem.properties?.content || selectedItem.properties.content.trim() === '')"
              @click.stop.prevent="handleItemAction('note_edit', selectedItem)"
              @touchstart.prevent
              class="action-btn primary"
            >
              ✏️ 编写纸条
            </button>

            <!-- Note edit (existing content) -->
            <button
              v-if="selectedItem.item_type.name === 'note' && selectedItem.status === 'available' && selectedItem.properties?.content && selectedItem.properties.content.trim() !== ''"
              @click.stop.prevent="handleItemAction('note_edit', selectedItem)"
              @touchstart.prevent
              class="action-btn secondary"
            >
              ✏️ 编辑纸条
            </button>

            <!-- Note view -->
            <button
              v-if="selectedItem.item_type.name === 'note' && selectedItem.status === 'available' && selectedItem.properties?.content && selectedItem.properties.content.trim() !== ''"
              @click.stop.prevent="handleItemAction('note_view', selectedItem)"
              @touchstart.prevent
              class="action-btn primary"
            >
              👁️ 查看纸条
            </button>

            <!-- Share item -->
            <button
              v-if="canShareItem(selectedItem)"
              @click.stop.prevent="handleItemAction('share', selectedItem)"
              @touchstart.prevent
              class="action-btn secondary"
              :disabled="sharingItem"
            >
              <span v-if="sharingItem">分享中...</span>
              <span v-else>🔗 分享物品</span>
            </button>

            <!-- Bury item -->
            <button
              v-if="canBuryItem(selectedItem)"
              @click.stop.prevent="handleItemAction('bury', selectedItem)"
              @touchstart.prevent
              class="action-btn secondary"
            >
              ⛏️ 掩埋物品
            </button>

            <!-- Universal Key usage -->
            <button
              v-if="canUseUniversalKey(selectedItem)"
              @click.stop.prevent="handleItemAction('universal_key', selectedItem)"
              @touchstart.prevent
              class="action-btn universal-key"
              :disabled="usingUniversalKey"
            >
              <span v-if="usingUniversalKey">使用中...</span>
              <span v-else>🗝️ 使用万能钥匙</span>
            </button>

            <!-- Treasury Item usage -->
            <button
              v-if="canUseTreasury(selectedItem)"
              @click.stop.prevent="handleItemAction('treasury', selectedItem)"
              @touchstart.prevent
              class="action-btn primary"
            >
              💰 管理小金库
            </button>

            <!-- Detection Radar usage -->
            <button
              v-if="canUseDetectionRadar(selectedItem)"
              @click.stop.prevent="handleItemAction('detection_radar', selectedItem)"
              @touchstart.prevent
              class="action-btn radar"
              :disabled="usingDetectionRadar"
            >
              <span v-if="usingDetectionRadar">探测中...</span>
              <span v-else>🎯 使用探测雷达</span>
            </button>

            <!-- Blizzard Bottle usage -->
            <button
              v-if="canUseBlizzardBottle(selectedItem)"
              @click.stop.prevent="handleItemAction('blizzard_bottle', selectedItem)"
              @touchstart.prevent
              class="action-btn blizzard"
              :disabled="usingBlizzardBottle"
            >
              <span v-if="usingBlizzardBottle">释放中...</span>
              <span v-else>🌨️ 使用暴雪瓶</span>
            </button>

            <!-- Sun Bottle usage -->
            <button
              v-if="canUseSunBottle(selectedItem)"
              @click.stop.prevent="handleItemAction('sun_bottle', selectedItem)"
              @touchstart.prevent
              class="action-btn sun"
              :disabled="usingSunBottle"
            >
              <span v-if="usingSunBottle">使用中...</span>
              <span v-else>☀️ 使用太阳瓶</span>
            </button>

            <!-- Time Hourglass usage -->
            <button
              v-if="canUseTimeHourglass(selectedItem)"
              @click.stop.prevent="handleItemAction('time_hourglass', selectedItem)"
              @touchstart.prevent
              class="action-btn hourglass"
              :disabled="usingTimeHourglass"
            >
              <span v-if="usingTimeHourglass">使用中...</span>
              <span v-else>⏳ 使用时间沙漏</span>
            </button>

            <!-- Lucky Charm usage -->
            <button
              v-if="canUseLuckyCharm(selectedItem)"
              @click.stop.prevent="handleItemAction('lucky_charm', selectedItem)"
              @touchstart.prevent
              class="action-btn lucky-charm"
              :disabled="usingLuckyCharm"
            >
              <span v-if="usingLuckyCharm">使用中...</span>
              <span v-else>🍀 使用幸运符</span>
            </button>

            <!-- Energy Potion usage -->
            <button
              v-if="canUseEnergyPotion(selectedItem)"
              @click.stop.prevent="handleItemAction('energy_potion', selectedItem)"
              @touchstart.prevent
              class="action-btn energy-potion"
              :disabled="usingEnergyPotion"
            >
              <span v-if="usingEnergyPotion">使用中...</span>
              <span v-else>⚡ 使用活力药水</span>
            </button>

            <!-- Time Anchor usage -->
            <button
              v-if="canUseTimeAnchor(selectedItem)"
              @click.stop.prevent="handleItemAction('time_anchor', selectedItem)"
              @touchstart.prevent
              class="action-btn time-anchor"
              :disabled="usingTimeAnchor"
            >
              <span v-if="usingTimeAnchor">使用中...</span>
              <span v-else>⚓ 使用时间锚点</span>
            </button>

            <!-- Exploration Compass usage -->
            <button
              v-if="canUseExplorationCompass(selectedItem)"
              @click.stop.prevent="handleItemAction('exploration_compass', selectedItem)"
              @touchstart.prevent
              class="action-btn exploration-compass"
              :disabled="usingExplorationCompass"
            >
              <span v-if="usingExplorationCompass">使用中...</span>
              <span v-else>🧭 使用探索指南针</span>
            </button>

            <!-- Influence Crown usage -->
            <button
              v-if="canUseInfluenceCrown(selectedItem)"
              @click.stop.prevent="handleItemAction('influence_crown', selectedItem)"
              @touchstart.prevent
              class="action-btn influence-crown"
              :disabled="usingInfluenceCrown"
            >
              <span v-if="usingInfluenceCrown">使用中...</span>
              <span v-else>👑 使用影响力皇冠</span>
            </button>

            <!-- Small Campfire usage -->
            <button
              v-if="canUseSmallCampfire(selectedItem)"
              @click.stop.prevent="handleItemAction('small_campfire', selectedItem)"
              @touchstart.prevent
              class="action-btn small-campfire"
              :disabled="usingSmallCampfire"
            >
              <span v-if="usingSmallCampfire">使用中...</span>
              <span v-else>🔥 使用小火堆</span>
            </button>

            <!-- Discard item -->
            <button
              v-if="canDiscardItem(selectedItem)"
              @click.stop.prevent="handleItemAction('discard', selectedItem)"
              @touchstart.prevent
              class="action-btn danger"
            >
              🗑️ 丢弃物品
            </button>

            <!-- Close button -->
            <button
              @click.stop.prevent="selectedItem = null"
              @touchstart.prevent
              class="action-btn secondary"
            >
              关闭
            </button>
          </template>
        </NotificationToast>

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


            <div v-if="itemToBury" class="item-info-section">
              <h4 class="info-title">📦 掩埋物品</h4>
              <div class="item-info-card">
                <span class="item-icon">{{ itemToBury.item_type.icon }}</span>
                <div class="item-details">
                  <span class="item-name">{{ itemToBury.item_type.display_name }}</span>
                  <span class="item-description">{{ itemToBury.item_type.description }}</span>
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
                  万能钥匙可以直接完成任何可完成的带锁任务，并获得正常的完成奖励。
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

      <!-- Time Hourglass Modal -->
      <div v-if="showTimeHourglassModal" class="modal-overlay" @click.self="closeTimeHourglassModal">
        <div class="action-modal time-hourglass-modal">
          <div class="modal-header">
            <h3 class="modal-title">⏳ 使用时间沙漏</h3>
            <button @click="closeTimeHourglassModal" class="modal-close">×</button>
          </div>

          <div v-if="!hourglassResults" class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">⏳</div>
              <div class="warning-content">
                <h4 class="warning-title">时间沙漏</h4>
                <p class="warning-message">
                  将当前带锁任务状态回退到30分钟前，撤销最近30分钟内的加减时、冻结等操作。
                </p>
                <p class="warning-note">
                  ⚠️ 使用后物品将被自动销毁，此操作不可撤销！
                </p>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeTimeHourglassModal" class="modal-btn secondary">
                取消
              </button>
              <button
                @click="useTimeHourglass"
                class="modal-btn primary"
                :disabled="usingTimeHourglass"
              >
                {{ usingTimeHourglass ? '使用中...' : '⏳ 使用时间沙漏' }}
              </button>
            </div>
          </div>

          <div v-else class="modal-body">
            <div class="hourglass-results-section">
              <h4 class="info-title">⏳ 时间回退结果</h4>

              <div class="hourglass-results-grid">
                <div class="hourglass-result-card">
                  <div class="result-header">
                    <span class="result-icon">🔄</span>
                    <span class="result-label">回退操作数</span>
                  </div>
                  <div class="result-content">{{ hourglassResults.reverted_events_count }}</div>
                </div>

                <div class="hourglass-result-card">
                  <div class="result-header">
                    <span class="result-icon">⏰</span>
                    <span class="result-label">新结束时间</span>
                  </div>
                  <div class="result-content">{{ hourglassResults.new_end_time ? formatDate(hourglassResults.new_end_time) : '无' }}</div>
                </div>

                <div v-if="hourglassResults.is_frozen" class="hourglass-result-card frozen">
                  <div class="result-header">
                    <span class="result-icon">❄️</span>
                    <span class="result-label">冻结状态</span>
                  </div>
                  <div class="result-content">任务已冻结</div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeTimeHourglassModal" class="modal-btn primary">
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

  <!-- Lucky Charm Modal -->
  <div v-if="showLuckyCharmModal" class="modal-overlay" @click.self="closeLuckyCharmModal">
    <div class="action-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">🍀 使用幸运符</h3>
        <button @click="closeLuckyCharmModal" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <div class="item-info">
          <p><strong>效果：</strong>下一个带锁任务的小时奖励概率+20%</p>
          <p><strong>说明：</strong>使用后立即生效，持续到下一个任务完成</p>
          <p class="warning">⚠️ 确认要使用幸运符吗？使用后道具将消失</p>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeLuckyCharmModal" class="modal-btn secondary">取消</button>
        <button
          @click="useLuckyCharm"
          :disabled="usingLuckyCharm"
          class="modal-btn primary"
        >
          <span v-if="usingLuckyCharm">使用中...</span>
          <span v-else>确认使用</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Energy Potion Modal -->
  <div v-if="showEnergyPotionModal" class="modal-overlay" @click.self="closeEnergyPotionModal">
    <div class="action-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">⚡ 使用活力药水</h3>
        <button @click="closeEnergyPotionModal" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <div class="item-info">
          <p><strong>效果：</strong>24小时内活跃度衰减减少50%</p>
          <p><strong>持续时间：</strong>24小时</p>
          <p class="warning">⚠️ 确认要使用活力药水吗？使用后道具将消失</p>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeEnergyPotionModal" class="modal-btn secondary">取消</button>
        <button
          @click="useEnergyPotion"
          :disabled="usingEnergyPotion"
          class="modal-btn primary"
        >
          <span v-if="usingEnergyPotion">使用中...</span>
          <span v-else>确认使用</span>
        </button>
      </div>
    </div>
  </div>


  <!-- Time Anchor Modal -->
  <div v-if="showTimeAnchorModal" class="modal-overlay" @click.self="closeTimeAnchorModal">
    <div class="action-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">⚓ 使用时间锚点</h3>
        <button @click="closeTimeAnchorModal" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <div class="warning-section">
          <div class="warning-icon">⚓</div>
          <div class="warning-content">
            <h4 class="warning-title">时间锚点</h4>
            <p class="warning-message">
              保存当前任务状态，如果任务失败可以恢复到保存点。
            </p>
            <p class="warning-note">
              使用后道具将被自动销毁，请谨慎使用！
            </p>
          </div>
        </div>

        <!-- Show saved state info if anchor has saved state -->
        <div v-if="timeAnchorHasSavedState" class="saved-state-info">
          <div class="info-header">
            <span class="info-icon">💾</span>
            <h4 class="info-title">已保存状态</h4>
          </div>
          <div class="saved-info-details">
            <p><strong>任务:</strong> {{ savedTaskInfo?.taskTitle || '未知任务' }}</p>
            <p><strong>保存状态:</strong> {{ savedTaskInfo?.savedStatus || '未知' }}</p>
            <p v-if="savedTaskInfo?.savedAt"><strong>保存时间:</strong> {{ formatDate(savedTaskInfo.savedAt) }}</p>
          </div>
        </div>

        <!-- Action selection - always allow save, show restore only if has saved state -->
        <div class="form-group">
          <label class="form-label">选择操作</label>
          <div class="radio-group">
            <label class="radio-option">
              <input v-model="timeAnchorAction" type="radio" value="save" />
              <span>{{ timeAnchorHasSavedState ? '重新保存任务状态' : '保存任务状态' }}</span>
            </label>
            <label v-if="timeAnchorHasSavedState" class="radio-option">
              <input v-model="timeAnchorAction" type="radio" value="restore" />
              <span>恢复任务状态</span>
            </label>
          </div>
        </div>

        <!-- Unified task selection for all cases -->
        <div class="form-group">
          <label class="form-label">选择任务</label>

          <div v-if="timeAnchorAction === 'save' && timeAnchorSaveTasks.length === 0" class="no-tasks-message">
            <p>暂无可保存的带锁任务</p>
            <p class="hint">只能保存自己的活跃状态或投票状态的带锁任务</p>
          </div>


          <!-- Task list for save operation -->
          <div v-if="timeAnchorAction === 'save' && timeAnchorSaveTasks.length > 0" class="tasks-list">
            <div
              v-for="task in timeAnchorSaveTasks"
              :key="task.id"
              class="task-item"
              :class="{ 'selected': selectedTimeAnchorTaskId === task.id }"
              @click="selectedTimeAnchorTaskId = task.id"
            >
              <div class="task-info">
                <h4 class="task-title">{{ task.title }}</h4>
                <p class="task-meta">
                  <span class="task-difficulty">{{ getDifficultyText(task.difficulty) }}</span>
                  <span class="task-status">{{ getStatusText(task.status) }}</span>
                </p>
                <p v-if="task.description" class="task-description">{{ stripHtmlAndTruncate(task.description, 120) }}</p>
              </div>
            </div>
          </div>

          <!-- Restore operation - show saved task info instead of task selection -->
          <div v-if="timeAnchorAction === 'restore'" class="restore-task-info">
            <div v-if="savedTaskCanBeRestored" class="saved-task-display">
              <h4 class="saved-task-title">将恢复以下任务状态：</h4>
              <div class="saved-task-card">
                <div class="task-info">
                  <h4 class="task-title">{{ savedTaskInfo?.taskTitle || '未知任务' }}</h4>
                  <p class="task-meta">
                    <span class="task-status failed">{{ savedTaskInfo?.savedStatus || '未知状态' }}</span>
                    <span class="saved-time">保存于: {{ savedTaskInfo?.savedAt ? formatDate(savedTaskInfo.savedAt) : '未知时间' }}</span>
                  </p>
                </div>
              </div>
            </div>

            <div v-else class="no-restore-available">
              <div class="warning-section">
                <div class="warning-icon">⚠️</div>
                <div class="warning-content">
                  <h4 class="warning-title">无法恢复</h4>
                  <p v-if="!timeAnchorHasSavedState" class="warning-message">
                    此时间锚点尚未保存任何任务状态
                  </p>
                  <p v-else-if="!savedTaskCanBeRestored" class="warning-message">
                    保存的任务"{{ savedTaskInfo?.taskTitle }}"尚未失败，无法恢复
                  </p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeTimeAnchorModal" class="modal-btn secondary">取消</button>
        <button
          @click="useTimeAnchor"
          :disabled="usingTimeAnchor || !selectedTimeAnchorTaskId || (timeAnchorAction === 'restore' && !savedTaskCanBeRestored)"
          class="modal-btn primary"
        >
          <span v-if="usingTimeAnchor">使用中...</span>
          <span v-else>{{ timeAnchorAction === 'save' ? '确认保存' : '确认恢复' }}</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Exploration Compass Modal -->
  <div v-if="showExplorationCompassModal" class="modal-overlay" @click.self="closeExplorationCompassModal">
    <div class="action-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">🧭 使用探索指南针</h3>
        <button @click="closeExplorationCompassModal" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <div class="item-info">
          <p><strong>效果：</strong>显示指定区域内所有已埋藏宝物的相关信息（物品类型、难度、埋藏者），但不显示具体位置</p>
          <div class="modal-form">
            <label>选择探索区域：</label>
            <select v-model="selectedCompassZone" class="form-select">
              <option value="">请选择区域</option>
              <option value="beach">🏖️ 月光海滩 (简单)</option>
              <option value="forest">🌲 神秘森林 (普通)</option>
              <option value="mountain">🏔️ 雾山 (困难)</option>
              <option value="desert">🏜️ 沙漠绿洲 (普通)</option>
              <option value="cave">🕳️ 深邃洞穴 (困难)</option>
            </select>
          </div>
          <p class="warning">⚠️ 确认要使用探索指南针吗？使用后道具将消失</p>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeExplorationCompassModal" class="modal-btn secondary">取消</button>
        <button
          @click="useExplorationCompass"
          :disabled="usingExplorationCompass || !selectedCompassZone"
          class="modal-btn primary"
        >
          <span v-if="usingExplorationCompass">使用中...</span>
          <span v-else>确认使用</span>
        </button>
      </div>
    </div>
  </div>


  <!-- Influence Crown Modal -->
  <div v-if="showInfluenceCrownModal" class="modal-overlay" @click.self="closeInfluenceCrownModal">
    <div class="action-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">👑 使用影响力皇冠</h3>
        <button @click="closeInfluenceCrownModal" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <div class="item-info">
          <p><strong>效果：</strong>48小时内，所有投票的权重变为3倍</p>
          <p><strong>持续时间：</strong>48小时</p>
          <p class="warning">⚠️ 确认要使用影响力皇冠吗？使用后道具将消失</p>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="closeInfluenceCrownModal" class="modal-btn secondary">取消</button>
        <button
          @click="useInfluenceCrown"
          :disabled="usingInfluenceCrown"
          class="modal-btn primary"
        >
          <span v-if="usingInfluenceCrown">使用中...</span>
          <span v-else>确认使用</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Small Campfire Modal -->
  <div v-if="showSmallCampfireModal" class="modal-overlay" @click.self="closeSmallCampfireModal">
    <div class="action-modal small-campfire-modal">
      <div class="modal-header">
        <h3 class="modal-title">🔥 使用小火堆</h3>
        <button @click="closeSmallCampfireModal" class="modal-close">×</button>
      </div>

      <div class="modal-body">
        <div class="warning-section">
          <div class="warning-icon">🔥</div>
          <div class="warning-content">
            <h4 class="warning-title">小火堆</h4>
            <p class="warning-message">
              可以解冻您自己的被冻结的带锁任务，让任务恢复倒计时。
            </p>
            <p class="warning-note">
              ⚠️ 使用后物品将被自动销毁，请谨慎使用！
            </p>
          </div>
        </div>

        <div class="form-group">
          <div v-if="frozenTasks.length === 0" class="no-tasks-message">
            <p>暂无被冻结的带锁任务</p>
            <p class="hint">只能解冻自己的已被冻结的带锁任务</p>
          </div>

          <div v-else-if="frozenTasks[0]" class="frozen-task-info">
            <h4 class="info-title">🧊 被冻结的任务</h4>
            <div class="task-display-card">
              <div class="task-info">
                <h4 class="task-title">{{ frozenTasks[0].title }}</h4>
                <p class="task-meta">
                  <span class="task-difficulty">{{ getDifficultyText(frozenTasks[0].difficulty) }}</span>
                  <span class="task-status frozen">❄️ 已冻结</span>
                </p>
                <p v-if="frozenTasks[0].description" class="task-description">
                  {{ stripHtmlAndTruncate(frozenTasks[0].description, 120) }}
                </p>
                <div v-if="frozenTasks[0].frozen_at" class="freeze-info">
                  <span class="freeze-time">冻结时间：{{ formatFreezeTime(frozenTasks[0].frozen_at) }}</span>
                </div>
              </div>
            </div>
            <p class="auto-select-note">
              💡 将自动解冻上述任务
            </p>
          </div>
        </div>

        <div v-if="selectedItem" class="item-info-section">
          <h4 class="info-title">🔥 使用物品</h4>
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
        <button @click="closeSmallCampfireModal" class="modal-btn secondary">取消</button>
        <button
          @click="useSmallCampfire"
          class="modal-btn primary"
          :disabled="frozenTasks.length === 0 || usingSmallCampfire"
        >
          <span v-if="usingSmallCampfire">使用中...</span>
          <span v-else>🔥 使用小火堆</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Exploration Compass Results Modal -->
  <div v-if="compassResults" class="modal-overlay" @click.self="compassResults = null">
    <div class="action-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">🧭 探索结果 - {{ compassResults.zone_display_name }}</h3>
        <button @click="compassResults = null" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <div class="item-info">
          <p><strong>探索区域：</strong>{{ compassResults.zone_display_name }}</p>
          <p><strong>发现宝物：</strong>{{ compassResults.treasure_count }} 个</p>
          <p><strong>使用时间：</strong>{{ new Date(compassResults.compass_used_at).toLocaleString() }}</p>
        </div>
        <div v-if="compassResults.treasures.length > 0">
          <h4>发现的宝物详情：</h4>
          <div v-for="treasure in compassResults.treasures" :key="treasure.treasure_id"
               :class="['detection-result-card', { 'own-treasure': treasure.is_own_treasure }]">
            <div class="treasure-info">
              <pre class="treasure-info-text">{{ treasure.treasure_info }}</pre>
              <p><strong>📅 埋藏时间：</strong>{{ new Date(treasure.buried_at).toLocaleString() }}</p>
              <p><strong>⏰ 到期时间：</strong>{{ new Date(treasure.expires_at).toLocaleString() }}</p>
              <div v-if="treasure.is_own_treasure" class="own-treasure-badge">
                <span class="badge-icon">🏠</span>
                <span class="badge-text">您的宝物</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="no-tasks-message">
          <p>该区域当前没有埋藏的宝物</p>
        </div>
      </div>
      <div class="modal-footer">
        <button @click="compassResults = null" class="modal-btn secondary">确定</button>
      </div>
    </div>
  </div>

  <!-- Notification Toast Display -->
  <div class="notification-container">
    <div
      v-for="notification in notifications"
      :key="notification.id"
      :class="['notification-toast', `notification-${notification.type}`]"
    >
      <div class="notification-content">
        <span class="notification-icon">
          {{ notification.type === 'success' ? '✅' :
             notification.type === 'error' ? '❌' :
             notification.type === 'warning' ? '⚠️' : 'ℹ️' }}
        </span>
        <span class="notification-message">{{ notification.message }}</span>
      </div>
      <button
        @click="removeNotification(notification.id)"
        class="notification-close"
      >
        ×
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../lib/api-commons'
import { storeApi, tasksApi } from '../lib/api'
import { tasksApi as tasksApiDetailed } from '../lib/api-tasks'
import { smartGoBack } from '../utils/navigation'
import { useAuthStore } from '../stores/auth'
import { useNotificationToast } from '../composables/NotificationToast'
import type { UserInventory, Item } from '../types'
import TreasuryItemModal from '../components/TreasuryItemModal.vue'
import NotificationToast from '../components/NotificationToast.vue'

// Router
const router = useRouter()

// Stores
const authStore = useAuthStore()

// Notification toast
const { showNotification, notifications, removeNotification } = useNotificationToast()

// Reactive data
const inventory = ref<UserInventory | null>(null)
const selectedItem = ref<Item | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const tasks = ref<any[]>([])
const availableTasks = ref<any[]>([])

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
const itemToBury = ref<Item | null>(null)
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

// Time Hourglass
const showTimeHourglassModal = ref(false)
const usingTimeHourglass = ref(false)
const hourglassResults = ref<any>(null)
const availableHourglassTasks = ref<any[]>([])

// Lucky Charm
const showLuckyCharmModal = ref(false)
const usingLuckyCharm = ref(false)

// Energy Potion
const showEnergyPotionModal = ref(false)
const usingEnergyPotion = ref(false)


// Time Anchor
const showTimeAnchorModal = ref(false)
const usingTimeAnchor = ref(false)
const timeAnchorAction = ref<'save' | 'restore'>('save')
const selectedTimeAnchorTaskId = ref('')

// Exploration Compass
const showExplorationCompassModal = ref(false)
const usingExplorationCompass = ref(false)
const selectedCompassZone = ref('')
const compassResults = ref<any>(null)


// Influence Crown
const showInfluenceCrownModal = ref(false)
const usingInfluenceCrown = ref(false)

// Small Campfire
const showSmallCampfireModal = ref(false)
const usingSmallCampfire = ref(false)
const frozenTasks = ref<Array<{
  id: string;
  title: string;
  description: string;
  difficulty: string;
  status: string;
  frozen_at?: string;
  frozen_end_time?: string;
  frozen_duration_seconds?: number;
  remaining_time_after_unfreeze_seconds?: number;
  start_time?: string;
  end_time?: string;
}>>([])
const selectedSmallCampfireTaskId = ref<string | null>(null)


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
  selectedItem.value = item
}

const getStatusText = (status: string): string => {
  const statusMap = {
    'available': '可用',
    'used': '已使用',
    'expired': '已过期',
    'in_drift_bottle': '漂流中',
    'buried': '已掩埋',
    'in_game': '预留奖品'
  }
  return statusMap[status as keyof typeof statusMap] || status
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const formatFreezeTime = (dateString: string): string => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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
  return item.status === 'available' && [
    'photo', 'note', 'key', 'little_treasury', 'time_hourglass',
    'lucky_charm', 'energy_potion', 'time_anchor',
    'exploration_compass', 'influence_crown', 'small_campfire'
  ].includes(item.item_type.name)
}

const canBuryItem = (item: Item): boolean => {
  return item.status === 'available' && [
    'photo', 'key', 'note', 'little_treasury', 'detection_radar', 'photo_paper',
    'blizzard_bottle', 'sun_bottle', 'time_hourglass',
    'lucky_charm', 'energy_potion', 'time_anchor', 'exploration_compass', 'influence_crown', 'small_campfire'
  ].includes(item.item_type.name)
}

const canShareNewItem = (item: Item): boolean => {
  if (item.status !== 'available') return false
  const shareableTypes = ['lucky_charm', 'energy_potion', 'time_anchor', 'exploration_compass', 'influence_crown', 'small_campfire']
  return shareableTypes.includes(item.item_type.name)
}

const canBuryNewItem = (item: Item): boolean => {
  if (item.status !== 'available') return false
  const buryableTypes = ['lucky_charm', 'energy_potion', 'time_anchor', 'exploration_compass', 'influence_crown', 'small_campfire']
  return buryableTypes.includes(item.item_type.name)
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

const canUseTimeHourglass = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'time_hourglass'
}


// Tasks for Time Anchor (save)
const timeAnchorSaveTasks = computed(() => {
  if (!tasks.value) return []
  return tasks.value.filter((task: any) =>
    task.task_type === 'lock' &&
    ['active', 'voting', 'voting_passed'].includes(task.status)
  ).map((task: any) => ({
    id: task.id,
    title: task.title,
    status: task.status,
    difficulty: task.difficulty,
    description: task.description
  }))
})

// Tasks for Time Anchor (restore)
const timeAnchorRestoreTasks = computed(() => {
  if (!tasks.value) return []
  return tasks.value.filter((task: any) =>
    task.task_type === 'lock' &&
    task.status === 'failed'
  ).map((task: any) => ({
    id: task.id,
    title: task.title,
    status: task.status,
    difficulty: task.difficulty,
    description: task.description
  }))
})


const canUseLuckyCharm = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'lucky_charm'
}

const canUseEnergyPotion = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'energy_potion'
}


const canUseTimeAnchor = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'time_anchor'
}

// Check if Time Anchor has saved state
const timeAnchorHasSavedState = computed(() => {
  if (!selectedItem.value || selectedItem.value.item_type.name !== 'time_anchor') {
    return false
  }
  // Check if the item has saved state in properties
  return selectedItem.value.properties?.has_saved_state === true ||
         selectedItem.value.properties?.saved_task_id ||
         selectedItem.value.properties?.saved_status
})

// Get the saved task info if available
const savedTaskInfo = computed(() => {
  if (!selectedItem.value || selectedItem.value.item_type.name !== 'time_anchor') {
    return null
  }
  return {
    taskId: selectedItem.value.properties?.saved_task_id,
    taskTitle: selectedItem.value.properties?.saved_task_title,
    savedStatus: selectedItem.value.properties?.saved_status,
    savedAt: selectedItem.value.properties?.saved_at
  }
})

// Check if the saved task can be restored (task exists and is failed)
const savedTaskCanBeRestored = computed(() => {
  if (!timeAnchorHasSavedState.value || !savedTaskInfo.value?.taskId) {
    return false
  }

  // Check if the saved task exists in the failed tasks list
  const savedTask = timeAnchorRestoreTasks.value.find(
    task => task.id === savedTaskInfo.value?.taskId
  )

  return savedTask && savedTask.status === 'failed'
})

const canUseExplorationCompass = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'exploration_compass'
}


const canUseInfluenceCrown = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'influence_crown'
}

const canUseSmallCampfire = (item: Item): boolean => {
  return item.status === 'available' && item.item_type.name === 'small_campfire'
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
  if (!itemToBury.value || !buryData.value.location_zone || !buryData.value.location_hint.trim()) return

  try {
    buryingItem.value = true
    await storeApi.buryItem({
      item_id: itemToBury.value.id,
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
  itemToBury.value = null
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
    showNotification(`${response.message}\n获得奖励：${response.reward_coins} 积分`, 'success')

  } catch (err) {    
    error.value = err instanceof Error ? err.message : '使用万能钥匙失败'
  } finally {
    // Close modal and reset selection
    closeUniversalKeyModal()
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

// Unified item action handler to fix modal closing and opening issues
const handleItemAction = async (action: string, item: Item | null) => {
  if (!item) return

  // 1. Immediately close toast by clearing selectedItem
  selectedItem.value = null

  // 2. Wait for DOM update to ensure toast is fully closed
  await nextTick()

  // 3. Small delay to ensure Transition animations complete
  await new Promise(resolve => setTimeout(resolve, 50))

  // 4. Open the corresponding modal based on action type
  switch (action) {
    case 'treasury':
      selectedTreasuryItem.value = item
      showTreasuryModal.value = true
      break
    case 'universal_key':
      showUniversalKeyModal.value = true
      await loadAvailableTasks()
      break
    case 'detection_radar':
      showDetectionRadarModal.value = true
      break
    case 'blizzard_bottle':
      showBlizzardBottleModal.value = true
      break
    case 'sun_bottle':
      showSunBottleModal.value = true
      break
    case 'time_hourglass':
      showTimeHourglassModal.value = true
      break
    case 'lucky_charm':
      showLuckyCharmModal.value = true
      break
    case 'energy_potion':
      showEnergyPotionModal.value = true
      break
    case 'time_anchor':
      showTimeAnchorModal.value = true
      break
    case 'exploration_compass':
      showExplorationCompassModal.value = true
      break
    case 'influence_crown':
      showInfluenceCrownModal.value = true
      break
    case 'small_campfire':
      showSmallCampfireModal.value = true
      break
    case 'note_edit':
      // Load existing content if available
      noteContent.value = item.properties?.content || ''
      showNoteEditModal.value = true
      break
    case 'note_view':
      showNoteViewModal.value = true
      // viewNote needs selectedItem to be set, so temporarily set it
      selectedItem.value = item
      viewNote()
      // Clear selectedItem after viewNote is called
      selectedItem.value = null
      break
    case 'photo_view':
      viewPhoto(item)
      break
    case 'share':
      // shareItem needs selectedItem to be set, so temporarily set it
      selectedItem.value = item
      await shareItem()
      break
    case 'bury':
      itemToBury.value = item
      showBuryModal.value = true
      break
    case 'discard':
      showDiscardModal.value = true
      break
    default:
      console.warn('Unknown action:', action)
  }
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
      showNotification('您没有时间被隐藏的带锁任务', 'warning')
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
    let errorMessage = '使用探测雷达失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
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
    let errorMessage = '使用暴雪瓶失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
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
    let errorMessage = '使用太阳瓶失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingSunBottle.value = false
  }
}

// Time Hourglass functions
const openTimeHourglassModal = () => {
  if (!selectedItem.value) return
  showTimeHourglassModal.value = true
}

const closeTimeHourglassModal = () => {
  showTimeHourglassModal.value = false
  hourglassResults.value = null
  selectedItem.value = null
}

const useTimeHourglass = async () => {
  if (!selectedItem.value) return

  try {
    usingTimeHourglass.value = true

    // Get user's active lock task
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

    if (allTasks.length === 0) {
      showNotification('您当前没有活跃的带锁任务', 'warning')
      return
    }

    // For simplicity, use the first active task
    // In a more complete implementation, you might show a task selection modal
    const targetTask = allTasks[0]

    // Call the time hourglass API
    const response = await tasksApiDetailed.useTimeHourglass(targetTask.id)

    // Set the hourglass results from the API response
    hourglassResults.value = {
      reverted_events_count: response.rollback_data.reverted_events_count,
      new_end_time: response.rollback_data.new_end_time,
      is_frozen: response.rollback_data.is_frozen,
      rollback_id: response.rollback_data.rollback_id
    }

    // Refresh inventory after successful use (item should be destroyed)
    await loadInventory()

    // Clear selected item since it was destroyed
    selectedItem.value = null

  } catch (error) {
    console.error('Error using time hourglass:', error)
    let errorMessage = '使用时间沙漏失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingTimeHourglass.value = false
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
    let errorMessage = '编辑纸条失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
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

// Lucky Charm Modal Functions
const openLuckyCharmModal = () => {
  if (!selectedItem.value) return
  showLuckyCharmModal.value = true
}

const closeLuckyCharmModal = () => {
  showLuckyCharmModal.value = false
  selectedItem.value = null
}

const useLuckyCharm = async () => {
  if (!selectedItem.value) return

  try {
    usingLuckyCharm.value = true
    const response = await storeApi.useLuckyCharm(selectedItem.value.id)

    // Refresh inventory after successful use
    await loadInventory()

    // Show success message
    showNotification(`${response.message}`, 'success')

    // Close modal and reset selection
    closeLuckyCharmModal()
  } catch (error) {
    console.error('Error using lucky charm:', error)
    let errorMessage = '使用幸运符失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingLuckyCharm.value = false
  }
}

// Energy Potion Modal Functions
const openEnergyPotionModal = () => {
  if (!selectedItem.value) return
  showEnergyPotionModal.value = true
}

const closeEnergyPotionModal = () => {
  showEnergyPotionModal.value = false
  selectedItem.value = null
}

const useEnergyPotion = async () => {
  if (!selectedItem.value) return

  try {
    usingEnergyPotion.value = true
    const response = await storeApi.useEnergyPotion(selectedItem.value.id)

    // Refresh inventory after successful use
    await loadInventory()

    // Show success message
    showNotification(`${response.message}`, 'success')

    // Close modal and reset selection
    closeEnergyPotionModal()
  } catch (error) {
    console.error('Error using energy potion:', error)

    let errorMessage = '使用活力药水失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    } else if (error && typeof error === 'object' && 'message' in error && typeof error.message === 'string') {
      errorMessage = error.message
    }

    console.log('Showing notification with message:', errorMessage)
    showNotification(errorMessage, 'error')
  } finally {
    usingEnergyPotion.value = false
  }
}


// Time Anchor Modal Functions
const openTimeAnchorModal = async () => {
  if (!selectedItem.value) return
  // Load tasks before showing modal
  if (tasks.value.length === 0) {
    try {
      // Load tasks with all relevant statuses including failed tasks for restore
      const activeTasks = await tasksApi.getTasksList({
        task_type: 'lock',
        status: 'active',
        my_tasks: true
      })
      const votingTasks = await tasksApi.getTasksList({
        task_type: 'lock',
        status: 'voting',
        my_tasks: true
      })
      const votingPassedTasks = await tasksApi.getTasksList({
        task_type: 'lock',
        status: 'voting_passed',
        my_tasks: true
      })
      const failedTasks = await tasksApi.getTasksList({
        task_type: 'lock',
        status: 'failed',
        my_tasks: true
      })
      tasks.value = [...activeTasks, ...votingTasks, ...votingPassedTasks, ...failedTasks]

      // Auto-select the first available task when modal opens
      if (timeAnchorSaveTasks.value.length > 0 && timeAnchorSaveTasks.value[0]) {
        selectedTimeAnchorTaskId.value = timeAnchorSaveTasks.value[0].id
      }
    } catch (err) {
      console.error('Failed to load tasks for time anchor:', err)
    }
  } else {
    // Auto-select the first available task if tasks are already loaded
    if (timeAnchorSaveTasks.value.length > 0 && timeAnchorSaveTasks.value[0]) {
      selectedTimeAnchorTaskId.value = timeAnchorSaveTasks.value[0].id
    }
  }
  // Set default action: always default to save for consistency
  timeAnchorAction.value = 'save'

  // If has saved state and want to restore, user can manually select
  // Auto-select the saved task if it can be restored and user chooses restore
  if (timeAnchorHasSavedState.value && savedTaskCanBeRestored.value && savedTaskInfo.value?.taskId) {
    // Don't auto-select restore, let user choose
    // selectedTimeAnchorTaskId.value = savedTaskInfo.value.taskId
  }

  showTimeAnchorModal.value = true
}

const closeTimeAnchorModal = () => {
  showTimeAnchorModal.value = false
  timeAnchorAction.value = 'save'
  selectedTimeAnchorTaskId.value = ''
  selectedItem.value = null
}

const useTimeAnchor = async () => {
  if (!selectedItem.value || !selectedTimeAnchorTaskId.value) return

  // Validation: Check if user has active locked task when trying to restore
  if (timeAnchorAction.value === 'restore') {
    try {
      // Check for active locked task
      const activeLockTask = await tasksApi.getActiveLockTask()
      if (activeLockTask) {
        showNotification('无法恢复任务：您当前有活跃的带锁任务。请先完成或停止当前任务后再恢复。', 'error')
        return
      }
    } catch (error) {
      console.error('Error checking active lock task:', error)
      showNotification('检查任务状态时发生错误，请重试', 'error')
      return
    }
  }

  try {
    usingTimeAnchor.value = true

    // For restore operations, check if key exists and request recreation if necessary
    let needsKeyRecreation = false
    if (timeAnchorAction.value === 'restore') {
      try {
        const keyOwnership = await storeApi.getTaskKeyHolder(selectedTimeAnchorTaskId.value)

        // If key doesn't exist (destroyed when task failed), request backend to recreate it
        if (!keyOwnership.has_key) {
          console.log('Key does not exist, requesting recreation during restore...')
          needsKeyRecreation = true
        }
      } catch (keyError) {
        console.warn('Failed to check key ownership:', keyError)
      }
    }

    const response = await storeApi.useTimeAnchor({
      item_id: selectedItem.value.id,
      task_id: selectedTimeAnchorTaskId.value,
      action: timeAnchorAction.value,
      recreate_key: needsKeyRecreation
    })

    // Wait for backend processing
    await new Promise(resolve => setTimeout(resolve, 1000))

    // Refresh inventory after successful use
    await loadInventory()

    // Show success message
    showNotification(`${response.message}`, 'success')

    // Handle key return for restore operations
    if (timeAnchorAction.value === 'restore') {
      // Check if key was successfully returned/recreated
      const updatedInventory = await storeApi.getUserInventory()
      const taskKey = updatedInventory.items?.find(item =>
        item.item_type.name === 'key' &&
        item.properties?.task_id === selectedTimeAnchorTaskId.value
      )

      if (taskKey) {
        // Determine appropriate message based on whether key was recreated or returned
        let keyMessage = response.key_return_message || '任务已恢复，对应的任务钥匙已返还到背包'

        if (response.key_recreated) {
          keyMessage = '任务已恢复，原钥匙已重新创建并返还到背包'
        } else if (needsKeyRecreation) {
          keyMessage = '任务已恢复，钥匙已重新创建并返还到背包'
        }

        showNotification(keyMessage, 'success')
      } else {
        // If key still not found, show appropriate message
        const keyOwnership = await storeApi.getTaskKeyHolder(selectedTimeAnchorTaskId.value)

        if (!keyOwnership.has_key) {
          if (needsKeyRecreation) {
            showNotification('任务已恢复，但钥匙重新创建失败。请联系管理员处理。', 'error')
          } else {
            showNotification('任务已恢复，但原钥匙已被销毁。请联系管理员重新创建钥匙。', 'warning')
          }
        } else {
          showNotification('任务已恢复，但钥匙返还可能需要稍等片刻。', 'info')
        }
      }
    }

    // Close modal and reset selection
    closeTimeAnchorModal()
  } catch (error) {
    console.error('Error using time anchor:', error)
    let errorMessage = '使用时间锚点失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingTimeAnchor.value = false
  }
}

// Exploration Compass Modal Functions
const openExplorationCompassModal = () => {
  if (!selectedItem.value) return
  showExplorationCompassModal.value = true
}

const closeExplorationCompassModal = () => {
  showExplorationCompassModal.value = false
  selectedCompassZone.value = ''
  compassResults.value = null
  selectedItem.value = null
}

const useExplorationCompass = async () => {
  if (!selectedItem.value || !selectedCompassZone.value) return

  try {
    usingExplorationCompass.value = true
    const response = await storeApi.useExplorationCompass({
      item_id: selectedItem.value.id,
      zone_name: selectedCompassZone.value
    })

    // Set compass results from API response
    compassResults.value = {
      zone_name: response.zone_name,
      zone_display_name: response.zone_display_name,
      treasures: response.treasures,
      treasure_count: response.treasure_count,
      compass_used_at: response.compass_used_at
    }

    // Refresh inventory after successful use
    await loadInventory()

    // Show success message
    showNotification(`${response.message}`, 'success')

    // Close modal but keep results displayed
    showExplorationCompassModal.value = false
  } catch (error) {
    console.error('Error using exploration compass:', error)
    let errorMessage = '使用探索指南针失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingExplorationCompass.value = false
  }
}


// Influence Crown Modal Functions
const openInfluenceCrownModal = () => {
  if (!selectedItem.value) return
  showInfluenceCrownModal.value = true
}

const closeInfluenceCrownModal = () => {
  showInfluenceCrownModal.value = false
  selectedItem.value = null
}

const useInfluenceCrown = async () => {
  if (!selectedItem.value) return

  try {
    usingInfluenceCrown.value = true
    const response = await storeApi.useInfluenceCrown(selectedItem.value.id)

    // Refresh inventory after successful use
    await loadInventory()

    // Show success message
    showNotification(`${response.message}`, 'success')

    // Close modal and reset selection
    closeInfluenceCrownModal()
  } catch (error) {
    console.error('Error using influence crown:', error)
    let errorMessage = '使用影响力皇冠失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingInfluenceCrown.value = false
  }
}

// Small Campfire Modal Functions
const openSmallCampfireModal = async () => {
  if (!selectedItem.value) return

  try {
    // Load frozen tasks when opening the modal
    const response = await storeApi.getFrozenTasks()
    frozenTasks.value = response.frozen_tasks || []

    // Auto-select the first (and only) frozen task if available
    if (frozenTasks.value.length > 0 && frozenTasks.value[0]) {
      selectedSmallCampfireTaskId.value = frozenTasks.value[0].id
    }

    showSmallCampfireModal.value = true
  } catch (error) {
    console.error('Error loading frozen tasks:', error)
    showNotification('加载冻结任务失败，请重试', 'error')
  }
}

const closeSmallCampfireModal = () => {
  showSmallCampfireModal.value = false
  selectedSmallCampfireTaskId.value = null
  frozenTasks.value = []
  if (selectedItem.value) {
    selectedItem.value = null
  }
}

const useSmallCampfire = async () => {
  if (!selectedItem.value || !selectedSmallCampfireTaskId.value) return

  try {
    usingSmallCampfire.value = true
    const response = await storeApi.useSmallCampfireOnTask({
      item_id: selectedItem.value.id,
      task_id: selectedSmallCampfireTaskId.value
    })

    // Refresh inventory after successful use
    await loadInventory()

    // Show success message
    showNotification(`${response.message}`, 'success')

    // Close modal and reset selection
    closeSmallCampfireModal()
  } catch (error) {
    console.error('Error using small campfire:', error)
    let errorMessage = '使用小火堆失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
  } finally {
    usingSmallCampfire.value = false
  }
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
    let errorMessage = '查看纸条失败，请重试'
    if (error instanceof ApiError) {
      errorMessage = error.message
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    showNotification(errorMessage, 'error')
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


// Watch for timeAnchorAction changes to auto-select tasks
watch(timeAnchorAction, (newAction) => {
  if (newAction === 'save' && timeAnchorSaveTasks.value.length > 0 && timeAnchorSaveTasks.value[0]) {
    selectedTimeAnchorTaskId.value = timeAnchorSaveTasks.value[0].id
  } else if (newAction === 'restore') {
    // For restore, only allow the saved task if it can be restored
    if (timeAnchorHasSavedState.value && savedTaskCanBeRestored.value && savedTaskInfo.value?.taskId) {
      selectedTimeAnchorTaskId.value = savedTaskInfo.value.taskId
    } else {
      // No valid restore target available
      selectedTimeAnchorTaskId.value = ''
    }
  } else {
    selectedTimeAnchorTaskId.value = ''
  }
})

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

/* Overflow info slot */
.inventory-slot.overflow-info {
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 3px solid #856404;
  box-shadow: 4px 4px 0 #856404;
  grid-column: 1 / -1; /* 占满整行 */
}

.inventory-slot.overflow-info .slot-content {
  flex-direction: row;
  justify-content: center;
  gap: 1rem;
  padding: 1rem;
}

.overflow-icon {
  font-size: 1.5rem;
}

.overflow-text {
  font-weight: 900;
  font-size: 1rem;
  color: #856404;
  text-transform: uppercase;
}

.overflow-count {
  font-weight: 700;
  font-size: 0.875rem;
  color: #dc3545;
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

/* In-game items special styling */
.inventory-slot.occupied.in-game {
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border-color: #f39c12;
  box-shadow: 4px 4px 0 #e67e22;
}

.inventory-slot.occupied.in-game .item-status {
  color: #d68910;
  font-weight: 900;
  background: rgba(211, 84, 0, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #d35400;
}

.inventory-slot.occupied.in-game .item-icon {
  opacity: 0.8;
  filter: sepia(0.3) hue-rotate(30deg);
}

/* In-game notice styling */
.in-game-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-top: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 3px solid #f39c12;
  border-radius: 6px;
  box-shadow: 4px 4px 0 #e67e22;
}

.notice-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.notice-content {
  flex: 1;
}

.notice-title {
  font-size: 0.875rem;
  font-weight: 900;
  color: #d68910;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.5rem 0;
}

.notice-text {
  font-size: 0.75rem;
  color: #b7950b;
  line-height: 1.4;
  margin: 0;
  font-weight: 600;
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
  /* Mobile optimizations */
  touch-action: manipulation;
  user-select: none;
  -webkit-user-select: none;
  -webkit-tap-highlight-color: transparent;
  position: relative;
  z-index: 1;
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

.action-btn:active {
  transform: translate(3px, 3px);
  box-shadow: 1px 1px 0 #000;
}

/* Item Toast Content Styles */
.item-toast-content {
  text-align: left;
}

.item-toast-content .item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.item-toast-content .meta-item {
  display: flex;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.875rem;
}

.item-toast-content .meta-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
}

.item-toast-content .meta-value {
  font-weight: 700;
  color: #000;
}

.item-toast-content .owner-link {
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

.item-toast-content .owner-link:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
  background: #138496;
}

.item-toast-content .no-owner {
  color: #999;
  font-style: italic;
  font-weight: 600;
}

.item-toast-content .in-game-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin: 0.5rem 0;
  padding: 0.75rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 3px solid #f39c12;
  border-radius: 6px;
  box-shadow: 4px 4px 0 #e67e22;
}

.item-toast-content .notice-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.item-toast-content .notice-content {
  flex: 1;
}

.item-toast-content .notice-title {
  font-size: 0.8rem;
  font-weight: 900;
  color: #d68910;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.25rem 0;
}

.item-toast-content .notice-text {
  font-size: 0.8rem;
  color: #856404;
  margin: 0;
  line-height: 1.4;
}

.item-toast-content .properties-section {
  margin-top: 1rem;
}

.item-toast-content .properties-title {
  font-size: 0.9rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.item-toast-content .properties-content {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 0.75rem;
}

.item-toast-content .properties-json {
  font-family: 'Courier New', monospace;
  font-size: 0.7rem;
  margin: 0;
  white-space: pre-wrap;
  color: #333;
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
}

/* New Item Modal Styles */
.lucky-charm-modal {
  .modal-content {
    max-width: 500px;
    background: linear-gradient(135deg, #4CAF50, #45a049);
    border: 2px solid #4CAF50;
  }

  .modal-header {
    background: linear-gradient(135deg, #45a049, #4CAF50);
    color: white;
  }

  .item-info {
    p {
      margin: 8px 0;

      strong {
        color: #2e7d32;
      }
    }
  }
}

.energy-potion-modal {
  .modal-content {
    max-width: 500px;
    background: linear-gradient(135deg, #FF9800, #F57C00);
    border: 2px solid #FF9800;
  }

  .modal-header {
    background: linear-gradient(135deg, #F57C00, #FF9800);
    color: white;
  }

  .item-info {
    p {
      margin: 8px 0;

      strong {
        color: #e65100;
      }
    }
  }
}

.friendship-bridge-modal {
  .modal-content {
    max-width: 550px;
    background: linear-gradient(135deg, #2196F3, #1976D2);
    border: 2px solid #2196F3;
  }

  .modal-header {
    background: linear-gradient(135deg, #1976D2, #2196F3);
    color: white;
  }

  .form-group {
    margin: 15px 0;

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #333;
    }

    .form-input,
    .form-select {
      width: 100%;
      padding: 10px;
      border: 2px solid #ddd;
      border-radius: 8px;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: #2196F3;
        box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.2);
      }
    }

    .radio-group {
      display: flex;
      gap: 15px;

      .radio-option {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;

        input[type="radio"] {
          margin: 0;
        }
      }
    }
  }
}

.time-anchor-modal {
  .modal-content {
    max-width: 550px;
    background: linear-gradient(135deg, #6F42C1, #5B21B6);
    border: 2px solid #6F42C1;
  }

  .modal-header {
    background: linear-gradient(135deg, #5B21B6, #6F42C1);
    color: white;
  }

  .form-group {
    margin: 15px 0;

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #333;
    }

    .form-input,
    .form-select {
      width: 100%;
      padding: 10px;
      border: 2px solid #ddd;
      border-radius: 8px;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: #6F42C1;
        box-shadow: 0 0 0 3px rgba(107, 66, 193, 0.2);
      }
    }

    .radio-group {
      display: flex;
      gap: 15px;

      .radio-option {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;

        input[type="radio"] {
          margin: 0;
        }
      }
    }
  }
}

.exploration-compass-modal {
  .modal-content {
    max-width: 600px;
    background: linear-gradient(135deg, #17A2B8, #138756);
    border: 2px solid #17A2B8;
  }

  .modal-header {
    background: linear-gradient(135deg, #138756, #17A2B8);
    color: white;
  }

  .form-group {
    margin: 15px 0;

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #333;
    }

    .form-select {
      width: 100%;
      padding: 10px;
      border: 2px solid #ddd;
      border-radius: 8px;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: #17A2B8;
        box-shadow: 0 0 0 3px rgba(23, 162, 184, 0.2);
      }
    }
  }
}

.spacetime-gate-modal {
  .modal-content {
    max-width: 550px;
    background: linear-gradient(135deg, #6F42C1, #5B21B6);
    border: 2px solid #6F42C1;
  }

  .modal-header {
    background: linear-gradient(135deg, #5B21B6, #6F42C1);
    color: white;
  }

  .form-group {
    margin: 15px 0;

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #333;
    }

    .form-select {
      width: 100%;
      padding: 10px;
      border: 2px solid #ddd;
      border-radius: 8px;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: #6F42C1;
        box-shadow: 0 0 0 3px rgba(107, 66, 193, 0.2);
      }
    }
  }
}

.influence-crown-modal {
  .modal-content {
    max-width: 500px;
    background: linear-gradient(135deg, #FFD700, #FFA500);
    border: 2px solid #FFD700;
  }

  .modal-header {
    background: linear-gradient(135deg, #FFA500, #FFD700);
    color: white;
  }

  .item-info {
    p {
      margin: 8px 0;

      strong {
        color: #c58000;
      }
    }
  }
}

.compass-results-modal {
  .modal-content {
    max-width: 700px;
    max-height: 80vh;
    overflow-y: auto;
    background: linear-gradient(135deg, #17A2B8, #138756);
    border: 2px solid #17A2B8;
  }

  .modal-header {
    background: linear-gradient(135deg, #138756, #17A2B8);
    color: white;
  }

  .compass-summary {
    background: rgba(255, 255, 255, 0.1);
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;

    p {
      margin: 8px 0;

      strong {
        color: #138756;
      }
    }
  }

  .treasures-list {
    max-height: 400px;
    overflow-y: auto;

    .treasure-item {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 15px;
      margin-bottom: 10px;

      .treasure-info {
        p {
          margin: 5px 0;
          font-size: 13px;

          strong {
            color: #17A2B8;
          }
        }

        .treasure-info-text {
          background: #f8f9fa;
          border: 1px solid #dee2e6;
          border-radius: 4px;
          padding: 10px;
          margin: 10px 0;
          font-family: inherit;
          font-size: 13px;
          white-space: pre-line;
          color: #495057;
          line-height: 1.4;
        }

        .own-treasure-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: #e3f2fd;
          color: #1565c0;
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
          margin-top: 8px;
          border: 1px solid #bbdefb;

          .badge-icon {
            font-size: 12px;
          }

          .badge-text {
            font-weight: 600;
          }
        }
      }
    }

    &.own-treasure {
      background: #f8f9fa;
      border-color: #17a2b8;
      box-shadow: 3px 3px 0 #17a2b8;

      &:hover {
        box-shadow: 4px 4px 0 #17a2b8;
      }
    }
  }

  .no-treasures {
    text-align: center;
    padding: 20px;
    color: #666;
    font-style: italic;
  }
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

.task-duration {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.25rem 0.5rem;
  border: 2px solid #000;
  background: white;
  color: #000;
}

.task-duration.valid {
  background: #d4edda;
  color: #155724;
  border-color: #28a745;
}

.task-duration.invalid {
  background: #f8d7da;
  color: #721c24;
  border-color: #dc3545;
}

.task-item.selected .task-difficulty,
.task-item.selected .task-status,
.task-item.selected .task-duration {
  background: #cce7ff;
  color: #000;
}

.task-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.task-item.disabled:hover {
  transform: none;
  box-shadow: 4px 4px 0 #000;
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

/* Time Hourglass Modal Styles */
.time-hourglass-modal {
  max-width: 600px;
  width: 100%;
}

.hourglass-results-section {
  background: #f0f8ff;
  border: 3px solid #4682b4;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #4682b4;
}

.hourglass-results-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.hourglass-result-card {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.hourglass-result-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.hourglass-result-card.frozen {
  background: #e1f5fe;
  border-color: #17a2b8;
  box-shadow: 3px 3px 0 #17a2b8;
}

.hourglass-result-card.frozen:hover {
  box-shadow: 4px 4px 0 #17a2b8;
}

.action-btn.hourglass {
  background: #4682b4;
  color: white;
  border-color: #000;
}

.action-btn.hourglass:hover {
  background: #36648b;
  color: white;
}

/* Responsive Design for Time Hourglass */
@media (max-width: 768px) {
  .time-hourglass-modal {
    margin: 1rem;
    max-width: calc(100vw - 2rem);
  }

  .hourglass-results-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .hourglass-result-card {
    padding: 0.75rem;
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

/* Exclusive Task Styles */
.action-btn.exclusive-task-btn {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  color: white;
  border: 3px solid #000;
  font-weight: bold;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #ee5a52, #dc3545);
    transform: translateY(-2px);
  }

  &:disabled {
    background: #ccc;
    cursor: not-allowed;
  }
}

.exclusive-task-modal {
  background: #fff;
  border: 4px solid #000;
  border-radius: 0;
  box-shadow: 8px 8px 0 rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;

  .modal-header {
    background: #ff6b6b;
    color: white;
    padding: 1rem;
    border-bottom: 3px solid #000;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .modal-title {
      margin: 0;
      font-size: 1.25rem;
      font-weight: bold;
    }

    .close-btn {
      background: none;
      border: none;
      color: white;
      font-size: 1.5rem;
      cursor: pointer;
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50%;
      }
    }
  }

  .modal-body {
    padding: 1.5rem;
  }

  .task-info-section {
    background: #f8f9fa;
    border: 2px solid #000;
    padding: 1rem;
    margin-bottom: 1.5rem;

    .info-text {
      margin: 0 0 0.5rem 0;
      font-size: 1rem;
    }

    .cost-info, .reward-info {
      margin: 0.25rem 0;
      font-size: 0.9rem;
    }

    .cost-amount, .reward-amount {
      color: #ff6b6b;
      font-weight: bold;
    }
  }

  .task-form {
    .form-group {
      margin-bottom: 1rem;

      .form-label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: bold;
        color: #333;
      }

      .form-input, .form-textarea, .form-select {
        width: 100%;
        padding: 0.75rem;
        border: 2px solid #000;
        border-radius: 0;
        font-size: 1rem;
        background: white;

        &:focus {
          outline: none;
          border-color: #ff6b6b;
          box-shadow: 0 0 0 2px rgba(255, 107, 107, 0.2);
        }
      }

      .form-textarea {
        resize: vertical;
        min-height: 100px;
      }
    }

    .form-actions {
      display: flex;
      gap: 1rem;
      margin-top: 1.5rem;

      .cancel-btn, .submit-btn {
        flex: 1;
        padding: 0.75rem 1.5rem;
        border: 2px solid #000;
        border-radius: 0;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.2s ease;

        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }

      .cancel-btn {
        background: white;
        color: #333;

        &:hover:not(:disabled) {
          background: #f8f9fa;
          transform: translateY(-1px);
        }
      }

      .submit-btn {
        background: #ff6b6b;
        color: white;

        &:hover:not(:disabled) {
          background: #ee5a52;
          transform: translateY(-1px);
        }
      }
    }
  }
}

/* Mobile responsive for exclusive task modal */
@media (max-width: 768px) {
  .exclusive-task-modal {
    width: 95%;
    margin: 1rem;
    max-height: 90vh;

    .modal-body {
      padding: 1rem;
    }

    .task-info-section {
      padding: 0.75rem;
      margin-bottom: 1rem;
    }

    .form-actions {
      flex-direction: column;
      gap: 0.75rem;

      .cancel-btn, .submit-btn {
        padding: 0.75rem;
      }
    }
  }
}

/* Time Anchor Saved State Styles */
.saved-state-info {
  background: linear-gradient(135deg, #e8f5e8, #f0f8f0);
  border: 3px solid #28a745;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #28a745;
  border-radius: 6px;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.info-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.info-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #155724;
}

.saved-info-details {
  margin-bottom: 1rem;
}

.saved-info-details p {
  margin: 0.5rem 0;
  font-size: 0.875rem;
  color: #155724;
  font-weight: 600;
}

.saved-info-details strong {
  color: #0d4419;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-note {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.7);
  padding: 0.75rem;
  border: 2px solid #28a745;
  border-radius: 4px;
}

.note-icon {
  font-size: 1rem;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.note-text {
  font-size: 0.75rem;
  font-weight: 700;
  color: #155724;
  line-height: 1.4;
}

.restore-ready {
  background: #d4edda;
  color: #155724;
  padding: 0.25rem 0.5rem;
  border: 2px solid #28a745;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.7rem;
  border-radius: 3px;
}

/* Mobile responsive for saved state info */
@media (max-width: 768px) {
  .saved-state-info {
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .info-header {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .info-title {
    font-size: 1rem;
  }

  .saved-info-details p {
    font-size: 0.8rem;
  }

  .info-note {
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.5rem;
    text-align: center;
  }

  .note-text {
    font-size: 0.7rem;
  }
}

/* Time Anchor Restore Task Info Styles */
.restore-task-info {
  margin-top: 1rem;
}

.saved-task-display {
  background: linear-gradient(135deg, #e8f5e8, #f0f8f0);
  border: 3px solid #28a745;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #28a745;
  border-radius: 6px;
}

.saved-task-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #155724;
}

.saved-task-card {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
  box-shadow: 3px 3px 0 #000;
  border-radius: 4px;
}

.saved-task-card .task-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.saved-task-card .task-meta {
  display: flex;
  gap: 1rem;
  margin: 0;
  flex-wrap: wrap;
}

.saved-task-card .task-status.failed {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 0.25rem 0.5rem;
  border: 2px solid #dc3545;
  background: #f8d7da;
  color: #721c24;
  border-radius: 3px;
}

.saved-task-card .saved-time {
  font-size: 0.75rem;
  font-weight: 600;
  color: #666;
  background: #f8f9fa;
  padding: 0.25rem 0.5rem;
  border: 1px solid #dee2e6;
  border-radius: 3px;
}

.no-restore-available {
  background: #f8d7da;
  border: 3px solid #dc3545;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #dc3545;
  border-radius: 6px;
}

.no-restore-available .warning-section {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  box-shadow: none;
}

.no-restore-available .warning-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.no-restore-available .warning-content {
  flex: 1;
}

.no-restore-available .warning-title {
  font-size: 1.1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #721c24;
}

.no-restore-available .warning-message {
  font-weight: 700;
  color: #721c24;
  margin: 0;
  line-height: 1.4;
}

/* Mobile responsive for restore task info */
@media (max-width: 768px) {
  .restore-task-info {
    margin-top: 0.75rem;
  }

  .saved-task-display,
  .no-restore-available {
    padding: 1rem;
  }

  .saved-task-title {
    font-size: 0.875rem;
    margin-bottom: 0.75rem;
  }

  .saved-task-card {
    padding: 0.75rem;
  }

  .saved-task-card .task-title {
    font-size: 0.875rem;
  }

  .saved-task-card .task-meta {
    flex-direction: column;
    gap: 0.5rem;
  }

  .no-restore-available .warning-section {
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }

  .no-restore-available .warning-title {
    font-size: 1rem;
  }
}

/* Notification Toast Styles */
.notification-container {
  position: fixed;
  top: 2rem;
  right: 2rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 400px;
  pointer-events: none;
}

.notification-toast {
  background: white;
  border: 4px solid #000;
  padding: 1rem 1.5rem;
  box-shadow: 8px 8px 0 #000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  pointer-events: auto;
  animation: slideInRight 0.3s ease-out;
  max-width: 100%;
  word-wrap: break-word;
}

.notification-success {
  border-color: #28a745;
  background: #d4edda;
  box-shadow: 8px 8px 0 #28a745;
}

.notification-error {
  border-color: #dc3545;
  background: #f8d7da;
  box-shadow: 8px 8px 0 #dc3545;
}

.notification-warning {
  border-color: #ffc107;
  background: #fff3cd;
  box-shadow: 8px 8px 0 #ffc107;
}

.notification-info {
  border-color: #17a2b8;
  background: #d1ecf1;
  box-shadow: 8px 8px 0 #17a2b8;
}

.notification-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.notification-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.notification-message {
  font-weight: 700;
  font-size: 0.875rem;
  line-height: 1.4;
  color: #000;
  word-break: break-word;
}

.notification-close {
  background: none;
  border: 2px solid #000;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  font-size: 1rem;
  font-weight: 900;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.notification-close:hover {
  background: #000;
  color: white;
  transform: scale(1.1);
}

@keyframes slideInRight {
  0% {
    transform: translateX(100%);
    opacity: 0;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Mobile responsive for notifications */
@media (max-width: 768px) {
  .notification-container {
    top: 1rem;
    right: 1rem;
    left: 1rem;
    max-width: none;
  }

  .notification-toast {
    padding: 0.75rem 1rem;
    box-shadow: 4px 4px 0 #000;
  }

  .notification-success {
    box-shadow: 4px 4px 0 #28a745;
  }

  .notification-error {
    box-shadow: 4px 4px 0 #dc3545;
  }

  .notification-warning {
    box-shadow: 4px 4px 0 #ffc107;
  }

  .notification-info {
    box-shadow: 4px 4px 0 #17a2b8;
  }

  .notification-message {
    font-size: 0.8rem;
  }

  .notification-close {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.875rem;
  }
}

/* Small Campfire Modal Styles */
.small-campfire-modal {
  .modal-content {
    max-width: 600px;
    background: linear-gradient(135deg, #ff6b35, #ff8c42);
    border: 3px solid #000;
    box-shadow: 8px 8px 0 #000;
  }

  .modal-header {
    background: linear-gradient(135deg, #ff6b35, #ff4500);
    color: white;
    border-bottom: 3px solid #000;
  }

  .modal-body {
    padding: 1.5rem;
    background: white;
  }

  .warning-section {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: linear-gradient(135deg, #fff8e1, #ffecb3);
    border: 3px solid #ffa000;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1.5rem;
    box-shadow: 4px 4px 0 #ffa000;
  }

  .warning-icon {
    font-size: 2rem;
    flex-shrink: 0;
  }

  .warning-content {
    flex: 1;
  }

  .warning-title {
    font-size: 1.125rem;
    font-weight: 900;
    color: #e65100;
    margin: 0 0 0.5rem 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .warning-message {
    font-size: 0.95rem;
    font-weight: 600;
    color: #333;
    margin: 0 0 0.5rem 0;
    line-height: 1.4;
  }

  .warning-note {
    font-size: 0.875rem;
    font-weight: 700;
    color: #d84315;
    margin: 0;
  }

  .tasks-list {
    max-height: 300px;
    overflow-y: auto;
    border: 3px solid #000;
    border-radius: 8px;
    background: #f8f9fa;
  }

  .task-item {
    border-bottom: 2px solid #dee2e6;
    padding: 1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    background: white;

    &:last-child {
      border-bottom: none;
    }

    &:hover {
      background: #e9ecef;
      transform: translateX(2px);
    }

    &.selected {
      background: linear-gradient(135deg, #ff6b35, #ff8c42);
      color: white;
      border-left: 5px solid #ff4500;
      box-shadow: inset 0 0 0 2px #fff;

      .task-title {
        color: white;
      }

      .task-meta {
        color: #fff;
      }

      .task-description {
        color: #fff;
      }
    }
  }

  .task-info {
    width: 100%;
  }

  .task-title {
    font-size: 1.125rem;
    font-weight: 900;
    color: #212529;
    margin: 0 0 0.5rem 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .task-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    font-weight: 700;
  }

  .task-difficulty {
    background: #007bff;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 0.75rem;
  }

  .task-status.frozen {
    background: #6c757d;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
  }

  .task-description {
    font-size: 0.875rem;
    color: #666;
    line-height: 1.4;
    margin: 0;
  }

  .no-tasks-message {
    text-align: center;
    padding: 2rem;
    color: #666;

    p {
      margin: 0.5rem 0;
      font-weight: 600;
    }

    .hint {
      font-size: 0.875rem;
      color: #999;
    }
  }

  .frozen-task-info {
    margin: 1rem 0;
  }

  .task-display-card {
    background: linear-gradient(135deg, #e3f2fd, #bbdefb);
    border: 3px solid #1976d2;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
    box-shadow: 4px 4px 0 #1976d2;
  }

  .freeze-info {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 2px solid #90caf9;
  }

  .freeze-time {
    font-size: 0.875rem;
    font-weight: 600;
    color: #1565c0;
    background: rgba(25, 118, 210, 0.1);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }

  .auto-select-note {
    font-size: 0.875rem;
    color: #666;
    text-align: center;
    margin: 1rem 0;
    font-weight: 600;
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    border: 2px solid #ff9800;
    border-radius: 6px;
    padding: 0.75rem;
    box-shadow: 2px 2px 0 #ff9800;
  }

  .item-info-section {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 3px solid #dee2e6;
  }

  .info-title {
    font-size: 1rem;
    font-weight: 900;
    color: #333;
    margin: 0 0 1rem 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .item-info-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: linear-gradient(135deg, #f8f9fa, #e9ecef);
    border: 3px solid #000;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 4px 4px 0 #000;
  }

  .item-icon {
    font-size: 2rem;
    flex-shrink: 0;
  }

  .item-details {
    flex: 1;
  }

  .item-name {
    display: block;
    font-size: 1rem;
    font-weight: 900;
    color: #212529;
    margin-bottom: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .item-description {
    display: block;
    font-size: 0.875rem;
    color: #666;
    line-height: 1.4;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    padding: 1rem 1.5rem;
    background: #f8f9fa;
    border-top: 3px solid #000;

    .modal-btn {
      padding: 0.75rem 1.5rem;
      border: 3px solid #000;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      cursor: pointer;
      box-shadow: 4px 4px 0 #000;
      transition: all 0.2s ease;

      &.secondary {
        background: #6c757d;
        color: white;

        &:hover {
          background: #5a6268;
          transform: translate(-1px, -1px);
          box-shadow: 5px 5px 0 #000;
        }
      }

      &.primary {
        background: linear-gradient(135deg, #ff6b35, #ff4500);
        color: white;

        &:hover:not(:disabled) {
          background: linear-gradient(135deg, #ff4500, #e63900);
          transform: translate(-1px, -1px);
          box-shadow: 5px 5px 0 #000;
        }

        &:disabled {
          background: #6c757d;
          cursor: not-allowed;
          opacity: 0.6;
        }
      }

      &:active {
        transform: translate(1px, 1px);
        box-shadow: 2px 2px 0 #000;
      }
    }
  }
}

/* Action button for small campfire */
.action-btn.small-campfire {
  background: linear-gradient(135deg, #ff6b35, #ff4500);
  color: white;
  border-color: #ff4500;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #ff4500, #e63900);
    transform: translate(-1px, -1px);
    box-shadow: 5px 5px 0 #000;
  }

  &:disabled {
    background: #6c757d;
    border-color: #6c757d;
    cursor: not-allowed;
    opacity: 0.6;
  }
}
</style>