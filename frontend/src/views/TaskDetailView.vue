<template>
  <div class="task-detail">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">← 返回</button>
        <h1>任务详情</h1>
        <div class="header-actions">
          <button
            @click="openShareModal"
            class="share-btn"
            title="分享任务"
          >
            🔗 分享
          </button>
          <button
            v-if="canDeleteTask"
            @click="deleteTask"
            class="delete-btn"
            title="删除任务"
          >
            🗑️ 删除
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="container">
        <!-- Loading -->
        <div v-if="loading" class="loading">
          加载中...
        </div>

        <!-- Error -->
        <div v-else-if="error" class="error">
          {{ error }}
        </div>

        <!-- Task Detail -->
        <div v-else-if="task" class="task-detail-content">
          <!-- Quick Actions Bar - 高频操作区域 -->
          <section v-if="canManageTask || canClaimTask || canSubmitProof || canReviewTask || canEndTask || canAddOvertime || canStartVoting || canVote" class="quick-actions-bar">
            <div class="quick-actions-content">
              <div class="actions-primary">
                <!-- Lock task primary actions -->
                <button
                  v-if="task.status === 'pending' && canManageTask"
                  @click="startTask"
                  class="quick-action-btn primary large"
                >
                  🚀 开始任务
                </button>
                <button
                  v-if="task.status === 'active' && canCompleteTask"
                  @click="completeTask"
                  class="quick-action-btn success large"
                >
                  ✅ 完成任务
                </button>
                <button
                  v-if="(task.status === 'active' || task.status === 'voting') && canManageLockTask"
                  @click="stopTask"
                  class="quick-action-btn danger large"
                >
                  ⏹️ 停止任务
                </button>

                <!-- Board task primary actions -->
                <button
                  v-if="canClaimTask"
                  @click="claimTask"
                  class="quick-action-btn warning large"
                >
                  📋 揭榜任务
                </button>
                <button
                  v-if="canSubmitProof"
                  @click="openSubmissionModal"
                  class="quick-action-btn info large"
                >
                  📤 提交完成证明
                </button>
                <button
                  v-if="canReviewTask"
                  @click="approveTask"
                  class="quick-action-btn success large"
                >
                  ✅ 审核通过
                </button>
                <button
                  v-if="canReviewTask"
                  @click="rejectTask"
                  class="quick-action-btn danger large"
                >
                  ❌ 审核拒绝
                </button>

                <!-- End task button -->
                <button
                  v-if="canEndTask"
                  @click="endTask"
                  class="quick-action-btn danger large"
                >
                  🏁 结束任务
                </button>

                <!-- Voting actions -->
                <button
                  v-if="canStartVoting"
                  @click="startVoting"
                  class="quick-action-btn vote large pulse"
                >
                  🗳️ 发起投票
                </button>
                <button
                  v-else-if="canVote"
                  @click="openVoteModal"
                  class="quick-action-btn vote large"
                >
                  🗳️ 参与投票
                </button>
              </div>

              <div class="actions-secondary">
                <!-- Secondary actions -->
                <button
                  v-if="canAddOvertime"
                  @click="addOvertime"
                  class="quick-action-btn secondary"
                >
                  ⏰ 随机加时
                </button>

              </div>
            </div>
          </section>
          <!-- Task Info Card -->
          <section class="task-card">
            <div class="task-header">
              <div class="task-basic-info">
                <h2 class="task-title">{{ task.title }}</h2>
                <div class="task-meta">
                  <span class="task-type">{{ getTaskTypeText(taskUnlockType) }}</span>
                  <span class="task-difficulty" :class="taskDifficulty">
                    {{ getDifficultyText(taskDifficulty) }}
                  </span>
                  <span class="task-status" :class="task.status">
                    {{ getStatusText(task.status) }}
                  </span>
                </div>
              </div>
              <div class="task-user">
                <UserAvatar
                  :user="task.user"
                  size="normal"
                  :clickable="true"
                  :show-lock-indicator="true"
                  :title="`查看 ${task.user.username} 的资料`"
                  @click="openUserProfile(task.user.id)"
                />
                <div class="user-info">
                  <button
                    @click="openUserProfile(task.user.id)"
                    class="username-btn"
                    :class="getLevelCSSClass(task.user.level || 1)"
                    :style="{ color: getLevelUsernameColor(task.user.level || 1) }"
                    :title="`查看 ${task.user.username} 的资料 (${getLevelDisplayName(task.user.level || 1)})`"
                  >
                    {{ task.user.username }}
                  </button>
                  <div class="create-time">创建于 {{ formatDateTime(task.created_at) }}</div>
                </div>
              </div>
            </div>

            <div class="task-description">
              <h3>任务描述</h3>
              <div v-if="task.description" class="task-description-content" v-html="task.description"></div>
              <p v-else class="no-description">暂无描述</p>
            </div>

            <!-- Task Details Grid -->
            <div class="task-details-grid">
              <div v-if="task.task_type === 'lock' && task.status === 'active'" class="detail-item">
                <span class="label">剩余时间</span>
                <span v-if="taskFrozen" class="value">
                  <span class="frozen-time-placeholder">❄️ 已冻结 ({{ formatTimeRemaining(timeRemaining) }})</span>
                </span>
                <span v-else-if="!taskTimeDisplayHidden" class="value countdown-display" :class="{ 'overtime': timeRemaining <= 0 }">
                  {{ timeRemaining > 0 ? formatTimeRemaining(timeRemaining) : '倒计时已结束' }}
                </span>
                <span v-else class="value">
                  <span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                </span>
              </div>
              <div v-if="task.task_type === 'lock' && taskStartTime" class="detail-item">
                <span class="label">开始时间</span>
                <span class="value">{{ formatDateTime(taskStartTime) }}</span>
              </div>
              <div v-if="task.task_type === 'lock' && taskEndTime" class="detail-item">
                <span class="label">预计结束时间</span>
                <span v-if="!taskTimeDisplayHidden" class="value">
                  {{ formatDateTime(taskEndTime) }}
                </span>
                <span v-else class="value">
                  <span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                </span>
              </div>
              <div class="detail-item">
                <span class="label">难度等级</span>
                <span class="value">{{ getDifficultyText(taskDifficulty) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">解锁方式</span>
                <span class="value">{{ getTaskTypeText(taskUnlockType) }}</span>
              </div>
              <div v-if="taskVoteThreshold" class="detail-item">
                <span class="label">投票门槛</span>
                <span class="value">{{ taskVoteThreshold }} 票</span>
              </div>

              <!-- Board task details -->
              <div v-if="task.task_type === 'board' && task.reward" class="detail-item">
                <span class="label">奖励金额</span>
                <span class="value">{{ task.reward }} 积分</span>
              </div>
              <div v-if="task.task_type === 'board' && task.max_duration" class="detail-item">
                <span class="label">最大完成时间</span>
                <span class="value">{{ task.max_duration }} 小时</span>
              </div>

              <!-- Multi-person task details -->
              <div v-if="task.task_type === 'board' && task.max_participants" class="detail-item">
                <span class="label">参与人数限制</span>
                <span class="value">{{ task.max_participants }} 人</span>
              </div>
              <div v-if="task.task_type === 'board' && task.participant_count !== undefined" class="detail-item">
                <span class="label">当前参与人数</span>
                <span class="value">{{ task.participant_count }}/{{ task.max_participants }} 人</span>
              </div>
              <div v-if="task.task_type === 'board' && task.submitted_count !== undefined" class="detail-item">
                <span class="label">已提交人数</span>
                <span class="value">{{ task.submitted_count }} 人</span>
              </div>
              <div v-if="task.task_type === 'board' && task.approved_count !== undefined" class="detail-item">
                <span class="label">已通过人数</span>
                <span class="value">{{ task.approved_count }} 人</span>
              </div>
              <div v-if="task.task_type === 'board' && task.max_participants > 1 && task.reward" class="detail-item">
                <span class="label">奖励分配</span>
                <span class="value">每人 {{ Math.ceil(task.reward / task.max_participants) }} 积分</span>
              </div>
            </div>

            <!-- Multi-person Task Participants Section -->
            <div v-if="task && task.task_type === 'board' && task.max_participants > 1 && (task as any).participants" class="participants-section">
              <div class="participants-header">
                <h3>参与情况</h3>
                <!-- Multi-person task status indicator -->
                <div v-if="task.status === 'submitted'" class="multi-task-status-notice">
                  <span class="notice-icon">ℹ️</span>
                  <span class="notice-text">任务有人已提交，仍可继续接取参与</span>
                </div>
                <div class="participants-stats">
                  <span class="stat-item">
                    <span class="stat-label">参与:</span>
                    <span class="stat-value">{{ task.participant_count || 0 }}/{{ task.max_participants }}</span>
                  </span>
                  <span class="stat-item">
                    <span class="stat-label">提交:</span>
                    <span class="stat-value">{{ task.submitted_count || 0 }}</span>
                  </span>
                  <span class="stat-item">
                    <span class="stat-label">通过:</span>
                    <span class="stat-value">{{ task.approved_count || 0 }}</span>
                  </span>
                </div>
              </div>

              <!-- Grid View -->
              <div class="participants-grid">
                <div
                  v-for="participant in (task as any).participants"
                  :key="participant.id"
                  class="participant-card"
                  :class="getParticipantCardClass(participant.status)"
                >
                  <div class="participant-header">
                    <UserAvatar
                      :user="participant.participant"
                      size="small"
                      :clickable="true"
                      @click="openUserProfile(participant.participant.id)"
                    />
                    <div class="participant-info">
                      <button
                        @click="openUserProfile(participant.participant.id)"
                        class="participant-name"
                        :title="`查看 ${participant.participant.username} 的资料`"
                      >
                        {{ participant.participant.username }}
                      </button>
                      <div class="participant-join-time">
                        {{ formatDateTime(participant.joined_at) }} 加入
                      </div>
                    </div>
                    <div class="participant-status-badge" :class="participant.status">
                      {{ getParticipantStatusText(participant.status) }}
                    </div>
                  </div>

                  <div v-if="participant.submission_text" class="participant-submission">
                    <div class="submission-label">提交内容:</div>
                    <div class="submission-text">{{ participant.submission_text }}</div>
                  </div>

                  <div v-if="participant.submission_files && participant.submission_files.length > 0" class="participant-files">
                    <div class="files-label">提交文件:</div>
                    <div class="files-grid">
                      <div
                        v-for="(file, fileIndex) in participant.submission_files"
                        :key="file.id"
                        class="file-item"
                        :class="{ 'primary-file': file.is_primary, 'image-file': isImageFile(file) }"
                        @click="handleFileClick(file)"
                        :title="isImageFile(file) ? '点击查看大图' : '点击下载文件'"
                      >
                        <!-- Image preview -->
                        <div v-if="isImageFile(file)" class="file-preview">
                          <img
                            :src="getFileUrl(file)"
                            :alt="`提交图片 ${fileIndex + 1}`"
                            class="preview-image"
                            @error="handleImageError"
                            loading="lazy"
                          />
                          <div class="image-overlay">
                            <span class="view-icon">👁️</span>
                          </div>
                        </div>
                        <!-- Non-image file -->
                        <div v-else class="file-icon">
                          <span class="file-type-icon">📄</span>
                        </div>

                      </div>
                    </div>
                  </div>

                  <div v-if="participant.review_comment" class="participant-review">
                    <div class="review-label">审核意见:</div>
                    <div class="review-comment">{{ participant.review_comment }}</div>
                  </div>

                  <div v-if="participant.reward_amount" class="participant-reward">
                    <div class="reward-label">分配奖励:</div>
                    <div class="reward-amount">{{ participant.reward_amount }} 积分</div>
                  </div>

                  <!-- Review actions for task publisher -->
                  <div v-if="canReviewParticipant(participant)" class="participant-actions">
                    <button
                      @click="approveParticipant(participant)"
                      class="action-btn approve-btn"
                    >
                      ✅ 通过
                    </button>
                    <button
                      @click="rejectParticipant(participant)"
                      class="action-btn reject-btn"
                    >
                      ❌ 拒绝
                    </button>
                  </div>
                </div>
              </div>

              <!-- Show available spots for open tasks -->
              <div v-if="task.status === 'open' && task.task_type === 'board' && task.available_spots && task.available_spots > 0" class="available-spots">
                <div class="spots-message">
                  🎯 还有 {{ task.available_spots }} 个名额，欢迎参与！
                </div>
              </div>

              <!-- Show task full message -->
              <div v-else-if="task.status === 'open' && task.task_type === 'board' && task.is_full" class="task-full">
                <div class="full-message">
                  🔒 任务已满员，无法继续参与
                </div>
              </div>
            </div>

            <!-- Task Timeline -->
            <div v-if="timeline.length > 0 || taskStartTime || taskEndTime" class="task-timeline">
              <div class="timeline-header">
                <h3>任务时间线</h3>
                <button
                  @click="refreshTimeline"
                  :disabled="timelineLoading"
                  class="refresh-timeline-btn"
                  title="刷新时间线"
                >
                  {{ timelineLoading ? '🔄' : '🔄' }} 刷新
                </button>
              </div>
              <div v-if="timelineLoading" class="timeline-loading">
                加载时间线中...
              </div>
              <div v-else>
                <!-- Desktop Timeline (Vertical) -->
                <div class="timeline-container desktop-timeline">
                  <!-- Timeline events from API -->
                  <div
                    v-for="event in timeline"
                    :key="event.id"
                    class="timeline-item"
                  >
                    <div class="timeline-dot" :class="getEventTypeClass(event.event_type)"></div>
                    <div class="timeline-content">
                      <div class="timeline-title">{{ event.event_type_display }}</div>
                      <div class="timeline-description">{{ event.description }}</div>
                      <div v-if="!taskTimeDisplayHidden" class="timeline-time">{{ formatDateTime(event.created_at) }}</div>
                      <div v-else class="timeline-time-hidden">
                        <span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                      </div>
                      <div v-if="event.user" class="timeline-user">
                        操作者:
                        <button
                          @click="openUserProfile(event.user.id)"
                          class="timeline-user-btn"
                          :title="`查看 ${event.user.username} 的资料`"
                        >
                          {{ event.user.username }}
                        </button>
                      </div>
                      <div v-if="event.time_change_minutes && !taskTimeDisplayHidden" class="timeline-time-change">
                        时间变化: {{ event.time_change_minutes > 0 ? '+' : '' }}{{ event.time_change_minutes }} 分钟
                      </div>
                      <div v-else-if="event.time_change_minutes && taskTimeDisplayHidden" class="timeline-time-change-hidden">
                        <span class="hidden-time-placeholder">🔒 时间变化已隐藏</span>
                      </div>
                      <div v-if="event.previous_end_time && event.new_end_time && !taskTimeDisplayHidden" class="timeline-times">
                        <div class="previous-time">原定结束: {{ formatDateTime(event.previous_end_time) }}</div>
                        <div class="new-time">新的结束: {{ formatDateTime(event.new_end_time) }}</div>
                      </div>
                      <div v-else-if="event.previous_end_time && event.new_end_time && taskTimeDisplayHidden" class="timeline-times-hidden">
                        <span class="hidden-time-placeholder">🔒 时间信息已隐藏</span>
                      </div>
                    </div>
                  </div>

                  <!-- Fallback: Basic timeline if no API events -->
                  <div v-if="timeline.length === 0 && taskStartTime" class="timeline-item">
                    <div class="timeline-dot start"></div>
                    <div class="timeline-content">
                      <div class="timeline-title">任务开始</div>
                      <div class="timeline-time">{{ formatDateTime(taskStartTime) }}</div>
                    </div>
                  </div>
                  <div v-if="timeline.length === 0 && taskEndTime" class="timeline-item">
                    <div class="timeline-dot end"></div>
                    <div class="timeline-content">
                      <div class="timeline-title">任务结束</div>
                      <div class="timeline-time">{{ formatDateTime(taskEndTime) }}</div>
                    </div>
                  </div>
                </div>

                <!-- Mobile Timeline (Horizontal) -->
                <div class="horizontal-timeline-wrapper mobile-timeline">
                <div
                  class="horizontal-timeline-container"
                  :style="{
                    '--timeline-items': timeline.length || 1,
                    'width': `${Math.max(timeline.length * 280 + 40, 320)}px`,
                    'min-height': `${Math.max(280, 240)}px`
                  }"
                >
                  <!-- Timeline track -->
                  <div class="timeline-track"></div>

                  <!-- Timeline events from API (oldest to newest, left to right) -->
                  <div
                    v-for="(event, index) in timelineReversed"
                    :key="event.id"
                    class="horizontal-timeline-item"
                    :style="{ left: `${index * 280 + 20}px` }"
                  >
                    <div class="timeline-dot-wrapper">
                      <div class="timeline-dot" :class="getEventTypeClass(event.event_type)"></div>
                      <div class="timeline-connector" v-if="index < timelineReversed.length - 1"></div>
                    </div>
                    <div class="timeline-card">
                      <div class="timeline-card-header">
                        <div class="timeline-title">{{ event.event_type_display }}</div>
                        <div v-if="!taskTimeDisplayHidden" class="timeline-time">
                          {{ formatDateTime(event.created_at) }}
                        </div>
                        <div v-else class="timeline-time-hidden">
                          <span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                        </div>
                      </div>
                      <div class="timeline-card-body">
                        <div class="timeline-description">{{ event.description }}</div>
                        <div v-if="event.user" class="timeline-user">
                          操作者:
                          <button
                            @click="openUserProfile(event.user.id)"
                            class="timeline-user-btn"
                            :title="`查看 ${event.user.username} 的资料`"
                          >
                            {{ event.user.username }}
                          </button>
                        </div>
                        <div v-if="event.time_change_minutes && !taskTimeDisplayHidden" class="timeline-time-change">
                          时间变化: {{ event.time_change_minutes > 0 ? '+' : '' }}{{ event.time_change_minutes }} 分钟
                        </div>
                        <div v-else-if="event.time_change_minutes && taskTimeDisplayHidden" class="timeline-time-change-hidden">
                          <span class="hidden-time-placeholder">🔒 时间变化已隐藏</span>
                        </div>
                        <div v-if="event.previous_end_time && event.new_end_time && !taskTimeDisplayHidden" class="timeline-times">
                          <div class="previous-time">原定结束: {{ formatDateTime(event.previous_end_time) }}</div>
                          <div class="new-time">新的结束: {{ formatDateTime(event.new_end_time) }}</div>
                        </div>
                        <div v-else-if="event.previous_end_time && event.new_end_time && taskTimeDisplayHidden" class="timeline-times-hidden">
                          <span class="hidden-time-placeholder">🔒 时间信息已隐藏</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Fallback: Basic timeline if no API events -->
                  <div v-if="timeline.length === 0 && taskStartTime" class="horizontal-timeline-item" style="left: 20px">
                    <div class="timeline-dot-wrapper">
                      <div class="timeline-dot start"></div>
                      <div class="timeline-connector" v-if="taskEndTime"></div>
                    </div>
                    <div class="timeline-card">
                      <div class="timeline-card-header">
                        <div class="timeline-title">任务开始</div>
                        <div class="timeline-time">{{ formatDateTime(taskStartTime) }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-if="timeline.length === 0 && taskEndTime" class="horizontal-timeline-item" style="left: 300px">
                    <div class="timeline-dot-wrapper">
                      <div class="timeline-dot end"></div>
                    </div>
                    <div class="timeline-card">
                      <div class="timeline-card-header">
                        <div class="timeline-title">任务结束</div>
                        <div class="timeline-time">{{ formatDateTime(taskEndTime) }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                </div>
              </div>
            </div>

            <!-- Progress Bar for Active Lock Tasks or Taken Board Tasks -->
            <div v-if="(task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')" class="task-progress-section">
              <h3>进度</h3>
              <div v-if="taskFrozen" class="progress-frozen-section">
                <span class="frozen-time-placeholder">❄️ 进度已冻结</span>
              </div>
              <div v-else-if="!taskTimeDisplayHidden" class="progress-container">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
                </div>
                <div class="progress-text">{{ progressPercent.toFixed(1) }}% 完成</div>
              </div>
              <div v-else class="progress-hidden-section">
                <span class="hidden-time-placeholder">🔒 进度已隐藏</span>
              </div>
              <div class="time-remaining">
                <span v-if="taskFrozen" class="frozen-time-placeholder">
                  ❄️ 已冻结 (剩余: {{ formatTimeRemaining(timeRemaining) }})
                </span>
                <span v-else-if="!taskTimeDisplayHidden">
                  <span v-if="timeRemaining > 0">剩余时间: {{ formatTimeRemaining(timeRemaining) }}</span>
                  <span v-else class="overtime">倒计时已结束</span>
                </span>
                <span v-else class="hidden-time-placeholder">🔒 时间已隐藏</span>
              </div>

              <!-- 带锁任务完成提示 -->
              <div v-if="task.task_type === 'lock' && task.status === 'active'" class="completion-hint">
                <!-- Key ownership requirement -->
                <div v-if="keyCheckLoading" class="hint-loading">
                  🔍 正在检查钥匙持有情况...
                </div>
                <div v-else-if="!hasTaskKey && authStore.isAuthenticated" class="hint-no-key">
                  <span v-if="!keyHolderInfo || !keyHolderInfo.has_key">
                    🔑 您没有持有此任务的钥匙，无法完成任务。只有钥匙的当前持有者才能完成此任务。
                  </span>
                  <span v-else-if="keyHolderInfo.key_holder">
                    🔑 您没有持有此任务的钥匙，无法完成任务。只有钥匙的当前持有者
                    <button
                      @click="openUserProfile(keyHolderInfo.key_holder.id)"
                      class="key-holder-link"
                      :title="`查看 ${keyHolderInfo.key_holder.username} 的资料`"
                    >
                      {{ keyHolderInfo.key_holder.username }}
                    </button>
                    才能完成此任务。
                  </span>
                </div>
                <div v-else-if="hasTaskKey">
                  <!-- Unlock type specific hints for key holders -->
                  <div v-if="taskUnlockType === 'vote'" class="hint-vote">
                    <div v-if="!isVotingPassed">
                      🗳️ 投票解锁任务：倒计时结束后可发起投票，投票通过后等待实际时间结束才能完成
                    </div>
                    <div v-else-if="timeRemaining > 0" class="hint-waiting">
                      <span v-if="!taskTimeDisplayHidden">
                        ✅ 投票已通过！等待倒计时结束后可手动完成任务：{{ formatTimeRemaining(timeRemaining) }}
                      </span>
                      <span v-else>
                        ✅ 投票已通过！等待倒计时结束后可手动完成任务：<span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                      </span>
                    </div>
                    <div v-else class="hint-ready">
                      🎉 投票已通过且倒计时已结束，您可以手动完成任务！
                    </div>
                  </div>
                  <div v-else-if="timeRemaining > 0" class="hint-waiting">
                    ⏳ 定时解锁任务：需要等待倒计时结束后才能手动完成
                  </div>
                  <div v-else class="hint-ready">
                    ✅ 倒计时已结束，您持有钥匙，可以手动完成任务
                  </div>

                  <!-- Key management section for key holders -->
                  <div v-if="taskKey && taskKey.original_owner && taskKey.original_owner.id !== authStore.user?.id" class="key-management">
                    <div class="key-return-info">
                      🔄 此钥匙原本属于 <strong>{{ taskKey.original_owner.username }}</strong>，您可以选择归还
                    </div>
                    <button
                      @click="returnKeyToOriginalOwner"
                      :disabled="returningKey"
                      class="return-key-btn"
                    >
                      {{ returningKey ? '归还中...' : '🔄 归还钥匙' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>


          <!-- Voting Section for Vote-based Tasks -->
          <section v-if="taskUnlockType === 'vote' && (task.status === 'active' || task.status === 'voting')" class="voting-section">
            <h3>投票解锁</h3>

            <!-- Task in active state, waiting for countdown -->
            <div v-if="task.status === 'active'" class="voting-waiting">
              <div v-if="timeRemaining > 0" class="vote-countdown-notice">
                <span v-if="!taskTimeDisplayHidden">
                  ⏳ 投票将在倒计时结束后开放: {{ formatTimeRemaining(timeRemaining) }}
                </span>
                <span v-else>
                  ⏳ 投票将在倒计时结束后开放: <span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                </span>
              </div>
              <div v-else-if="isOwnTask" class="vote-ready-notice">
                ✅ 倒计时已结束，你可以发起投票！点击按钮开始10分钟投票期
              </div>
              <div v-else class="vote-waiting-notice">
                ⏳ 倒计时已结束，等待任务创建者发起投票...
              </div>
            </div>

            <!-- Task in voting period -->
            <div v-else-if="task.status === 'voting'" class="voting-active">
              <div class="voting-period-info">
                <h4>🗳️ 投票期进行中</h4>
                <div class="voting-countdown">
                  <span v-if="!taskTimeDisplayHidden">
                    投票剩余时间: <strong>{{ formatVotingTimeRemaining() }}</strong>
                  </span>
                  <span v-else>
                    投票剩余时间: <span class="hidden-time-placeholder">🔒 时间已隐藏</span>
                  </span>
                </div>
                <div v-if="!taskTimeDisplayHidden" class="voting-schedule">
                  投票开始: {{ formatDateTime(taskVotingStartTime || '') }}<br>
                  投票结束: {{ formatDateTime(taskVotingEndTime || '') }}
                </div>
                <div v-else class="voting-schedule">
                  <span class="hidden-time-placeholder">🔒 投票时间已隐藏</span>
                </div>
              </div>
            </div>

            <!-- Vote statistics -->
            <div class="vote-info">
              <div class="vote-count">
                当前票数: <strong>{{ currentVotes }}</strong> 票
                <span v-if="taskVoteAgreementRatio">(需要 {{ (taskVoteAgreementRatio * 100).toFixed(0) }}% 同意率)</span>
              </div>
              <div v-if="currentVotes > 0" class="vote-breakdown">
                同意: {{ taskVoteAgreementCount }} 票 |
                反对: {{ currentVotes - taskVoteAgreementCount }} 票 |
                同意率: {{ (taskVoteAgreementCount / currentVotes * 100).toFixed(1) }}%
              </div>
            </div>

            <!-- 投票按钮已移至页面顶部快速操作栏 -->

            <!-- Status messages -->
            <div v-if="hasVoted" class="voted-message">
              ✅ 你已投票
            </div>

            <!-- Voting results display for completed or active tasks -->
            <div v-if="showVotingResults" class="voting-results">
              <h4>🗳️ 投票结果</h4>
              <div class="voting-result-summary">
                <div class="result-item">
                  <span class="result-label">总票数:</span>
                  <span class="result-value">{{ currentVotes }} 票</span>
                </div>
                <div class="result-item">
                  <span class="result-label">同意票:</span>
                  <span class="result-value">{{ taskVoteAgreementCount }} 票</span>
                </div>
                <div class="result-item">
                  <span class="result-label">反对票:</span>
                  <span class="result-value">{{ currentVotes - taskVoteAgreementCount }} 票</span>
                </div>
                <div class="result-item">
                  <span class="result-label">同意率:</span>
                  <span class="result-value">{{ currentVotes > 0 ? (taskVoteAgreementCount / currentVotes * 100).toFixed(1) : 0 }}%</span>
                </div>
              </div>

              <div class="voting-conclusion">
                <div v-if="isTaskCompleted" class="voting-passed">
                  ✅ 投票通过！任务已完成。
                </div>
                <div v-else-if="isVotingPassed" class="voting-passed">
                  ✅ 投票通过！任务可完成。
                </div>
                <div v-else class="voting-failed">
                  ❌ 投票未通过，任务继续进行并已加时。
                  <div class="failure-reasons">
                    <div v-if="currentVotes < taskVoteThresholdValue">
                      • 票数不足（需要 {{ taskVoteThresholdValue }} 票，当前 {{ currentVotes }} 票）
                    </div>
                    <div v-if="taskVoteAgreementRatio && currentVotes > 0 && (taskVoteAgreementCount / currentVotes) < taskVoteAgreementRatio">
                      • 同意率不足（需要 {{ (taskVoteAgreementRatio * 100).toFixed(0) }}%，当前 {{ (taskVoteAgreementCount / currentVotes * 100).toFixed(1) }}%）
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- Board Task Completion Proof Section -->
          <section v-if="canViewCompletionProof" class="completion-proof-section">
            <div class="proof-header">
              <h3>📋 任务完成证明</h3>
              <div class="proof-meta">
                <span class="proof-status" :class="getProofStatusClass(task.status)">{{ getProofStatusText(task.status) }}</span>
                <span class="submitter">提交者: {{ task.taker?.username || '未知' }}</span>
              </div>
            </div>

            <div class="proof-content">
              <div class="proof-label">完成证明内容：</div>
              <div class="proof-text">{{ task.completion_proof }}</div>
            </div>

            <!-- Media Files Section -->
            <div v-if="task.submission_files && task.submission_files.length > 0" class="media-files-section">
              <div class="media-files-header">
                <h4>📎 提交的媒体文件</h4>
              </div>
              <div class="media-files-grid">
                <div
                  v-for="file in task.submission_files"
                  :key="file.id"
                  class="media-file-item"
                  :class="{ 'primary-file': file.is_primary }"
                >
                  <!-- Image Files -->
                  <div v-if="file.is_image" class="media-file-image">
                    <img
                      :src="file.file_url"
                      :alt="`提交图片`"
                      @click="openImageModal(file)"
                      class="media-image"
                    />
                    <div class="file-info-static">
                      <span v-if="file.is_primary" class="primary-badge">主要文件</span>
                    </div>
                  </div>

                  <!-- Video Files -->
                  <div v-else-if="file.is_video" class="media-file-video">
                    <video
                      :src="file.file_url"
                      controls
                      preload="metadata"
                      class="media-video"
                    >
                      您的浏览器不支持视频播放
                    </video>
                    <div class="file-info">
                      <span v-if="file.is_primary" class="primary-badge">主要文件</span>
                    </div>
                  </div>

                  <!-- Other Files -->
                  <div v-else class="media-file-document">
                    <div class="document-icon">📄</div>
                    <div class="file-info">
                      <span v-if="file.is_primary" class="primary-badge">主要文件</span>
                    </div>
                    <a
                      :href="file.file_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="download-btn"
                      title="下载文件"
                    >
                      📥 下载
                    </a>
                  </div>

                  <!-- File Description -->
                  <div v-if="file.description" class="file-description">
                    {{ file.description }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Review actions for task publisher -->
            <div v-if="canReviewTask" class="proof-review-actions">
              <div class="review-notice">
                <span class="notice-icon">⚠️</span>
                <span class="notice-text">请仔细审核任务完成证明，审核决定一旦做出无法撤销</span>
              </div>
              <div class="review-buttons">
                <button
                  @click="approveTask"
                  class="review-btn approve-btn"
                >
                  ✅ 审核通过
                </button>
                <button
                  @click="rejectTask"
                  class="review-btn reject-btn"
                >
                  ❌ 审核拒绝
                </button>
              </div>
            </div>

            <!-- Status info for non-reviewers -->
            <div v-else-if="task.task_type === 'board' && task.status === 'submitted'" class="proof-status-info">
              <span class="status-icon">⏳</span>
              <span class="status-text">等待任务发布者审核中...</span>
            </div>
          </section>

          <!-- Key Holder Actions Section -->
          <section v-if="canManageKeyActions" class="key-holder-section">
            <div class="key-holder-header">
              <h3>🔑 钥匙持有者专属操作</h3>
              <div class="key-holder-info">
                <span class="coins-display">💰 当前积分: {{ authStore.user?.coins || 0 }}</span>
              </div>
            </div>

            <div class="key-actions-grid">
              <!-- Manual Time Adjustment -->
              <div class="key-action-card">
                <div class="action-header">
                  <h4>⏰ 手动时间调整</h4>
                  <span class="action-cost">消耗 10 积分</span>
                </div>
                <p class="action-description">固定调整任务时间 ±20 分钟</p>
                <div class="action-buttons">
                  <button
                    @click="manualTimeAdjustment('increase')"
                    :disabled="!canAffordTimeAdjustment"
                    class="key-action-btn increase"
                    :class="{ 'disabled': !canAffordTimeAdjustment }"
                  >
                    ⏰ 加时
                  </button>
                  <button
                    @click="manualTimeAdjustment('decrease')"
                    :disabled="!canAffordTimeAdjustment"
                    class="key-action-btn decrease"
                    :class="{ 'disabled': !canAffordTimeAdjustment }"
                  >
                    ⏰ 减时
                  </button>
                </div>
              </div>

              <!-- Time Display Toggle -->
              <div class="key-action-card">
                <div class="action-header">
                  <h4>👁️ 时间显示控制</h4>
                  <span class="action-cost">消耗 50 积分</span>
                </div>
                <p class="action-description">
                  当前状态: {{ taskTimeDisplayHidden ? '🌫️ 时间已隐藏' : '👁️ 时间可见' }}
                </p>
                <div class="action-buttons">
                  <button
                    @click="toggleTimeDisplay"
                    :disabled="!canAffordTimeToggle"
                    class="key-action-btn time-toggle"
                    :class="{
                      'disabled': !canAffordTimeToggle,
                      'hidden-mode': taskTimeDisplayHidden
                    }"
                  >
                    {{ taskTimeDisplayHidden ? '👁️ 显示时间' : '🙈 隐藏时间' }}
                  </button>
                </div>
              </div>

              <!-- Freeze/Unfreeze Task -->
              <div class="key-action-card">
                <div class="action-header">
                  <h4>❄️ 冻结/解冻控制</h4>
                  <span class="action-cost">消耗 25 积分</span>
                </div>
                <p class="action-description">
                  当前状态: {{ taskFrozen ? '❄️ 任务已冻结' : '🔥 任务进行中' }}
                </p>
                <div class="action-buttons">
                  <button
                    v-if="!taskFrozen"
                    @click="freezeTask"
                    :disabled="!canAffordFreeze || freezingInProgress"
                    class="key-action-btn freeze"
                    :class="{ 'disabled': !canAffordFreeze || freezingInProgress }"
                  >
                    {{ freezingInProgress ? '冻结中...' : '❄️ 冻结任务' }}
                  </button>
                  <button
                    v-else
                    @click="unfreezeTask"
                    :disabled="!canAffordFreeze || freezingInProgress"
                    class="key-action-btn unfreeze"
                    :class="{ 'disabled': !canAffordFreeze || freezingInProgress }"
                  >
                    {{ freezingInProgress ? '解冻中...' : '🔥 解冻任务' }}
                  </button>
                </div>
              </div>

              <!-- Pin Task Owner -->
              <div class="key-action-card">
                <div class="action-header">
                  <h4>📌 置顶惩罚</h4>
                  <span class="action-cost">消耗 60 积分</span>
                </div>
                <p class="action-description">
                  置顶任务创建者 <strong>{{ task?.user?.username }}</strong> 30分钟，置顶期间他人加时效果×10
                </p>
                <div class="action-buttons">
                  <button
                    @click="pinTaskOwner"
                    :disabled="!canAffordPinning || pinningInProgress"
                    class="key-action-btn pin"
                    :class="{ 'disabled': !canAffordPinning || pinningInProgress }"
                  >
                    {{ pinningInProgress ? '置顶中...' : '📌 置顶惩罚' }}
                  </button>
                </div>
              </div>

              <!-- Key Return Option -->
              <div v-if="taskKey && taskKey.original_owner && taskKey.original_owner.id !== authStore.user?.id" class="key-action-card">
                <div class="action-header">
                  <h4>🔄 钥匙归还</h4>
                  <span class="action-cost">免费</span>
                </div>
                <p class="action-description">
                  将钥匙归还给原持有者: <strong>{{ taskKey.original_owner.username }}</strong>
                </p>
                <div class="action-buttons">
                  <button
                    @click="returnKeyToOriginalOwner"
                    :disabled="returningKey"
                    class="key-action-btn return"
                  >
                    {{ returningKey ? '归还中...' : '🔄 归还钥匙' }}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Task Submission Modal -->
    <TaskSubmissionModal
      :is-visible="showSubmissionModal"
      :task="task as any"
      @close="closeSubmissionModal"
      @success="handleSubmissionSuccess"
    />

    <!-- Profile Modal -->
    <ProfileModal
      :is-visible="showProfileModal"
      :user-id="selectedUserId"
      @close="closeProfileModal"
    />

    <!-- Vote Confirmation Modal -->
    <VoteConfirmationModal
      :is-visible="showVoteModal"
      :task="task as any"
      @close="closeVoteModal"
      @vote="submitVote"
    />

    <!-- Share Modal -->
    <ShareModal
      :is-visible="showShareModal"
      :share-url="shareUrl"
      :task-title="task?.title || ''"
      :task-type="task?.task_type || ''"
      :task-description="task?.description"
      :task-id="task?.id"
      :task-status="task?.status"
      @close="closeShareModal"
    />

    <!-- Image Modal -->
    <div v-if="showImageModal && selectedImage" class="image-modal-overlay" @click="closeImageModal">
      <div class="image-modal-content" @click.stop>
        <div class="image-modal-header">
          <button @click="closeImageModal" class="image-modal-close">×</button>
        </div>
        <div class="image-modal-body">
          <img
            :src="selectedImage.file_url"
            :alt="`提交图片`"
            class="image-modal-img"
          />
        </div>
      </div>
    </div>


    <!-- Notification Toast -->
    <NotificationToast
      :is-visible="showToast"
      :type="toastData.type"
      :title="toastData.title"
      :message="toastData.message"
      :secondary-message="toastData.secondaryMessage"
      :details="toastData.details"
      @close="showToast = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import { tasksApi } from '../lib/api-tasks'
import { storeApi } from '../lib/api'
import { getLevelCSSClass, getLevelDisplayName, getLevelUsernameColor } from '../lib/level-colors'
import { smartGoBack } from '../utils/navigation'
import TaskSubmissionModal from '../components/TaskSubmissionModal.vue'
import ProfileModal from '../components/ProfileModal.vue'
import VoteConfirmationModal from '../components/VoteConfirmationModal.vue'
import ShareModal from '../components/ShareModal.vue'
import NotificationToast from '../components/NotificationToast.vue'
import UserAvatar from '../components/UserAvatar.vue'
import type { Task } from '../types/index'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const tasksStore = useTasksStore()

// State
const task = ref<Task | null>(null)
const loading = ref(true)
const error = ref('')
const currentVotes = ref(0)
const hasVoted = ref(false)
const progressInterval = ref<number>()
const currentTime = ref(Date.now())
const timeline = ref<any[]>([])
const timelineLoading = ref(false)
const showSubmissionModal = ref(false)
const showProfileModal = ref(false)
const selectedUserId = ref<number | undefined>(undefined)
const showVoteModal = ref(false)
const votingProcessing = ref(false) // 防止重复处理投票结果
const userInventory = ref<any>(null)
const hasTaskKey = ref(false)
const keyCheckLoading = ref(false)
const taskKey = ref<any>(null)
const returningKey = ref(false)
const showShareModal = ref(false)
const keyHolderInfo = ref<{
  has_key: boolean
  key_holder?: {
    id: number
    username: string
    is_current_user: boolean
  }
  original_owner?: {
    id: number
    username: string
  }
} | null>(null)

// Pinning state
const pinningInProgress = ref(false)

// Freeze state
const freezingInProgress = ref(false)

// Image modal state
const showImageModal = ref(false)
const selectedImage = ref<any>(null)

// Multi-person task participants navigation state (removed review mode)


// Toast notification state
const showToast = ref(false)
const toastData = ref<{
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  secondaryMessage?: string
  details?: Record<string, any>
}>({
  type: 'info',
  title: '',
  message: ''
})

// Computed properties for template access
const taskUnlockType = computed(() => {
  if (!task.value) return 'time'
  return task.value.task_type === 'lock' ? (task.value as any).unlock_type || 'time' : 'time'
})

const taskDifficulty = computed(() => {
  if (!task.value) return 'normal'
  return task.value.task_type === 'lock' ? (task.value as any).difficulty || 'normal' : 'normal'
})

const taskVoteThreshold = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return 0
  return (task.value as any).vote_threshold || 0
})

const taskStartTime = computed(() => {
  if (!task.value) return null
  return task.value.task_type === 'lock' ? (task.value as any).start_time : null
})

const taskVotingStartTime = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return null
  return (task.value as any).voting_start_time || null
})

const taskVotingEndTime = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return null
  return (task.value as any).voting_end_time || null
})

const taskVoteAgreementRatio = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return null
  return (task.value as any).vote_agreement_ratio || null
})

const taskVoteAgreementCount = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return 0
  return (task.value as any).vote_agreement_count || 0
})

const taskVoteThresholdValue = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return 0
  return (task.value as any).vote_threshold || 0
})

const isVotingPassed = computed(() => {
  if (!task.value || task.value.task_type !== 'lock' || taskUnlockType.value !== 'vote') {
    console.log('🗳️ isVotingPassed: false - not a vote unlock task')
    return false
  }

  const totalVotes = currentVotes.value
  const agreeVotes = taskVoteAgreementCount.value
  const requiredThreshold = taskVoteThresholdValue.value || 0
  const requiredRatio = taskVoteAgreementRatio.value || 0.5

  console.log('🗳️ isVotingPassed check:', {
    totalVotes,
    agreeVotes,
    requiredThreshold,
    requiredRatio,
    hasVotingTimes: !!(taskVotingStartTime.value && taskVotingEndTime.value)
  })

  // 检查是否经历了完整的投票流程
  if (!taskVotingStartTime.value || !taskVotingEndTime.value) {
    console.log('🗳️ isVotingPassed: false - no complete voting process')
    return false
  }

  // 检查投票数量是否达到门槛
  if (totalVotes < requiredThreshold) {
    console.log('🗳️ isVotingPassed: false - not enough votes:', totalVotes, '<', requiredThreshold)
    return false
  }

  // 检查同意比例是否达到要求
  const agreementRatio = totalVotes === 0 ? 0 : agreeVotes / totalVotes
  if (agreementRatio < requiredRatio) {
    console.log('🗳️ isVotingPassed: false - agreement ratio not met:', agreementRatio, '<', requiredRatio)
    return false
  }

  console.log('🗳️ isVotingPassed: true - all conditions met')
  return true
})

const taskEndTime = computed(() => {
  if (!task.value) return null
  if (task.value.task_type === 'lock') {
    return (task.value as any).end_time || null
  }
  return null
})

const canDeleteTask = computed(() => {
  if (!task.value) return false
  return authStore.user?.is_staff || authStore.user?.is_superuser
})

const canManageTask = computed(() => {
  if (!task.value) return false
  const canManage = authStore.user?.id === task.value.user.id
  console.log('🔧 canManageTask:', canManage, 'for user:', authStore.user?.id, 'task owner:', task.value.user.id)
  return canManage
})

const isOwnTask = computed(() => {
  if (!task.value) return false
  return authStore.user?.id === task.value.user.id
})

const canClaimTask = computed(() => {
  if (!task.value) return false

  // 基本条件：是任务板，不是自己的任务
  if (task.value.task_type !== 'board' || isOwnTask.value) return false

  // 使用后端返回的 can_take 字段
  return task.value.can_take === true
})

const canSubmitProof = computed(() => {
  if (!task.value || !authStore.user) return false

  // 只有任务板可以提交证明
  if (task.value.task_type !== 'board') return false

  // 不能提交自己发布的任务
  if (task.value.user.id === authStore.user.id) return false

  // 判断是单人还是多人任务
  const isMultiPerson = task.value.max_participants && task.value.max_participants > 1

  if (isMultiPerson) {
    // 多人任务：检查是否已参与且任务状态允许提交
    const isParticipant = task.value.participants?.some(p => p.participant.id === authStore.user?.id)
    const allowedStatuses = ['taken', 'submitted']  // 多人任务在这些状态下都可以提交

    if (!isParticipant || !allowedStatuses.includes(task.value.status)) {
      return false
    }

    // 检查当前用户是否已经提交过
    const currentParticipant = task.value.participants?.find(p => p.participant.id === authStore.user?.id)
    return currentParticipant?.status !== 'submitted' && currentParticipant?.status !== 'approved'
  } else {
    // 单人任务：检查是否是接取者且状态为taken
    return task.value.status === 'taken' && task.value.taker?.id === authStore.user.id
  }
})

const canReviewTask = computed(() => {
  if (!task.value) return false
  // Can review if it's a board task, submitted status, and user is the publisher
  // Cannot review if task is completed
  return task.value.task_type === 'board' &&
         task.value.status === 'submitted' &&
         task.value.user.id === authStore.user?.id
})

const canEndTask = computed(() => {
  if (!task.value || !isOwnTask.value) return false

  // 只有任务板可以手动结束
  if (task.value.task_type !== 'board') return false

  // 判断是单人还是多人任务
  const isMultiPerson = task.value.max_participants && task.value.max_participants > 1

  if (isMultiPerson) {
    // 多人任务：任何状态下都可以结束（除了已完成和已失败）
    return !['completed', 'failed'].includes(task.value.status)
  } else {
    // 单人任务：只能在开放或已接取状态结束
    return ['open', 'taken'].includes(task.value.status)
  }
})

const canViewCompletionProof = computed(() => {
  if (!task.value || !authStore.isAuthenticated) return false

  // Only for board tasks with completion proof
  if (task.value.task_type !== 'board' || !task.value.completion_proof) return false

  // Task publisher (owner) can always view
  const isTaskPublisher = task.value.user.id === authStore.user?.id

  // Task taker (揭榜者) can always view
  const isTaskTaker = task.value.taker?.id === authStore.user?.id

  console.log('🔍 canViewCompletionProof check:', {
    taskId: task.value.id,
    currentUserId: authStore.user?.id,
    taskPublisherId: task.value.user.id,
    taskTakerId: task.value.taker?.id,
    isTaskPublisher,
    isTaskTaker,
    canView: isTaskPublisher || isTaskTaker
  })

  return isTaskPublisher || isTaskTaker
})

const canAddOvertime = computed(() => {
  if (!task.value) return false
  // Can add overtime if it's a lock task, status is active, and not own task
  return task.value.task_type === 'lock' &&
         task.value.status === 'active' &&
         !isOwnTask.value
})

const canManageLockTask = computed(() => {
  if (!task.value) return false

  // For lock tasks, either the task owner OR the key holder can manage certain actions
  if (task.value.task_type === 'lock') {
    const isTaskOwner = authStore.user?.id === task.value.user.id
    const isKeyHolder = hasTaskKey.value && !keyCheckLoading.value

    console.log('🔐 canManageLockTask check:', {
      isTaskOwner,
      isKeyHolder,
      hasTaskKey: hasTaskKey.value,
      keyCheckLoading: keyCheckLoading.value
    })

    return isTaskOwner || isKeyHolder
  }

  // For non-lock tasks, use original logic
  return canManageTask.value
})

const canCompleteTask = computed(() => {
  if (!task.value) return false

  console.log('🎯 canCompleteTask check for task:', task.value.id, {
    taskType: task.value.task_type,
    status: task.value.status,
    unlockType: taskUnlockType.value,
    hasTaskKey: hasTaskKey.value,
    keyCheckLoading: keyCheckLoading.value
  })

  // For lock tasks, must have the task key to complete
  if (task.value.task_type === 'lock') {
    // If still checking key ownership, don't allow completion yet
    if (keyCheckLoading.value) {
      console.log('🎯 canCompleteTask: false - still checking key ownership')
      return false
    }

    // Must have the task key
    if (!hasTaskKey.value) {
      console.log('🎯 canCompleteTask: false - user does not have task key')
      return false
    }

    // For lock tasks with vote unlock type - can complete after voting passes AND countdown ends
    if (taskUnlockType.value === 'vote') {
      // Check if voting has passed
      if (!isVotingPassed.value) {
        console.log('🎯 canCompleteTask: false - voting has not passed yet')
        return false
      }

      // If voting passed, check if countdown has ended
      if (taskEndTime.value) {
        const now = currentTime.value
        const endTime = new Date(taskEndTime.value).getTime()
        const canComplete = now >= endTime
        console.log('🎯 canCompleteTask (vote unlock, voting passed, checking time):', canComplete, 'now:', now, 'endTime:', endTime)
        return canComplete
      }

      // If no end time, can complete immediately after voting passes
      console.log('🎯 canCompleteTask: true - voting passed and no countdown')
      return true
    }

    // For lock tasks with time unlock type, can only complete after countdown ends
    if (taskEndTime.value) {
      const now = currentTime.value
      const endTime = new Date(taskEndTime.value).getTime()
      const canComplete = now >= endTime
      console.log('🎯 canCompleteTask (time unlock with key):', canComplete, 'now:', now, 'endTime:', endTime)
      return canComplete
    }
  }

  // For board tasks, can complete anytime when active
  const canComplete = task.value.status === 'active'
  console.log('🎯 canCompleteTask (board task):', canComplete)
  return canComplete
})

const progressPercent = computed(() => {
  if (!task.value) return 0

  // Lock tasks progress
  if (task.value.task_type === 'lock' && task.value.status === 'active' && task.value.start_time && task.value.end_time) {
    const start = new Date(task.value.start_time).getTime()
    const end = new Date(task.value.end_time).getTime()
    const now = currentTime.value

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  // Board tasks progress
  if (task.value.task_type === 'board' && task.value.status === 'taken') {
    const boardTask = task.value as any // Type assertion for board task properties
    if (boardTask.taken_at && boardTask.deadline) {
      const start = new Date(boardTask.taken_at).getTime()
      const end = new Date(boardTask.deadline).getTime()
      const now = currentTime.value

      if (now <= start) return 0
      if (now >= end) return 100

      return ((now - start) / (end - start)) * 100
    }
  }

  return 0
})

const timeRemaining = computed(() => {
  if (!task.value) return 0

  // Lock tasks time remaining
  if (task.value.task_type === 'lock' && task.value.status === 'active' && task.value.end_time) {
    // If task is frozen, return the frozen remaining time
    if (taskFrozen.value && (task.value as any).frozen_end_time && (task.value as any).frozen_at) {
      const frozenEndTime = new Date((task.value as any).frozen_end_time).getTime()
      const frozenAtTime = new Date((task.value as any).frozen_at).getTime()
      return Math.max(0, frozenEndTime - frozenAtTime)
    }

    const end = new Date(task.value.end_time).getTime()
    const now = currentTime.value
    return Math.max(0, end - now)
  }

  // Board tasks time remaining
  if (task.value.task_type === 'board' && task.value.status === 'taken') {
    const boardTask = task.value as any // Type assertion for board task properties
    if (boardTask.deadline) {
      const end = new Date(boardTask.deadline).getTime()
      const now = currentTime.value
      return Math.max(0, end - now)
    }
  }

  return 0
})

const votingTimeRemaining = computed(() => {
  if (!task.value || task.value.status !== 'voting' || !taskVotingEndTime.value) {
    return 0
  }

  const end = new Date(taskVotingEndTime.value).getTime()
  const now = currentTime.value
  return Math.max(0, end - now)
})

const canVote = computed(() => {
  if (!task.value || hasVoted.value) {
    return false
  }

  // Can vote if task is in voting period
  if (task.value.status === 'voting') {
    return votingTimeRemaining.value > 0
  }

  return false
})

const canStartVoting = computed(() => {
  if (!task.value || taskUnlockType.value !== 'vote') {
    return false
  }

  // 如果投票已经通过，不显示发起投票按钮
  if (isVotingPassed.value) {
    return false
  }

  // Either task owner or key holder can start voting
  const isTaskOwner = isOwnTask.value
  const isKeyHolder = hasTaskKey.value && !keyCheckLoading.value

  if (!isTaskOwner && !isKeyHolder) {
    return false
  }

  // Can start voting if task is active and countdown has ended
  if (task.value.status === 'active' && timeRemaining.value <= 0) {
    return true // Can always start voting when countdown is over
  }

  return false
})

// Helper computed for template type checking
const isTaskCompleted = computed(() => {
  return task.value?.status === 'completed'
})

const isTaskActive = computed(() => {
  return task.value?.status === 'active'
})

const showVotingResults = computed(() => {
  if (!task.value || taskUnlockType.value !== 'vote' || !taskVotingEndTime.value) {
    return false
  }
  return ['active', 'completed'].includes(task.value.status)
})

// Share URL computed property
const shareUrl = computed(() => {
  if (!task.value) return ''
  const baseUrl = window.location.origin
  return `${baseUrl}/tasks/${task.value.id}`
})

// Timeline reversed for mobile horizontal display (oldest to newest, left to right)
const timelineReversed = computed(() => {
  return [...timeline.value].reverse()
})

// 钥匙玩法相关计算属性
const taskTimeDisplayHidden = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return false
  return (task.value as any).time_display_hidden || false
})

const taskFrozen = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return false
  return (task.value as any).is_frozen || false
})

const canManageKeyActions = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return false

  // Only key holders can manage key actions
  const isKeyHolder = hasTaskKey.value && !keyCheckLoading.value

  console.log('🔑 canManageKeyActions check:', {
    hasTaskKey: hasTaskKey.value,
    keyCheckLoading: keyCheckLoading.value,
    isKeyHolder,
    taskId: task.value.id
  })

  return isKeyHolder
})

const canAffordTimeAdjustment = computed(() => {
  if (!authStore.user || !canManageKeyActions.value) return false
  return authStore.user.coins >= 10 // 手动时间调整需要10积分
})

const canAffordTimeToggle = computed(() => {
  if (!authStore.user || !canManageKeyActions.value) return false
  return authStore.user.coins >= 50 // 时间显示切换需要50积分
})

const canAffordPinning = computed(() => {
  if (!authStore.user || !canManageKeyActions.value) return false
  return authStore.user.coins >= 60 // 置顶惩罚需要60积分
})

const canAffordFreeze = computed(() => {
  if (!authStore.user || !canManageKeyActions.value) return false
  return authStore.user.coins >= 25 // 冻结/解冻需要25积分
})

// Multi-person task computed properties (review mode removed)

// Methods
const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
}

const openShareModal = () => {
  showShareModal.value = true
}

const closeShareModal = () => {
  showShareModal.value = false
}

const checkUserHasTaskKey = async () => {
  if (!task.value || !authStore.isAuthenticated) {
    hasTaskKey.value = false
    keyHolderInfo.value = null
    return
  }

  try {
    keyCheckLoading.value = true
    userInventory.value = await storeApi.getUserInventory()

    // Check if user has a key for this specific task
    const foundTaskKey = userInventory.value.items.find((item: any) =>
      item.item_type.name === 'key' &&
      item.status === 'available' &&
      item.properties?.task_id === task.value?.id
    )

    hasTaskKey.value = !!foundTaskKey
    taskKey.value = foundTaskKey || null

    // If user doesn't have the key, fetch key holder information
    if (!hasTaskKey.value && task.value?.id) {
      try {
        keyHolderInfo.value = await storeApi.getTaskKeyHolder(task.value.id)
        console.log('🔍 Key holder info:', keyHolderInfo.value)
      } catch (error: any) {
        console.error('Error fetching key holder info:', error)
        keyHolderInfo.value = null
      }
    } else {
      keyHolderInfo.value = null
    }

    console.log('🔑 Key ownership check:', {
      taskId: task.value.id,
      hasKey: hasTaskKey.value,
      keyItem: taskKey.value?.id,
      totalItems: userInventory.value.items.length,
      keyItems: userInventory.value.items.filter((item: any) => item.item_type.name === 'key').length,
      keyHolderInfo: keyHolderInfo.value
    })

  } catch (error) {
    console.error('Error checking task key ownership:', error)
    hasTaskKey.value = false
    keyHolderInfo.value = null
  } finally {
    keyCheckLoading.value = false
  }
}

const fetchTimeline = async () => {
  const taskId = route.params.id as string
  if (!taskId || !task.value) return

  try {
    timelineLoading.value = true
    const timelineData = await tasksApi.getTaskTimeline(taskId)
    timeline.value = timelineData.timeline_events || []

    console.log('📊 Timeline data loaded:', timeline.value.length, 'events')

    // Scroll to newest event on mobile after timeline loads
    await nextTick()
    console.log('🔄 Triggering scroll to newest event after DOM update')
    scrollToNewestEvent()

    // Setup intersection observer for mobile timeline visibility
    if (window.innerWidth <= 768) {
      setTimeout(() => {
        setupTimelineObserver()
      }, 300)
    }
  } catch (err: any) {
    console.error('Error fetching timeline:', err)
    // Timeline is optional, don't show error to user
  } finally {
    timelineLoading.value = false
  }
}

const scrollToNewestEvent = () => {
  // Only scroll on mobile devices
  if (window.innerWidth > 768) return

  // Use a small delay to ensure DOM is fully rendered
  setTimeout(() => {
    // Find the horizontal timeline wrapper
    const timelineWrapper = document.querySelector('.horizontal-timeline-wrapper')
    if (timelineWrapper && timeline.value.length > 0) {
      console.log('📱 Scrolling to newest event on mobile')
      console.log('Timeline wrapper found:', timelineWrapper)
      console.log('Scroll width:', timelineWrapper.scrollWidth)
      console.log('Client width:', timelineWrapper.clientWidth)

      // Calculate scroll position to show newest event (rightmost)
      const maxScrollLeft = timelineWrapper.scrollWidth - timelineWrapper.clientWidth
      console.log('Calculated max scroll left:', maxScrollLeft)

      // Use smooth scrolling behavior
      timelineWrapper.scrollTo({
        left: maxScrollLeft,
        behavior: 'smooth'
      })

      // Also set scrollLeft as fallback
      timelineWrapper.scrollLeft = maxScrollLeft

      // Verify scroll position was set after a short delay
      setTimeout(() => {
        console.log('Actual scroll left after setting:', timelineWrapper.scrollLeft)
      }, 50)
    } else {
      console.log('❌ Timeline wrapper not found or no timeline events')
      console.log('Timeline wrapper:', timelineWrapper)
      console.log('Timeline length:', timeline.value.length)
    }
  }, 200) // Increased delay to ensure DOM is ready
}

// Add intersection observer for timeline visibility
const setupTimelineObserver = () => {
  if (window.innerWidth > 768) return

  // Clean up existing observer
  if (timelineObserver.value) {
    timelineObserver.value.disconnect()
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting && timeline.value.length > 0) {
        console.log('📱 Timeline became visible, scrolling to newest event')
        scrollToNewestEvent()
      }
    })
  }, {
    threshold: 0.1
  })

  // Observe the timeline container
  const timelineContainer = document.querySelector('.horizontal-timeline-container')
  if (timelineContainer) {
    observer.observe(timelineContainer)
    timelineObserver.value = observer
    console.log('📱 Timeline observer setup complete')
  }

  return observer
}

const refreshTimeline = async () => {
  console.log('Manual timeline refresh triggered')
  await fetchTimeline()
}

const fetchTask = async () => {
  const taskId = route.params.id as string
  console.log('🚀 fetchTask started with taskId:', taskId)

  if (!taskId) {
    console.error('❌ No taskId provided')
    error.value = '无效的任务ID'
    loading.value = false
    return
  }

  try {
    console.log('📡 Calling tasksApi.getTask with taskId:', taskId)
    console.log('🔍 API Base URL:', import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api')
    console.log('🎫 Auth token exists:', !!localStorage.getItem('token'))

    const fetchedTask = await tasksApi.getTask(taskId)
    console.log('✅ API call successful! Received task:', {
      id: fetchedTask.id,
      title: fetchedTask.title,
      task_type: fetchedTask.task_type,
      status: fetchedTask.status,
      submission_files_count: (fetchedTask as any).submission_files?.length || 0
    })

    task.value = fetchedTask

    // 获取实际投票数据
    currentVotes.value = (fetchedTask as any).vote_count || 0

    // 检查是否已投票（简单模拟）
    hasVoted.value = false

    // 如果是活跃任务或已接取的任务板，启动进度更新
    const taskValue = task.value as any
    if ((taskValue.task_type === 'lock' && taskValue.status === 'active') ||
        (taskValue.task_type === 'board' && taskValue.status === 'taken')) {
      startProgressUpdate()
    }

    // 获取任务时间线
    await fetchTimeline()

    // 检查钥匙持有情况（仅对带锁任务）
    if (fetchedTask.task_type === 'lock') {
      await checkUserHasTaskKey()
    }

  } catch (err: any) {
    console.error('❌ API call failed with error:', {
      message: err.message,
      status: err.status,
      statusText: err.statusText,
      data: err.data,
      fullError: err
    })
    // 使用模拟数据作为备用
    const mockTask: Task = {
      id: taskId,
      user: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        level: 2,
        activity_score: 150,
        last_active: '2024-01-01',
        location_precision: 1,
        coins: 75,
        bio: '热爱挑战的用户',
        total_posts: 8,
        total_likes_received: 25,
        total_tasks_completed: 5,
        total_lock_duration: 0,
        task_completion_rate: 75.0,
        created_at: '2023-12-01',
        updated_at: '2024-01-01'
      },
      title: '专注学习挑战',
      description: '在学习期间保持专注，不使用社交媒体和娱乐应用。这是一个测试意志力和自律能力的挑战任务。完成后将获得成就感和积分奖励。',
      task_type: 'lock' as const,
      duration_type: 'fixed' as const,
      duration_value: 240, // 4小时
      difficulty: 'normal' as const,
      unlock_type: 'vote' as const,
      vote_threshold: 3,
      start_time: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1小时前开始
      end_time: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(), // 3小时后结束
      status: 'active' as const,
      created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1天前创建
      updated_at: new Date(Date.now() - 60 * 60 * 1000).toISOString()
    }

    task.value = mockTask
    currentVotes.value = 1 // 模拟当前投票数

    // 如果是活跃任务或已接取的任务板，启动进度更新
    const taskValue = task.value as any
    if ((taskValue.task_type === 'lock' && taskValue.status === 'active') ||
        (taskValue.task_type === 'board' && taskValue.status === 'taken')) {
      startProgressUpdate()
    }

    // 检查钥匙持有情况（仅对带锁任务）
    if (mockTask.task_type === 'lock') {
      await checkUserHasTaskKey()
    }

    // Log the error for debugging
    if (err.status === 404) {
      console.log('Task not found, using mock data')
    } else {
      console.error('Error fetching task, using mock data:', err)
    }
  } finally {
    loading.value = false
  }
}

const startProgressUpdate = () => {
  // Clear any existing interval
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }

  progressInterval.value = window.setInterval(async () => {
    // Always update current time for reactive calculations
    currentTime.value = Date.now()

    // Check if voting period has ended and needs processing
    if (task.value?.status === 'voting' && taskVotingEndTime.value && !votingProcessing.value) {
      const now = currentTime.value
      const votingEndTime = new Date(taskVotingEndTime.value).getTime()

      console.log('⏰ Voting timer check:', {
        now: now,
        votingEndTime: votingEndTime,
        timeRemaining: votingEndTime - now,
        shouldProcess: now >= votingEndTime,
        alreadyProcessing: votingProcessing.value
      })

      if (now >= votingEndTime) {
        // 防止重复处理
        votingProcessing.value = true

        try {
          console.log('🗳️ Voting period ended, processing results...')

          let result = null
          let retryCount = 0
          const maxRetries = 3

          // 重试机制处理API调用
          while (retryCount < maxRetries && !result) {
            try {
              result = await tasksStore.processVotingResults()
              console.log('🗳️ Process voting results API response:', result)
              break
            } catch (apiError: any) {
              retryCount++
              console.warn(`⚠️ API call failed (attempt ${retryCount}/${maxRetries}):`, apiError)

              if (retryCount < maxRetries) {
                // 等待后重试
                await new Promise(resolve => setTimeout(resolve, 1000 * retryCount))
              } else {
                console.error('❌ All API retry attempts failed, will refresh task to check status')
              }
            }
          }

          // 无论API调用是否成功，都刷新任务状态
          await new Promise(resolve => setTimeout(resolve, 1000))
          await fetchTask()

          console.log('✅ Task status after voting period ended:', task.value?.status)

          const taskStatus = task.value?.status as string
          if (taskStatus === 'completed') {
            console.log('🎉 Task was auto-completed after voting passed!')

            // 停止进度更新定时器，因为任务已完成
            if (progressInterval.value) {
              clearInterval(progressInterval.value)
              progressInterval.value = undefined
            }

            // 刷新用户数据以更新lock status
            await authStore.refreshUser()

            // 刷新时间线以显示完成事件
            await fetchTimeline()

            // 显示完成提示
            alert('🎉 投票通过！任务已完成！')
          } else if (taskStatus === 'active') {
            console.log('⏰ Voting failed, task continues with penalty time')

            // 刷新时间线以显示失败事件
            await fetchTimeline()
          } else if (taskStatus === 'voting') {
            console.warn('⚠️ Task still in voting status, may need manual intervention')

            // 如果任务仍在投票状态，继续检查（可能是网络问题或其他临时问题）
            // 不重置 votingProcessing 标志，让下次定时器继续检查
            return
          }

          // Force a reactive update
          currentTime.value = Date.now()

          // Double check final state
          setTimeout(() => {
            console.log('🔘 Final state after voting ended:', {
              taskStatus: task.value?.status,
              canManageTask: canManageTask.value,
              canCompleteTask: canCompleteTask.value,
              isCompleted: task.value?.status === 'completed',
              votingEndTime: taskVotingEndTime.value,
              currentTime: currentTime.value
            })

            // 重置处理标志
            votingProcessing.value = false
          }, 500)
        } catch (error) {
          console.error('❌ Error processing voting results:', error)

          // 即使出错也要刷新任务状态，以防后端已经处理了
          try {
            await fetchTask()
            if (task.value?.status !== 'voting') {
              console.log('✅ Task status updated despite API error:', task.value?.status)
            }
          } catch (fetchError) {
            console.error('❌ Failed to refresh task after API error:', fetchError)
          }

          // 重置处理标志
          votingProcessing.value = false
        }
      }
    }
  }, 1000)
}

const deleteTask = async () => {
  if (!task.value || !confirm('确定要删除这个任务吗？')) {
    return
  }

  try {
    await tasksApi.deleteTask(task.value.id)
    console.log('任务删除成功')
    router.push({ name: 'tasks' })
  } catch (error: any) {
    console.error('Error deleting task:', error)

    // 处理特定错误消息
    let errorMessage = '删除任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限删除此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
  }
}

const startTask = async () => {
  if (!task.value) return

  try {
    const updatedTask = await tasksApi.startTask(task.value.id)
    task.value = updatedTask
    console.log('任务已开始')
    startProgressUpdate()
    // 刷新用户数据以更新lock status
    authStore.refreshUser()
  } catch (error: any) {
    console.error('Error starting task:', error)

    // 处理特定错误消息
    let errorMessage = '开始任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限开始此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
  }
}

const completeTask = async () => {
  if (!task.value) return

  // 第一次确认
  if (!confirm('确定要标记任务为已完成吗？')) {
    return
  }

  // 第二次确认（更加严重的提醒）
  if (!confirm('⚠️ 请再次确认：一旦标记为完成，此操作无法撤销！\n\n确定要完成这个任务吗？')) {
    return
  }

  try {
    const updatedTask = await tasksApi.completeTask(task.value.id)
    task.value = updatedTask
    console.log('任务已完成')
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
    }

    // 刷新钥匙持有状态（钥匙应该已被销毁）
    if (updatedTask.task_type === 'lock') {
      await checkUserHasTaskKey()
    }

    // 刷新用户数据以更新lock status
    authStore.refreshUser()
    alert('✅ 任务已成功完成！钥匙已被销毁。')
  } catch (error: any) {
    console.error('Error completing task:', error)

    // 处理特定错误消息
    let errorMessage = '完成任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限完成此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      // 网络错误或其他客户端错误
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ 完成失败：${errorMessage}`)
  }
}

const stopTask = async () => {
  if (!task.value) return

  // 第一次确认
  if (!confirm('确定要停止这个任务吗？任务将标记为失败。')) {
    return
  }

  // 第二次确认（更加严重的提醒）
  if (!confirm('⚠️ 请再次确认：停止任务将标记为失败，此操作无法撤销！\n\n确定要停止这个任务吗？')) {
    return
  }

  try {
    const updatedTask = await tasksApi.stopTask(task.value.id)
    task.value = updatedTask
    console.log('任务已停止')
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
    }
    // 刷新用户数据以更新lock status
    authStore.refreshUser()
    alert('⚠️ 任务已停止并标记为失败')
  } catch (error: any) {
    console.error('Error stopping task:', error)

    // 处理特定错误消息
    let errorMessage = '停止任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限停止此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      // 网络错误或其他客户端错误
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ 停止失败：${errorMessage}`)
  }
}

const startVoting = async () => {
  if (!task.value || !canStartVoting.value) return

  if (!confirm('确定要发起投票吗？投票期将持续10分钟。')) {
    return
  }

  try {
    const updatedTask = await tasksApi.startVoting(task.value.id)
    task.value = updatedTask
    console.log('投票期已开始')

    // Refresh task data to get updated voting information
    await fetchTask()

    // Refresh user data to update lock status
    await authStore.refreshUser()
  } catch (error) {
    console.error('Error starting voting:', error)
    alert('发起投票失败，请重试')
  }
}

const submitVote = async (agree: boolean) => {
  if (!task.value || hasVoted.value) return

  try {
    await tasksApi.voteTask(task.value.id, agree)

    if (agree) {
      currentVotes.value += 1
    }

    hasVoted.value = true
    closeVoteModal()
    console.log(`投票成功: ${agree ? '同意' : '拒绝'}`)

    // 刷新任务数据以获取最新投票状态
    await fetchTask()

    // 检查是否达到解锁门槛
    if (agree && currentVotes.value >= taskVoteThresholdValue.value) {
      console.log('投票门槛已达到，任务可以解锁')
    }
  } catch (error) {
    console.error('Error voting:', error)
    alert('投票失败，请重试')
    closeVoteModal()
  }
}

const claimTask = async () => {
  if (!task.value || !canClaimTask.value) return

  if (!confirm('确定要揭榜这个任务吗？揭榜后需要在规定时间内完成。')) {
    return
  }

  try {
    const updatedTask = await tasksApi.takeTask(task.value.id)
    task.value = updatedTask
    console.log('任务揭榜成功')
    startProgressUpdate() // 开始进度更新
  } catch (error) {
    console.error('Error claiming task:', error)
    alert('揭榜失败，请重试')
  }
}

const openSubmissionModal = () => {
  showSubmissionModal.value = true
}

const closeSubmissionModal = () => {
  showSubmissionModal.value = false
}

const openUserProfile = (userId: number) => {
  selectedUserId.value = userId
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  selectedUserId.value = undefined
}

const openVoteModal = () => {
  showVoteModal.value = true
}

const closeVoteModal = () => {
  showVoteModal.value = false
}

const handleSubmissionSuccess = () => {
  // Refresh task data to get updated status
  fetchTask()
  // Close the modal
  showSubmissionModal.value = false
}

const approveTask = async () => {
  if (!task.value || !canReviewTask.value) return

  // For multi-person tasks, need to approve individual participants
  if (task.value.task_type === 'board' && task.value.max_participants && task.value.max_participants > 1) {
    // Check if there are submitted participants to review
    const submittedParticipants = task.value.participants?.filter(p => p.status === 'submitted') || []
    if (submittedParticipants.length === 0) {
      alert('没有待审核的参与者提交')
      return
    }

    // Suggest using individual participant review
    alert('这是多人任务，请在参与者列表中逐个审核每位参与者的提交')
    return
  }

  if (!confirm('确定要审核通过这个任务吗？')) {
    return
  }

  try {
    // For single-person board tasks, can use approveTask directly
    const updatedTask = await tasksApi.approveTask(task.value.id)
    task.value = updatedTask

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '审核通过',
      message: '任务已审核通过',
      secondaryMessage: '参与者将获得相应奖励'
    }

    console.log('任务审核通过')
  } catch (error: any) {
    console.error('Error approving task:', error)

    let errorMessage = '审核失败，请重试'
    if (error.data?.error) {
      errorMessage = error.data.error
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '审核失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
  }
}

const rejectTask = async () => {
  if (!task.value || !canReviewTask.value) return

  // For multi-person tasks, need to reject individual participants
  if (task.value.task_type === 'board' && task.value.max_participants && task.value.max_participants > 1) {
    // Check if there are submitted participants to review
    const submittedParticipants = task.value.participants?.filter(p => p.status === 'submitted') || []
    if (submittedParticipants.length === 0) {
      alert('没有待审核的参与者提交')
      return
    }

    // Suggest using individual participant review
    alert('这是多人任务，请在参与者列表中逐个审核每位参与者的提交')
    return
  }

  const rejectReason = prompt('请输入拒绝原因（可选）：')

  if (!confirm('确定要审核拒绝这个任务吗？')) {
    return
  }

  try {
    // For single-person board tasks, can use rejectTask directly
    const updatedTask = await tasksApi.rejectTask(task.value.id, rejectReason || '')
    task.value = updatedTask

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '审核拒绝',
      message: '任务已审核拒绝',
      secondaryMessage: rejectReason ? `拒绝原因：${rejectReason}` : ''
    }

    console.log('任务审核拒绝')
  } catch (error: any) {
    console.error('Error rejecting task:', error)

    let errorMessage = '审核失败，请重试'
    if (error.data?.error) {
      errorMessage = error.data.error
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '审核失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
  }
}

const addOvertime = async () => {
  if (!task.value || !canAddOvertime.value) return

  try {
    const result = await tasksApi.addOvertime(task.value.id)

    // 更新任务结束时间 - 根据冻结状态更新相应字段
    if (task.value && task.value.task_type === 'lock') {
      if (result.is_frozen && result.frozen_end_time) {
        // 冻结状态下更新frozen_end_time
        await nextTick()
        const updatedTask = {
          ...task.value,
          frozen_end_time: String(result.frozen_end_time),
          is_frozen: Boolean(result.is_frozen)
        }
        task.value = updatedTask
      } else if (result.new_end_time) {
        // 非冻结状态下更新end_time
        await nextTick()
        const updatedTask = {
          ...task.value,
          end_time: String(result.new_end_time)
        }
        task.value = updatedTask
      }
    }

    // 刷新用户数据以更新lock status
    authStore.refreshUser()

    // 显示加时信息
    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '随机加时成功',
      message: `成功为任务加时 ${result.overtime_minutes} 分钟！`,
      secondaryMessage: '任务时间已延长，继续加油吧！',
      details: {
        '加时时长': `${result.overtime_minutes} 分钟`,
        '新的结束时间': formatDateTime(result.is_frozen && result.frozen_end_time ? result.frozen_end_time : result.new_end_time)
      }
    }
    console.log('任务加时成功:', result)
  } catch (error: any) {
    console.error('Error adding overtime:', error)

    // 处理特定错误消息
    let errorMessage = '加时失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限为此任务加时'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    // 显示错误通知
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '随机加时失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
  }
}

const endTask = async () => {
  if (!task.value || !canEndTask.value) return

  // 确认对话框
  if (!confirm('确定要结束这个任务吗？结束后将根据当前情况进行结算。')) {
    return
  }

  try {
    const updatedTask = await tasksApi.endTask(task.value.id)
    task.value = updatedTask
    console.log('任务已结束')

    // 刷新用户数据以更新积分等信息
    await authStore.refreshUser()

    // 显示成功提示
    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '任务已结束',
      message: '任务已成功结束并完成结算',
      secondaryMessage: '奖励已根据实际情况分配'
    }

  } catch (error: any) {
    console.error('Error ending task:', error)

    // 处理特定错误消息
    let errorMessage = '结束任务失败，请重试'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限结束此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    // 显示错误提示
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '结束任务失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
  }
}

const returnKeyToOriginalOwner = async () => {
  if (!taskKey.value || !taskKey.value.original_owner) {
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '无法归还',
      message: '钥匙信息不完整',
      secondaryMessage: '请刷新页面后重试'
    }
    return
  }

  const originalOwnerName = taskKey.value.original_owner.username

  try {
    returningKey.value = true

    const result = await storeApi.returnItem(taskKey.value.id)

    // 重新检查钥匙状态
    await checkUserHasTaskKey()

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '钥匙归还成功',
      message: `🔄 已成功将钥匙归还给 ${originalOwnerName}`,
      secondaryMessage: '您已失去对此任务的控制权',
      details: {
        '归还对象': originalOwnerName,
        '操作时间': formatDateTime(new Date().toISOString()),
        '状态变化': '钥匙持有者 → 普通用户'
      }
    }

    console.log('钥匙归还成功:', result)

  } catch (error: any) {
    console.error('Error returning key:', error)

    // 处理特定错误消息
    let errorMessage = '归还钥匙失败，请重试'
    let secondaryMessage = '请稍后重试或联系管理员'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '钥匙不存在或您没有权限归还此钥匙'
    } else if (error.status === 403) {
      errorMessage = '您没有权限归还此钥匙'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '归还失败',
      message: errorMessage,
      secondaryMessage: secondaryMessage
    }
  } finally {
    returningKey.value = false
  }
}

// 钥匙玩法方法
const manualTimeAdjustment = async (type: 'increase' | 'decrease') => {
  if (!task.value || !canAffordTimeAdjustment.value) {
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '操作失败',
      message: '积分不足或无权限进行时间调整',
      secondaryMessage: '请检查您的积分余额和权限设置'
    }
    return
  }

  // 检查剩余时间
  const remaining = timeRemaining.value
  const remainingMinutes = Math.floor(remaining / (1000 * 60))

  if (type === 'decrease' && remaining <= 0) {
    showToast.value = true
    toastData.value = {
      type: 'warning',
      title: '无法减时',
      message: '任务倒计时已结束，无法进行减时操作',
      secondaryMessage: '只能对正在倒计时的任务进行时间调整'
    }
    return
  }

  try {
    const result = await tasksApi.manualTimeAdjustment(task.value.id, type)

    console.log('Manual time adjustment result:', result)
    console.log('result.frozen_end_time type:', typeof result.frozen_end_time)
    console.log('result.frozen_end_time value:', result.frozen_end_time)

    // 更新任务时间 - 根据冻结状态更新相应字段
    if (task.value && task.value.task_type === 'lock') {
      if (result.is_frozen && result.frozen_end_time) {
        // 冻结状态下更新frozen_end_time
        console.log('Updating frozen_end_time (safe):', String(result.frozen_end_time))
        console.log('Result object keys:', Object.keys(result))
        console.log('frozen_end_time type check:', typeof result.frozen_end_time)

        // 使用 nextTick 确保 Vue 反应系统正确处理更新
        await nextTick()

        // 创建新的任务对象避免引用问题
        const updatedTask = {
          ...task.value,
          frozen_end_time: String(result.frozen_end_time),
          is_frozen: Boolean(result.is_frozen)
        }
        task.value = updatedTask
      } else if (result.new_end_time) {
        // 非冻结状态下更新end_time
        await nextTick()
        const updatedTask = {
          ...task.value,
          end_time: String(result.new_end_time)
        }
        task.value = updatedTask
      }
    }

    // 刷新用户数据以更新积分
    await authStore.refreshUser()

    // 刷新任务时间线
    await fetchTimeline()

    // 显示成功消息
    const actionText = type === 'increase' ? '加时' : '减时'
    const adjustmentMinutes = Math.abs(result.adjustment_minutes)

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: `${actionText}成功`,
      message: `已${actionText} ${adjustmentMinutes} 分钟`,
      secondaryMessage: `消耗了 ${result.cost} 积分`,
      details: {
        '调整时间': `${result.adjustment_minutes > 0 ? '+' : ''}${result.adjustment_minutes} 分钟`,
        '消耗积分': `${result.cost} 积分`,
        '剩余积分': `${result.remaining_coins} 积分`,
        '新的结束时间': formatDateTime(result.is_frozen && result.frozen_end_time ? result.frozen_end_time : result.new_end_time)
      }
    }

    console.log('手动时间调整成功:', result)
  } catch (error: any) {
    console.error('Error adjusting time:', error)

    // 处理特定错误消息
    let errorMessage = '时间调整失败，请重试'
    let secondaryMessage = '请稍后重试或联系管理员'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限调整此任务的时间'
    } else if (error.status === 400) {
      errorMessage = '积分不足或操作无效'
      secondaryMessage = '请检查您的积分余额'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '操作失败',
      message: errorMessage,
      secondaryMessage: secondaryMessage
    }
  }
}

const toggleTimeDisplay = async () => {
  if (!task.value || !canAffordTimeToggle.value) {
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '操作失败',
      message: '积分不足或无权限切换时间显示',
      secondaryMessage: '切换时间显示需要50积分，请检查您的余额'
    }
    return
  }

  try {
    const result = await tasksApi.toggleTimeDisplay(task.value.id)

    // 更新任务的时间显示状态
    if (task.value && task.value.task_type === 'lock') {
      (task.value as any).time_display_hidden = result.time_display_hidden
    }

    // 刷新用户数据以更新积分
    await authStore.refreshUser()

    // 刷新任务时间线
    await fetchTimeline()

    // 显示成功消息
    const statusText = result.time_display_hidden ? '隐藏' : '显示'
    const statusIcon = result.time_display_hidden ? '🙈' : '👁️'

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: `时间${statusText}成功`,
      message: `${statusIcon} 时间显示已${statusText}`,
      secondaryMessage: `消耗了 ${result.cost} 积分`,
      details: {
        '当前状态': result.time_display_hidden ? '🌫️ 时间已隐藏' : '👁️ 时间可见',
        '消耗积分': `${result.cost} 积分`,
        '剩余积分': `${result.remaining_coins} 积分`
      }
    }

    console.log('时间显示切换成功:', result)
  } catch (error: any) {
    console.error('Error toggling time display:', error)

    // 处理特定错误消息
    let errorMessage = '时间显示切换失败，请重试'
    let secondaryMessage = '请稍后重试或联系管理员'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限切换此任务的时间显示'
    } else if (error.status === 400) {
      errorMessage = '积分不足或操作无效'
      secondaryMessage = '请检查您的积分余额'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '操作失败',
      message: errorMessage,
      secondaryMessage: secondaryMessage
    }
  }
}

const pinTaskOwner = async () => {
  if (!task.value || !canAffordPinning.value) {
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '操作失败',
      message: '积分不足或无权限进行置顶操作',
      secondaryMessage: '置顶惩罚需要60积分，请检查您的余额'
    }
    return
  }

  pinningInProgress.value = true

  try {
    const result = await tasksApi.pinTaskOwner(task.value.id, 60, 30)

    // 刷新用户数据以更新积分
    await authStore.refreshUser()

    // 刷新任务时间线
    await fetchTimeline()

    // 显示成功消息
    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '置顶惩罚成功',
      message: `📌 ${task.value.user.username} 已被置顶30分钟`,
      secondaryMessage: '置顶期间他人加时效果×10',
      details: {
        '置顶用户': task.value.user.username,
        '置顶时长': '30分钟',
        '消耗积分': '60积分',
        '剩余积分': `${result.coins_remaining}积分`,
        '队列位置': result.position ? `第${result.position}位` : '排队中'
      }
    }

    console.log('置顶惩罚成功:', result)
  } catch (error: any) {
    console.error('Error pinning task owner:', error)

    // 处理特定错误消息
    let errorMessage = '置顶操作失败，请重试'
    let secondaryMessage = '请稍后重试或联系管理员'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限置顶此任务的创建者'
    } else if (error.status === 400) {
      errorMessage = '积分不足或操作无效'
      secondaryMessage = '请检查您的积分余额'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '置顶失败',
      message: errorMessage,
      secondaryMessage: secondaryMessage
    }
  } finally {
    pinningInProgress.value = false
  }
}

// Freeze/Unfreeze methods
const freezeTask = async () => {
  if (!task.value || !canAffordFreeze.value) {
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '冻结失败',
      message: '积分不足或无权限冻结任务',
      secondaryMessage: '冻结任务需要25积分，请检查您的余额'
    }
    return
  }

  freezingInProgress.value = true

  try {
    const result = await tasksApi.freezeTask(task.value.id)

    // 刷新用户数据以更新积分
    await authStore.refreshUser()

    // 刷新任务数据
    await fetchTask()

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '冻结成功',
      message: `❄️ 任务已成功冻结`,
      secondaryMessage: '任务倒计时已停止，您可以随时解冻恢复',
      details: {
        '消耗积分': '25',
        '剩余积分': result.remaining_coins || 0,
        '操作时间': formatDateTime(new Date().toISOString()),
        '状态变化': '进行中 → 已冻结'
      }
    }

    console.log('任务冻结成功:', result)

  } catch (error: any) {
    console.error('Error freezing task:', error)

    let errorMessage = '冻结任务失败，请重试'
    let secondaryMessage = '请稍后重试或联系管理员'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 400) {
      errorMessage = '任务状态不允许冻结或积分不足'
    } else if (error.status === 403) {
      errorMessage = '您没有权限冻结此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '冻结失败',
      message: errorMessage,
      secondaryMessage: secondaryMessage
    }
  } finally {
    freezingInProgress.value = false
  }
}

const unfreezeTask = async () => {
  if (!task.value || !canAffordFreeze.value) {
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '解冻失败',
      message: '积分不足或无权限解冻任务',
      secondaryMessage: '解冻任务需要25积分，请检查您的余额'
    }
    return
  }

  freezingInProgress.value = true

  try {
    const result = await tasksApi.unfreezeTask(task.value.id)

    // 刷新用户数据以更新积分
    await authStore.refreshUser()

    // 刷新任务数据
    await fetchTask()

    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '解冻成功',
      message: `🔥 任务已成功解冻`,
      secondaryMessage: '任务倒计时已恢复，从剩余时间继续',
      details: {
        '消耗积分': '25',
        '剩余积分': result.remaining_coins || 0,
        '操作时间': formatDateTime(new Date().toISOString()),
        '状态变化': '已冻结 → 进行中'
      }
    }

    console.log('任务解冻成功:', result)

  } catch (error: any) {
    console.error('Error unfreezing task:', error)

    let errorMessage = '解冻任务失败，请重试'
    let secondaryMessage = '请稍后重试或联系管理员'

    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 400) {
      errorMessage = '任务状态不允许解冻或积分不足'
    } else if (error.status === 403) {
      errorMessage = '您没有权限解冻此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '解冻失败',
      message: errorMessage,
      secondaryMessage: secondaryMessage
    }
  } finally {
    freezingInProgress.value = false
  }
}

// Multi-person task participant management methods (review mode removed)

const canReviewParticipant = (participant: any) => {
  if (!task.value || !authStore.user) return false

  // Only task publisher can review
  const isTaskPublisher = authStore.user.id === task.value.user.id

  // Cannot review if task is completed
  if (task.value.status === 'completed') return false

  // Can only review submitted participants
  return isTaskPublisher && participant.status === 'submitted'
}

const approveParticipant = async (participant: any) => {
  if (!task.value || !canReviewParticipant(participant)) return

  try {
    await tasksApi.approveParticipant(task.value.id, participant.id)

    // Refresh task data to get updated participant status
    await fetchTask()

    // Show success message
    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '审核通过',
      message: `已审核通过 ${participant.participant.username} 的提交`,
      secondaryMessage: '参与者将获得相应奖励'
    }


    console.log('参与者审核通过:', participant.participant.username)
  } catch (error: any) {
    console.error('Error approving participant:', error)

    let errorMessage = '审核失败，请重试'
    if (error.data?.error) {
      errorMessage = error.data.error
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '审核失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
  }
}

const rejectParticipant = async (participant: any) => {
  if (!task.value || !canReviewParticipant(participant)) return

  const rejectReason = prompt('请输入拒绝原因（可选）：')

  try {
    await tasksApi.rejectParticipant(task.value.id, participant.id, rejectReason || '')

    // Refresh task data to get updated participant status
    await fetchTask()

    // Show success message
    showToast.value = true
    toastData.value = {
      type: 'warning',
      title: '审核拒绝',
      message: `已拒绝 ${participant.participant.username} 的提交`,
      secondaryMessage: rejectReason ? `拒绝原因: ${rejectReason}` : '已通知参与者重新提交'
    }


    console.log('参与者审核拒绝:', participant.participant.username)
  } catch (error: any) {
    console.error('Error rejecting participant:', error)

    let errorMessage = '审核失败，请重试'
    if (error.data?.error) {
      errorMessage = error.data.error
    }

    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '审核失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
  }
}

const getParticipantStatusText = (status: string) => {
  const statusTexts = {
    joined: '已参与',
    submitted: '已提交',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return statusTexts[status as keyof typeof statusTexts] || status
}

const getParticipantStatusClass = (status: string) => {
  const statusClasses = {
    joined: 'participant-joined',
    submitted: 'participant-submitted',
    approved: 'participant-approved',
    rejected: 'participant-rejected'
  }
  return statusClasses[status as keyof typeof statusClasses] || 'participant-unknown'
}

const getParticipantCardClass = (status: string) => {
  const cardClasses = {
    joined: 'participant-card-joined',
    submitted: 'participant-card-submitted',
    approved: 'participant-card-approved',
    rejected: 'participant-card-rejected'
  }
  return cardClasses[status as keyof typeof cardClasses] || 'participant-card-default'
}

const getGenericFileName = (file: any, index: number) => {
  if (file.file_name) {
    return file.file_name
  }
  const extension = file.file_type ? `.${file.file_type.toLowerCase()}` : ''
  return `文件${index + 1}${extension}`
}

const getFileUrl = (file: any) => {
  return file.file_url || file.file
}

const isImageFile = (file: any) => {
  return file.is_image || false
}

const handleFileClick = (file: any) => {
  if (isImageFile(file)) {
    openImageModal(file)
  } else {
    // Download file
    window.open(getFileUrl(file), '_blank')
  }
}

const handleImageError = (event: Event) => {
  console.error('Image failed to load:', event)
}

const getTaskTypeText = (type: string) => {
  const texts = {
    time: '定时解锁',
    vote: '投票解锁'
  }
  return texts[type as keyof typeof texts] || type
}

const getDifficultyText = (difficulty: string) => {
  const texts = {
    easy: '简单',
    normal: '普通',
    hard: '困难',
    hell: '地狱'
  }
  return texts[difficulty as keyof typeof texts] || difficulty
}

const getStatusText = (status: string) => {
  if (!task.value) return status

  const isMultiPerson = task.value.task_type === 'board' && task.value.max_participants > 1

  if (isMultiPerson) {
    // 多人任务状态文本
    const multiPersonTexts = {
      pending: '待开始',
      active: '进行中',
      voting: '投票期',
      completed: '已完成',
      failed: '已失败',
      open: '招募中',
      taken: `进行中 (${(task.value as any).participant_count || 0}/${(task.value as any).max_participants || 0})`,
      submitted: `审核中 (${(task.value as any).participant_count || 0}/${(task.value as any).max_participants || 0})`
    }
    return multiPersonTexts[status as keyof typeof multiPersonTexts] || status
  } else {
    // 单人任务状态文本
    const singlePersonTexts = {
      pending: '待开始',
      active: '进行中',
      voting: '投票期',
      completed: '已完成',
      failed: '已失败',
      open: '开放中',
      taken: '已接取',
      submitted: '已提交'
    }
    return singlePersonTexts[status as keyof typeof singlePersonTexts] || status
  }
}

const formatDuration = (task: Task) => {
  if (task.task_type !== 'lock') return ''
  const lockTask = task as any
  const hours = Math.floor(lockTask.duration_value / 60)
  const minutes = lockTask.duration_value % 60

  if (lockTask.duration_type === 'random' && lockTask.duration_max) {
    const maxHours = Math.floor(lockTask.duration_max / 60)
    const maxMinutes = lockTask.duration_max % 60
    return `${hours}小时${minutes}分钟 - ${maxHours}小时${maxMinutes}分钟`
  }

  return `${hours}小时${minutes}分钟`
}

const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN')
}

const formatTimeRemaining = (milliseconds: number) => {
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

const formatVotingTimeRemaining = () => {
  return formatTimeRemaining(votingTimeRemaining.value)
}

const getEventTypeClass = (eventType: string) => {
  const classMap: Record<string, string> = {
    'task_created': 'created',
    'task_started': 'start',
    'task_completed': 'completed',
    'task_stopped': 'failed',
    'time_wheel_increase': 'time-increase',
    'time_wheel_decrease': 'time-decrease',
    'overtime_added': 'overtime',
    'task_voted': 'vote',
    'task_failed': 'failed'
  }
  return classMap[eventType] || 'default'
}

// Media file helper functions
const openImageModal = (file: any) => {
  selectedImage.value = file
  showImageModal.value = true
}

const closeImageModal = () => {
  showImageModal.value = false
  selectedImage.value = null
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// Get proof status text based on task status
const getProofStatusText = (status: string) => {
  const statusTexts = {
    submitted: '待审核',
    completed: '审核通过',
    failed: '审核拒绝',
    rejected: '审核拒绝'
  }
  return statusTexts[status as keyof typeof statusTexts] || '未知状态'
}

// Get proof status CSS class based on task status
const getProofStatusClass = (status: string) => {
  const statusClasses = {
    submitted: 'proof-status-pending',
    completed: 'proof-status-approved',
    failed: 'proof-status-rejected',
    rejected: 'proof-status-rejected'
  }
  return statusClasses[status as keyof typeof statusClasses] || 'proof-status-unknown'
}

// Watch for route parameter changes (when navigating between different tasks)
watch(() => route.params.id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    console.log(`Route parameter changed from ${oldId} to ${newId}, refetching task...`)
    // Reset state
    task.value = null
    loading.value = true
    error.value = ''
    timeline.value = []

    // Fetch new task data
    await fetchTask()
  }
}, { immediate: false })

// Watch for task changes to refresh timeline
watch(() => task.value?.updated_at, async (newUpdatedAt, oldUpdatedAt) => {
  if (newUpdatedAt && oldUpdatedAt && newUpdatedAt !== oldUpdatedAt) {
    console.log('Task updated, refreshing timeline...')
    await fetchTimeline()
  }
})

// Also watch for status changes
watch(() => task.value?.status, async (newStatus, oldStatus) => {
  if (newStatus && oldStatus && newStatus !== oldStatus) {
    console.log('📊 Task status changed from', oldStatus, 'to', newStatus)
    console.log('🔄 Refreshing timeline and checking button visibility...')
    await fetchTimeline()

    // Log button states after status change
    setTimeout(() => {
      console.log('🔘 Button visibility after status change:', {
        taskStatus: task.value?.status,
        canManageTask: canManageTask.value,
        canCompleteTask: canCompleteTask.value,
        stopButtonVisible: (task.value?.status === 'active' || task.value?.status === 'voting') && canManageTask.value,
        completeButtonVisible: task.value?.status === 'active' && canManageTask.value && canCompleteTask.value
      })
    }, 100)
  }
})

// Watch for timeline data changes and trigger scroll on mobile
watch(() => timeline.value.length, (newLength, oldLength) => {
  if (newLength > 0 && newLength !== oldLength && window.innerWidth <= 768) {
    console.log('📱 Timeline data changed, triggering scroll to newest event')
    nextTick(() => {
      scrollToNewestEvent()
    })
  }
})

// Watch for end_time changes (from time wheel)
watch(() => taskEndTime.value, async (newEndTime, oldEndTime) => {
  if (newEndTime && oldEndTime && newEndTime !== oldEndTime) {
    console.log('Task end time changed, refreshing timeline...')
    await fetchTimeline()
  }
})

// Keyboard navigation (review mode removed)

onMounted(() => {
  fetchTask()

  // Add window resize listener to handle orientation changes
  window.addEventListener('resize', () => {
    // Debounce resize events
    clearTimeout(resizeTimeout.value)
    resizeTimeout.value = setTimeout(() => {
      if (window.innerWidth <= 768 && timeline.value.length > 0) {
        console.log('🔄 Window resized to mobile, scrolling to newest event')
        scrollToNewestEvent()
      }
    }, 300)
  })
})

// Add resize timeout ref
const resizeTimeout = ref<number>()

// Add intersection observer ref
const timelineObserver = ref<IntersectionObserver | null>(null)

onUnmounted(() => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }

  // Clear resize timeout
  if (resizeTimeout.value) {
    clearTimeout(resizeTimeout.value)
  }

  // Disconnect intersection observer
  if (timelineObserver.value) {
    timelineObserver.value.disconnect()
  }

  // Remove window resize listener
  window.removeEventListener('resize', scrollToNewestEvent)

  // Cleanup (review mode navigation removed)
})
</script>

<style scoped>
.task-detail {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.header {
  background: white;
  border-bottom: 2px solid #000;
  padding: 1rem 0;
}

.header-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn, .delete-btn, .share-btn {
  background: none;
  border: 1px solid #666;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.back-btn:hover {
  background-color: #f8f9fa;
}

.share-btn {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
  margin-right: 0.5rem;
}

.share-btn:hover {
  background-color: #0056b3;
}

.delete-btn {
  background-color: #dc3545;
  color: white;
  border-color: #dc3545;
}

.delete-btn:hover {
  background-color: #c82333;
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.main-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.loading, .error {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  text-align: center;
}

.error {
  color: #dc3545;
  background-color: #f8d7da;
  border-color: #dc3545;
}

.task-detail-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.task-card, .actions-section, .voting-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e9ecef;
}

.task-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0 0 0.5rem 0;
  color: #333;
}

.task-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.task-type, .task-difficulty, .task-status {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: bold;
  text-transform: uppercase;
}

.task-type {
  background-color: #17a2b8;
  color: white;
}

.task-difficulty.easy {
  background-color: #28a745;
  color: white;
}

.task-difficulty.normal {
  background-color: #ffc107;
  color: #212529;
}

.task-difficulty.hard {
  background-color: #fd7e14;
  color: white;
}

.task-difficulty.hell {
  background-color: #dc3545;
  color: white;
}

.task-status.pending {
  background-color: #6c757d;
  color: white;
}

.task-status.active {
  background-color: #007bff;
  color: white;
}

.task-status.completed {
  background-color: #28a745;
  color: white;
}

.task-status.failed {
  background-color: #dc3545;
  color: white;
}

.task-status.open {
  background-color: #28a745;
  color: white;
}

.task-status.taken {
  background-color: #fd7e14;
  color: white;
}

.task-status.submitted {
  background-color: #6f42c1;
  color: white;
}

.task-status.voting {
  background-color: #ffc107;
  color: #212529;
  animation: pulse 2s infinite;
}

.task-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}


.username {
  font-weight: bold;
  font-size: 1.1rem;
}

.username-btn {
  background: none;
  border: 2px solid transparent;
  font-weight: 700;
  font-size: 1.1rem;
  text-decoration: underline;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  margin: -0.25rem -0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.username-btn:hover {
  color: white;
  text-decoration: none;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
  border-color: #000;
}

/* Level-specific hover effects */
.username-btn.level-1:hover {
  background-color: #6c757d !important;
  color: white !important;
}

.username-btn.level-2:hover {
  background-color: #17a2b8 !important;
  color: white !important;
}

.username-btn.level-3:hover {
  background-color: #ffc107 !important;
  color: white !important;
}

.username-btn.level-4:hover {
  background-color: #fd7e14 !important;
  color: white !important;
}

.create-time {
  font-size: 0.875rem;
  color: #666;
}

.task-description {
  margin-bottom: 2rem;
}

.task-description h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.task-description p {
  line-height: 1.6;
  color: #555;
}

.task-description-content {
  line-height: 1.6;
  color: #555;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.task-description-content h1,
.task-description-content h2,
.task-description-content h3 {
  margin: 0.5rem 0;
  font-weight: 900;
  color: #333;
}

.task-description-content h1 {
  font-size: 1.5rem;
}

.task-description-content h2 {
  font-size: 1.3rem;
}

.task-description-content h3 {
  font-size: 1.1rem;
}

.task-description-content ul {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.task-description-content li {
  margin: 0.25rem 0;
}

.task-description-content strong {
  font-weight: 900;
}

.task-description-content em {
  font-style: italic;
}

.no-description {
  color: #999;
  font-style: italic;
}

.task-details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.label {
  font-weight: 500;
  color: #666;
  font-size: 0.875rem;
}

.value {
  font-weight: bold;
  color: #333;
}

.countdown-display {
  font-size: 1.1rem;
  font-weight: 900;
  color: #007bff;
  animation: pulse-countdown 2s infinite;
}

.countdown-display.overtime {
  color: #dc3545;
  animation: pulse-danger 1s infinite;
}

@keyframes pulse-countdown {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

@keyframes pulse-danger {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.task-timeline {
  margin-bottom: 2rem;
}

.task-timeline h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.timeline-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  transition: all 0.3s ease;
  z-index: 3;
  position: relative;
}

.timeline-dot:hover {
  transform: scale(1.2);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

.timeline-dot.start {
  background-color: #28a745;
}

.timeline-dot.end {
  background-color: #dc3545;
}

.timeline-title {
  font-weight: bold;
}

.timeline-time {
  font-size: 0.875rem;
  color: #666;
}

.task-progress-section {
  margin-bottom: 2rem;
}

.task-progress-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.progress-container {
  margin-bottom: 1rem;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background-color: #007bff;
  transition: width 0.5s ease;
}

.progress-text {
  font-weight: bold;
  color: #007bff;
}

.time-remaining {
  font-size: 1.1rem;
  font-weight: 500;
}

.overtime {
  color: #dc3545;
}

.completion-hint {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  text-align: center;
}

.hint-vote {
  background-color: #e7f3ff;
  border: 1px solid #b3d9ff;
  color: #0066cc;
}

.hint-waiting {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
}

.hint-ready {
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
  animation: pulse 2s infinite;
}

.hint-loading {
  background-color: #e2e3e5;
  border: 1px solid #ced4da;
  color: #495057;
}

.hint-no-key {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  font-weight: 600;
}

.key-holder-link {
  background: #17a2b8;
  color: white;
  border: 3px solid #000;
  padding: 0.25rem 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  margin: 0 0.25rem;
  display: inline-block;
  text-decoration: none;
}

.key-holder-link:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
  background: #138496;
}

.key-management {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
}

.key-return-info {
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: #495057;
  text-align: center;
}

.return-key-btn {
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #17a2b8, #20c997);
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.return-key-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
  background: linear-gradient(135deg, #138496, #1e9b85);
}

.return-key-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 2px 2px 0 #000;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
  100% {
    opacity: 1;
  }
}

.action-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  color: white;
}

.start-btn {
  background-color: #28a745;
}

.start-btn:hover {
  background-color: #218838;
}

.complete-btn {
  background-color: #007bff;
}

.complete-btn:hover {
  background-color: #0056b3;
}

.stop-btn {
  background-color: #dc3545;
}

.stop-btn:hover {
  background-color: #c82333;
}

.claim-btn {
  background-color: #ffc107;
  color: #212529;
}

.claim-btn:hover {
  background-color: #e0a800;
}

.submit-btn {
  background-color: #17a2b8;
  color: white;
}

.submit-btn:hover {
  background-color: #138496;
}

.approve-btn {
  background-color: #28a745;
  color: white;
}

.approve-btn:hover {
  background-color: #218838;
}

.reject-btn {
  background-color: #dc3545;
  color: white;
}

.reject-btn:hover {
  background-color: #c82333;
}

.overtime-btn {
  background-color: #fd7e14;
  color: white;
}

.overtime-btn:hover {
  background-color: #e76500;
}

.voting-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.vote-info {
  margin-bottom: 1rem;
}

.vote-count {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.vote-bar {
  width: 100%;
  height: 16px;
  background-color: #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.vote-fill {
  height: 100%;
  background-color: #ffc107;
  transition: width 0.3s ease;
}

.vote-btn {
  background-color: #ffc107;
  color: #212529;
  border: none;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

.vote-btn:hover {
  background-color: #e0a800;
}

.voted-message {
  color: #28a745;
  font-weight: 500;
  font-size: 1.1rem;
}

.vote-countdown-notice {
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 8px;
  color: #856404;
  font-weight: 500;
  text-align: center;
  margin-bottom: 1rem;
  animation: pulse-countdown-notice 2s infinite;
}

@keyframes pulse-countdown-notice {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.vote-actions {
  margin-top: 1rem;
}

.vote-disabled-message {
  color: #6c757d;
  font-weight: 500;
  font-size: 1rem;
  text-align: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 8px;
}

/* Voting period specific styles */
.voting-waiting {
  margin-bottom: 1rem;
}

.vote-ready-notice {
  padding: 1rem;
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border: 2px solid #28a745;
  border-radius: 8px;
  color: #155724;
  font-weight: 500;
  text-align: center;
  animation: pulse-ready 2s infinite;
}

.voting-active {
  margin-bottom: 1rem;
}

.voting-period-info {
  padding: 1.5rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 8px;
  color: #856404;
}

.voting-period-info h4 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
  text-align: center;
}

.voting-countdown {
  font-size: 1.1rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 0.5rem;
}

.voting-schedule {
  font-size: 0.875rem;
  text-align: center;
  opacity: 0.8;
}

.vote-breakdown {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
  font-family: 'Courier New', monospace;
}

.voting-ended-message {
  padding: 1rem;
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border: 2px solid #dc3545;
  border-radius: 8px;
  color: #721c24;
  font-weight: 500;
  text-align: center;
  animation: pulse-warning 2s infinite;
}

@keyframes pulse-ready {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.02); }
}

.vote-waiting-notice {
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 8px;
  color: #856404;
  font-weight: 500;
  text-align: center;
  margin-bottom: 1rem;
}

.start-vote-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  border: 2px solid #000;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  animation: pulse-ready 2s infinite;
}

.start-vote-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

@keyframes pulse-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Voting Results */
.voting-results {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #6c757d;
  border-radius: 8px;
}

.voting-results h4 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
  text-align: center;
  color: #333;
}

.voting-result-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.result-label {
  font-weight: 500;
  color: #666;
  font-size: 0.875rem;
}

.result-value {
  font-weight: bold;
  color: #333;
  font-size: 0.875rem;
}

.voting-conclusion {
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  font-weight: 500;
}

.voting-passed {
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border: 2px solid #28a745;
  color: #155724;
  animation: pulse-success 2s infinite;
}

.voting-failed {
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border: 2px solid #dc3545;
  color: #721c24;
}

.failure-reasons {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  text-align: left;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
}

.failure-reasons div {
  margin: 0.25rem 0;
}

/* Quick Actions Bar */
.quick-actions-bar {
  background: white;
  border: 4px solid #000;
  padding: 1.5rem;
  box-shadow: 8px 8px 0 #000;
  margin-bottom: 2rem;
  position: sticky;
  top: 0;
  z-index: 10;
}

.quick-actions-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.actions-primary {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
}

.actions-secondary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: center;
}

.quick-action-btn {
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  padding: 0.75rem 1.5rem;
}

.quick-action-btn.large {
  font-size: 1rem;
  padding: 1rem 2rem;
  box-shadow: 6px 6px 0 #000;
}

.quick-action-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 8px 8px 0 #000;
}

.quick-action-btn.large:hover {
  transform: translate(-2px, -2px);
  box-shadow: 10px 10px 0 #000;
}

.quick-action-btn.primary {
  background: #007bff;
  color: white;
}

.quick-action-btn.success {
  background: #28a745;
  color: white;
}

.quick-action-btn.danger {
  background: #dc3545;
  color: white;
}

.quick-action-btn.warning {
  background: #ffc107;
  color: #000;
}

.quick-action-btn.info {
  background: #17a2b8;
  color: white;
}

.quick-action-btn.vote {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: #000;
  border-width: 4px;
}

.quick-action-btn.secondary {
  background: #fd7e14;
  color: white;
}

.quick-action-btn.pulse {
  animation: pulse-vote 2s infinite;
}

@keyframes pulse-vote {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
}

/* Optimize quick actions bar for mobile layout with sticky positioning */
@media (max-width: 768px) {
  .quick-actions-bar {
    position: sticky;
    top: 0;
    padding: 1rem;
    margin-bottom: 1.5rem;
    z-index: 100;
    background: white;
    border: 3px solid #000;
    box-shadow: 6px 6px 0 #000;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }

  .actions-primary {
    flex-direction: column;
    align-items: stretch;
  }

  .actions-secondary {
    flex-direction: column;
    align-items: stretch;
  }

  .quick-action-btn {
    width: 100%;
    justify-content: center;
    text-align: center;
  }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 0.75rem;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .header h1 {
    font-size: 1.25rem;
    margin: 0;
    flex: 1;
    text-align: center;
    order: 2;
    width: 100%;
  }

  .back-btn {
    order: 1;
    flex-shrink: 0;
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    min-width: auto;
  }

  .header-actions {
    order: 3;
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
    width: 100%;
    justify-content: center;
    margin-top: 0.5rem;
  }

  .share-btn, .delete-btn {
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    border-radius: 6px;
    flex: 1;
    max-width: 120px;
    text-align: center;
    white-space: nowrap;
  }

  .share-btn {
    background-color: #17a2b8;
    color: white;
    border-color: #17a2b8;
  }

  .share-btn:hover {
    background-color: #138496;
    border-color: #117a8b;
  }

  .delete-btn {
    background-color: #dc3545;
    color: white;
    border-color: #dc3545;
  }

  .delete-btn:hover {
    background-color: #c82333;
    border-color: #bd2130;
  }

  .main-content {
    padding: 1rem;
  }

  .task-card, .actions-section, .voting-section {
    padding: 1rem;
  }

  .task-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .task-details-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }

  .action-btn {
    width: 100%;
  }
}

/* Small mobile screens - additional responsive breakpoint */
@media (max-width: 480px) {
  .header-content {
    padding: 0 0.5rem;
    gap: 0.5rem;
  }

  .header h1 {
    font-size: 1.1rem;
    margin: 0;
  }

  .back-btn {
    padding: 0.4rem 0.6rem;
    font-size: 0.75rem;
  }

  .header-actions {
    gap: 0.4rem;
    margin-top: 0.4rem;
  }

  .share-btn, .delete-btn {
    padding: 0.4rem 0.6rem;
    font-size: 0.75rem;
    max-width: 100px;
  }

  .main-content {
    padding: 0.75rem;
  }

  .task-card, .actions-section, .voting-section {
    padding: 0.75rem;
  }
}

/* Timeline styles */
.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.timeline-header h3 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.refresh-timeline-btn {
  background: #007bff;
  color: white;
  border: 2px solid #000;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.refresh-timeline-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.refresh-timeline-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  animation: spin 1s linear infinite;
}

.timeline-loading {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 1rem;
}

/* Desktop Timeline (Vertical) - Keep original styles */
.desktop-timeline {
  max-height: 400px;
  overflow-y: auto;
  padding: 0.5rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #fafafa;
}

/* Hide mobile timeline on desktop */
.mobile-timeline {
  display: none;
}

/* Mobile Timeline Styles - Only show on mobile */
@media (max-width: 768px) {
  /* Hide desktop timeline on mobile */
  .desktop-timeline {
    display: none;
  }

  /* Show mobile timeline */
  .mobile-timeline {
    display: block;
  }

  .horizontal-timeline-wrapper {
    position: relative;
    margin-bottom: 1rem;
    overflow-x: auto;
    overflow-y: hidden; /* Prevent vertical scrollbar */
    padding: 0;
    /* Custom scrollbar for webkit browsers */
    scrollbar-width: thin;
    scrollbar-color: #6c757d #e9ecef;
    /* Touch scrolling for iOS */
    -webkit-overflow-scrolling: touch;
    /* Ensure wrapper adapts to content height */
    height: auto;
  }

  .horizontal-timeline-wrapper::-webkit-scrollbar {
    height: 8px;
  }

  .horizontal-timeline-wrapper::-webkit-scrollbar-track {
    background: #e9ecef;
    border-radius: 4px;
  }

  .horizontal-timeline-wrapper::-webkit-scrollbar-thumb {
    background: #6c757d;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .horizontal-timeline-wrapper::-webkit-scrollbar-thumb:hover {
    background: #495057;
  }

  .horizontal-timeline-container {
    position: relative;
    padding: 2rem 1rem 2rem 1rem; /* Remove extra bottom padding */
    scroll-behavior: smooth;
    background: linear-gradient(135deg, #f8f9fa, #e9ecef);
    border: 2px solid #dee2e6;
    border-radius: 12px;
    /* Allow height to grow with content */
    min-height: 200px;
    height: auto;
    /* Width will be set dynamically via inline style */
    display: inline-block;
    /* Ensure container expands to contain absolutely positioned children */
    overflow: visible;
  }

  .timeline-track {
    position: absolute;
    top: 3rem;
    left: 1rem;
    /* Dynamic width based on content, subtract padding */
    width: calc(100% - 2rem);
    max-width: calc(var(--timeline-items, 1) * 280px);
    height: 3px;
    background: linear-gradient(90deg, #007bff, #6f42c1, #e83e8c, #fd7e14, #ffc107);
    border-radius: 2px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .horizontal-timeline-item {
    position: absolute;
    top: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 260px;
    margin: 0 10px;
  }

  .timeline-dot-wrapper {
    position: relative;
    z-index: 2;
    margin-bottom: 1rem;
  }

  .timeline-connector {
    position: absolute;
    top: 50%;
    left: 100%;
    width: 280px;
    height: 3px;
    background: linear-gradient(90deg, rgba(0,123,255,0.8), rgba(111,66,193,0.8));
    transform: translateY(-50%);
    border-radius: 2px;
  }

  .timeline-card {
    background: white;
    border: 2px solid #dee2e6;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
    width: 100%;
    max-width: 260px;
    /* Allow content to wrap and expand height */
    min-height: 180px;
    height: auto;
    white-space: normal;
    word-wrap: break-word;
    display: flex;
    flex-direction: column;
  }

  .timeline-card-header {
    border-bottom: 1px solid #e9ecef;
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .timeline-card-body {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    flex: 1;
  }

}

/* Additional mobile optimizations */
@media (max-width: 768px) {
  .timeline-title {
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.2;
    word-break: break-word;
  }

  .timeline-time {
    font-size: 0.75rem;
  }

  .timeline-description {
    font-size: 0.85rem;
    line-height: 1.4;
    word-break: break-word;
    hyphens: auto;
    overflow-wrap: break-word;
    white-space: normal;
  }

  .timeline-dot {
    width: 16px;
    height: 16px;
    border-width: 2px;
  }

  .timeline-connector {
    width: 236px;
    height: 2px;
  }

  .scroll-hint-text {
    font-size: 0.8rem;
  }

  /* Ensure timeline container doesn't overflow parent */
  .horizontal-timeline-container {
    box-sizing: border-box;
  }

  /* Improve text wrapping and card layout */
  .timeline-card .timeline-description,
  .timeline-card .timeline-user,
  .timeline-card .timeline-time-change,
  .timeline-card .timeline-times {
    word-wrap: break-word;
    overflow-wrap: break-word;
    white-space: normal;
  }

  .timeline-user-btn {
    word-break: break-all;
    max-width: 100%;
  }

  /* Adjust card height for content */
  .timeline-card {
    min-height: 120px;
    height: auto;
    display: flex;
    flex-direction: column;
  }

  .timeline-card-body {
    flex: 1;
  }
}

@media (max-width: 480px) {
  .horizontal-timeline-container {
    padding: 1.5rem 0.5rem 1.5rem 0.5rem;
    min-height: 240px;
  }

  .timeline-track {
    top: 2.5rem;
    left: 0.5rem;
  }

  .horizontal-timeline-item {
    width: 180px;
    margin: 0 6px;
  }

  .timeline-card {
    max-width: 180px;
    padding: 0.75rem;
    min-height: 160px;
  }

  .timeline-title {
    font-size: 0.85rem;
  }

  .timeline-time {
    font-size: 0.7rem;
  }

  .timeline-description {
    font-size: 0.8rem;
    line-height: 1.4;
  }

  .timeline-dot {
    width: 14px;
    height: 14px;
  }

  .timeline-connector {
    width: 192px;
  }
}

/* Touch-friendly improvements */
@media (pointer: coarse) {
  .horizontal-timeline-wrapper {
    scroll-snap-type: x proximity;
  }

  .horizontal-timeline-item {
    scroll-snap-align: center;
  }

  .timeline-card {
    cursor: default;
  }

  .timeline-card:hover {
    transform: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .timeline-card:active {
    transform: scale(0.98);
    transition: transform 0.1s ease;
  }
}

.timeline-description {
  font-size: 0.9rem;
  color: #555;
  margin-bottom: 0.25rem;
}

.timeline-user {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

.timeline-user-btn {
  background: none;
  border: none;
  color: #007bff;
  font-size: 0.8rem;
  font-style: italic;
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
  margin-left: 0.25rem;
  transition: all 0.2s ease;
}

.timeline-user-btn:hover {
  color: #0056b3;
  text-decoration: none;
  font-weight: bold;
}

.timeline-time-change {
  font-size: 0.9rem;
  font-weight: bold;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-top: 0.25rem;
}

.timeline-time-change:contains('+') {
  background-color: #d4edda;
  color: #155724;
}

.timeline-times {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  background-color: #f8f9fa;
  padding: 0.5rem;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.previous-time {
  color: #6c757d;
  text-decoration: line-through;
}

.new-time {
  color: #007bff;
  font-weight: bold;
  margin-top: 0.25rem;
}

/* Timeline dot styles for different event types */
.timeline-dot.created {
  background-color: #6c757d;
}

.timeline-dot.time-increase {
  background-color: #28a745;
  animation: pulse-success 2s infinite;
}

.timeline-dot.time-decrease {
  background-color: #dc3545;
  animation: pulse-danger 2s infinite;
}

.timeline-dot.overtime {
  background-color: #fd7e14;
  animation: pulse-warning 2s infinite;
}

.timeline-dot.vote {
  background-color: #ffc107;
}

.timeline-dot.completed {
  background-color: #28a745;
}

.timeline-dot.failed {
  background-color: #dc3545;
}

.timeline-dot.default {
  background-color: #6c757d;
}

.timeline-time-hidden,
.timeline-time-change-hidden,
.timeline-times-hidden {
  margin: 0.25rem 0;
}

.timeline-time-hidden .hidden-time-placeholder,
.timeline-time-change-hidden .hidden-time-placeholder,
.timeline-times-hidden .hidden-time-placeholder {
  font-size: 0.7rem;
  padding: 0.25rem 0.5rem;
  margin: 0;
}

@keyframes pulse-success {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

@keyframes pulse-warning {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

/* Enhanced mobile sticky actions with scroll effects */
@media (max-width: 768px) {
  /* Add smooth transitions for sticky positioning */
  .quick-actions-bar {
    transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
    will-change: transform, box-shadow;
  }

  /* Enhanced shadow when scrolling */
  .quick-actions-bar.scrolled {
    box-shadow: 6px 6px 0 #000, 0 8px 32px rgba(0, 0, 0, 0.3);
    transform: translateZ(0);
  }

  /* Optimize button interactions on mobile */
  .quick-action-btn {
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .quick-action-btn:active {
    transform: scale(0.98);
    box-shadow: 2px 2px 0 #000;
  }

  /* Ensure content doesn't hide behind sticky bar */
  .task-detail-content {
    scroll-margin-top: 120px;
  }

  /* Add visual indicator for sticky state */
  .quick-actions-bar::after {
    content: '';
    position: absolute;
    bottom: -3px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 3px;
    background: linear-gradient(90deg, #007bff, #28a745);
    border-radius: 2px;
    opacity: 0.7;
  }
}

/* 时间隐藏占位符样式 */
.progress-hidden-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px dashed #6c757d;
  border-radius: 8px;
  margin-bottom: 1rem;
}

/* 进度冻结占位符样式 */
.progress-frozen-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border: 2px dashed #17a2b8;
  border-radius: 8px;
  margin-bottom: 1rem;
  animation: pulse-frozen 2s infinite;
}

.hidden-time-placeholder {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #343a40, #495057);
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
  animation: gentle-pulse 2s ease-in-out infinite;
}

/* Frozen time placeholder style */
.frozen-time-placeholder {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #17a2b8, #20c3aa);
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
  animation: pulse-frozen 2s ease-in-out infinite;
}

@keyframes pulse-frozen {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.98);
  }
}

@keyframes gentle-pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.02);
  }
}

/* 钥匙持有者操作部分样式 */
.key-holder-section {
  background: white;
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  padding: 2rem;
  margin-top: 2rem;
}

.key-holder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 3px solid #000;
}

.key-holder-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
}

.key-holder-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.coins-display {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: #000;
  padding: 0.5rem 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  font-weight: 900;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 3px 3px 0 #000;
}

.key-actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.key-action-card {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 3px solid #000;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.key-action-card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.action-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #000;
}

.action-cost {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
}

.action-description {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: #495057;
  line-height: 1.4;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.key-action-btn {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border: 3px solid #000;
  border-radius: 6px;
  padding: 0.75rem 1.5rem;
  font-weight: 800;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-width: 120px;
}

.key-action-btn:hover:not(.disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.key-action-btn.disabled {
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: #adb5bd;
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: 2px 2px 0 #000;
}

.key-action-btn.increase {
  background: linear-gradient(135deg, #28a745, #218838);
}

.key-action-btn.increase:hover:not(.disabled) {
  background: linear-gradient(135deg, #218838, #1e7e34);
}

.key-action-btn.decrease {
  background: linear-gradient(135deg, #dc3545, #c82333);
}

.key-action-btn.decrease:hover:not(.disabled) {
  background: linear-gradient(135deg, #c82333, #bd2130);
}

.key-action-btn.time-toggle {
  background: linear-gradient(135deg, #fd7e14, #e76500);
  min-width: 160px;
}

.key-action-btn.time-toggle:hover:not(.disabled) {
  background: linear-gradient(135deg, #e76500, #dc5f00);
}

.key-action-btn.time-toggle.hidden-mode {
  background: linear-gradient(135deg, #17a2b8, #138496);
  animation: pulse-hidden-mode 2s ease-in-out infinite;
}

.key-action-btn.pin {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  min-width: 140px;
}

.key-action-btn.pin:hover:not(.disabled) {
  background: linear-gradient(135deg, #ee5a52, #e74c3c);
}

.key-action-btn.return {
  background: linear-gradient(135deg, #6f42c1, #5a2d91);
}

.key-action-btn.return:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a2d91, #4c2a85);
}

.key-action-btn.freeze {
  background: linear-gradient(135deg, #17a2b8, #20c3aa);
  min-width: 140px;
}

.key-action-btn.freeze:hover:not(.disabled) {
  background: linear-gradient(135deg, #138496, #1aa085);
}

.key-action-btn.unfreeze {
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  min-width: 140px;
}

.key-action-btn.unfreeze:hover:not(.disabled) {
  background: linear-gradient(135deg, #ee5a24, #e74c3c);
}

@keyframes pulse-hidden-mode {
  0%, 100% {
    opacity: 1;
    box-shadow: 3px 3px 0 #000;
  }
  50% {
    opacity: 0.8;
    box-shadow: 5px 5px 0 #000;
    transform: translate(-1px, -1px);
  }
}

/* Mobile responsive for key holder section */
@media (max-width: 768px) {
  .key-holder-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .key-actions-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    justify-content: center;
  }

  .key-action-btn {
    flex: 1;
    min-width: auto;
  }
}

/* Board Task Completion Proof Section Styles */
.completion-proof-section {
  background: white;
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  padding: 2rem;
  margin-top: 2rem;
}

.proof-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 3px solid #000;
}

.proof-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
}

.proof-meta {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.proof-status {
  padding: 0.5rem 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  font-weight: 900;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 3px 3px 0 #000;
}

/* Proof status specific styles */
.proof-status-pending {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: #000;
}

.proof-status-approved {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
}

.proof-status-rejected {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
}

.proof-status-unknown {
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: white;
}

.submitter {
  background: linear-gradient(135deg, #17a2b8, #138496);
  color: white;
  padding: 0.5rem 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.9rem;
  box-shadow: 3px 3px 0 #000;
}

.proof-content {
  margin-bottom: 2rem;
}

.proof-label {
  font-weight: 700;
  font-size: 1.1rem;
  color: #333;
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.proof-text {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 3px solid #000;
  border-radius: 8px;
  padding: 1.5rem;
  font-size: 1rem;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
  box-shadow: 4px 4px 0 #000;
  min-height: 100px;
}

.proof-review-actions {
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 3px solid #ffc107;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.review-notice {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border: 2px solid #fd7e14;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
}

.notice-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.notice-text {
  font-weight: 600;
  color: #856404;
  font-size: 0.95rem;
}

.review-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.review-btn {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
  border: 3px solid #000;
  border-radius: 8px;
  padding: 1rem 2rem;
  font-weight: 900;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  min-width: 140px;
}

.review-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.review-btn.approve-btn {
  background: linear-gradient(135deg, #28a745, #218838);
}

.review-btn.approve-btn:hover {
  background: linear-gradient(135deg, #218838, #1e7e34);
}

.review-btn.reject-btn {
  background: linear-gradient(135deg, #dc3545, #c82333);
}

.review-btn.reject-btn:hover {
  background: linear-gradient(135deg, #c82333, #bd2130);
}

.proof-status-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #e2e3e5, #ced4da);
  border: 3px solid #6c757d;
  border-radius: 8px;
  box-shadow: 4px 4px 0 #000;
}

.status-icon {
  font-size: 1.5rem;
  color: #495057;
}

.status-text {
  font-weight: 600;
  color: #495057;
  font-size: 1rem;
  text-align: center;
}

/* Media Files Section Styles */
.media-files-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 6px 6px 0 #000;
}

.media-files-header {
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #000;
}

.media-files-header h4 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.media-files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
}

.media-file-item {
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  position: relative;
}

.media-file-item:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.media-file-item.primary-file {
  border-color: #ffc107;
  box-shadow: 4px 4px 0 #ffc107;
}

.media-file-item.primary-file:hover {
  box-shadow: 6px 6px 0 #ffc107;
}

/* Image Files */
.media-file-image {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
}

.media-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
  transition: all 0.2s ease;
}

.media-image:hover {
  transform: scale(1.05);
}

.file-info-static {
  position: static;
  background: white;
  padding: 0.75rem;
  border-top: 2px solid #000;
}

.file-info {
  color: white;
}

.file-name {
  display: block;
  font-weight: 700;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
  word-break: break-word;
}

.file-size {
  display: block;
  font-size: 0.75rem;
  opacity: 0.8;
  margin-bottom: 0.25rem;
}

.primary-badge {
  display: inline-block;
  background: #ffc107;
  color: #000;
  padding: 0.125rem 0.5rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-size: 0.625rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
}

/* Video Files */
.media-file-video {
  background: #000;
}

.media-video {
  width: 100%;
  height: auto;
  max-height: 300px;
}

.media-file-video .file-info {
  padding: 1rem;
  background: white;
  color: #000;
}

.media-file-video .file-name {
  color: #000;
}

.media-file-video .file-size {
  color: #666;
}

.media-file-video .primary-badge {
  margin-top: 0.5rem;
}

/* Document Files */
.media-file-document {
  padding: 2rem;
  text-align: center;
  background: white;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.document-icon {
  font-size: 3rem;
  color: #6c757d;
}

.media-file-document .file-info {
  text-align: center;
}

.media-file-document .file-name {
  color: #000;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.file-type {
  display: block;
  font-size: 0.75rem;
  color: #666;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.media-file-document .file-size {
  color: #666;
  margin-bottom: 0.5rem;
}

.download-btn {
  background: #17a2b8;
  color: white;
  border: 3px solid #000;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-weight: 700;
  font-size: 0.875rem;
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  display: inline-block;
}

.download-btn:hover {
  background: #138496;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
  text-decoration: none;
  color: white;
}

/* File Description */
.file-description {
  padding: 0.75rem;
  background: #f8f9fa;
  border-top: 2px solid #000;
  font-size: 0.875rem;
  color: #495057;
  line-height: 1.4;
}

/* Image Modal Styles */
.image-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.2s ease-out;
}

.image-modal-content {
  background: white;
  border: 4px solid #000;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 12px 12px 0 #000;
  animation: slideInModal 0.3s ease-out;
}

.image-modal-header {
  background: #17a2b8;
  color: white;
  padding: 0.75rem 1rem;
  border-bottom: 4px solid #000;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.image-modal-close {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  font-size: 1.5rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.image-modal-close:hover {
  background: #c82333;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.image-modal-body {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: #000;
}

.image-modal-img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
}

/* Modal Animations */
@keyframes slideInModal {
  from {
    opacity: 0;
    transform: scale(0.8) translateY(-50px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Mobile responsive for completion proof section */
@media (max-width: 768px) {
  .completion-proof-section {
    padding: 1.5rem;
    margin-top: 1.5rem;
    border-width: 3px;
    box-shadow: 6px 6px 0 #000;
  }

  .proof-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    align-items: stretch;
  }

  .proof-meta {
    flex-direction: column;
    gap: 0.75rem;
  }

  .proof-text {
    padding: 1rem;
    font-size: 0.9rem;
  }

  .review-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }

  .review-btn {
    width: 100%;
    min-width: auto;
    padding: 0.875rem 1.5rem;
    font-size: 0.9rem;
  }

  .review-notice {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .notice-text {
    font-size: 0.875rem;
  }

  /* Mobile responsive for media files */
  .media-files-section {
    padding: 1rem;
    margin-top: 1.5rem;
  }

  .media-files-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .media-file-item {
    border-width: 2px;
    box-shadow: 3px 3px 0 #000;
  }

  .media-file-item:hover {
    transform: none;
    box-shadow: 3px 3px 0 #000;
  }

  .media-file-item.primary-file {
    box-shadow: 3px 3px 0 #ffc107;
  }

  .media-file-item.primary-file:hover {
    box-shadow: 3px 3px 0 #ffc107;
  }

  .file-info-static {
    position: static;
    transform: none;
    background: white;
    padding: 0.75rem;
    border-top: 2px solid #000;
  }

  .image-modal-content {
    width: 95%;
    max-width: none;
    border-width: 3px;
    box-shadow: 8px 8px 0 #000;
  }

  .image-modal-header {
    padding: 0.5rem;
    justify-content: flex-end;
  }

  .image-modal-close {
    width: 35px;
    height: 35px;
    font-size: 1.25rem;
  }

  .image-modal-body {
    padding: 1rem;
  }

  .image-modal-img {
    max-height: 70vh;
  }
}

/* Multi-person Task Participants Styles */
.participants-section {
  background: white;
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  padding: 2rem;
  margin-top: 2rem;
}

.multi-task-status-notice {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin: 0.5rem 0;
  background: #e3f2fd;
  border: 2px solid #2196f3;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #1565c0;
  font-weight: 600;
}

.notice-icon {
  font-size: 1rem;
}

.notice-text {
  font-weight: 500;
}

.participants-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 3px solid #000;
}

.participants-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
}

.participants-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.stat-item {
  background: linear-gradient(135deg, #17a2b8, #138496);
  color: white;
  padding: 0.5rem 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.9rem;
  box-shadow: 3px 3px 0 #000;
}

.stat-label {
  margin-right: 0.25rem;
}

.stat-value {
  font-weight: 900;
}

/* Review Mode Toggle (removed) */

/* Participants Grid View */
.participants-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.participant-card {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 3px solid #000;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.participant-card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.participant-card-joined {
  border-color: #17a2b8;
  box-shadow: 4px 4px 0 #17a2b8;
}

.participant-card-submitted {
  border-color: #ffc107;
  box-shadow: 4px 4px 0 #ffc107;
}

.participant-card-approved {
  border-color: #28a745;
  box-shadow: 4px 4px 0 #28a745;
}

.participant-card-rejected {
  border-color: #dc3545;
  box-shadow: 4px 4px 0 #dc3545;
}

.participant-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.participant-info {
  flex: 1;
}

.participant-name {
  background: none;
  border: none;
  color: #007bff;
  font-weight: bold;
  font-size: 1rem;
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
  margin: 0 0 0.25rem 0;
  transition: all 0.2s ease;
}

.participant-name:hover {
  color: #0056b3;
  text-decoration: none;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
}

.participant-join-time {
  font-size: 0.8rem;
  color: #666;
}

.participant-status-badge {
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
}

.participant-status-badge.joined {
  background: #17a2b8;
  color: white;
}

.participant-status-badge.submitted {
  background: #ffc107;
  color: #000;
}

.participant-status-badge.approved {
  background: #28a745;
  color: white;
}

.participant-status-badge.rejected {
  background: #dc3545;
  color: white;
}

.participant-submission {
  margin: 1rem 0;
  padding: 1rem;
  background: white;
  border: 2px solid #000;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
}

.submission-label {
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #333;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.submission-text {
  font-size: 0.9rem;
  line-height: 1.4;
  color: #555;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.participant-files {
  margin: 1rem 0;
}

.files-label {
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: #333;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.file-item {
  display: flex;
  flex-direction: column;
  background: white;
  border: 2px solid #000;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  cursor: pointer;
  overflow: hidden;
}

.file-item:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.file-item.primary-file {
  border-color: #ffc107;
  box-shadow: 2px 2px 0 #ffc107;
}

.file-item.primary-file:hover {
  box-shadow: 3px 3px 0 #ffc107;
}

.file-preview {
  position: relative;
  width: 100%;
  height: 120px;
  overflow: hidden;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s ease;
}

.file-item:hover .preview-image {
  transform: scale(1.05);
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.file-item:hover .image-overlay {
  opacity: 1;
}

.view-icon {
  color: white;
  font-size: 1.5rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 120px;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
}

.file-type-icon {
  font-size: 2.5rem;
  opacity: 0.6;
}

.file-info {
  padding: 0.75rem;
  border-top: 1px solid #e9ecef;
}

.file-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: #333;
  margin-right: 1rem;
  flex: 1;
  word-break: break-word;
}

.file-size {
  font-size: 0.75rem;
  color: #666;
  margin-right: 0.5rem;
}

.file-click-hint {
  font-size: 1rem;
  opacity: 0.7;
}

.participant-review {
  margin: 1rem 0;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
}

.review-label {
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #856404;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.review-comment {
  font-size: 0.9rem;
  line-height: 1.4;
  color: #856404;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.participant-reward {
  margin: 1rem 0;
  padding: 1rem;
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border: 2px solid #28a745;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
}

.reward-label {
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #155724;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.reward-amount {
  font-size: 1.1rem;
  font-weight: 900;
  color: #155724;
}

.participant-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.action-btn {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
  border: 3px solid #000;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-weight: 700;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  flex: 1;
}

.action-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.action-btn.approve-btn {
  background: linear-gradient(135deg, #28a745, #218838);
}

.action-btn.approve-btn:hover {
  background: linear-gradient(135deg, #218838, #1e7e34);
}

.action-btn.reject-btn {
  background: linear-gradient(135deg, #dc3545, #c82333);
}

.action-btn.reject-btn:hover {
  background: linear-gradient(135deg, #c82333, #bd2130);
}

.action-btn.large {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  min-width: 140px;
}

/* Review Navigation Container (removed) */

/* Review Mode Completion Proof Section (removed) */

.media-file-card {
  background: white;
  border: 2px solid #000;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.media-file-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.media-file-card.primary-file {
  border-color: #ffc107;
  box-shadow: 3px 3px 0 #ffc107;
}

.media-file-card.primary-file:hover {
  box-shadow: 4px 4px 0 #ffc107;
}

.media-preview {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
}

.image-preview {
  background: #000;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preview-image.clickable-image:hover {
  transform: scale(1.05);
}

.file-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
}

.file-icon {
  font-size: 3rem;
  color: #6c757d;
}

.media-info {
  padding: 1rem;
}

.media-name {
  font-weight: 700;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
  color: #333;
  word-break: break-word;
}

.media-size {
  font-size: 0.75rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.media-description {
  font-size: 0.8rem;
  color: #555;
  line-height: 1.4;
  margin-top: 0.5rem;
}

.primary-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: #ffc107;
  color: #000;
  padding: 0.125rem 0.5rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-size: 0.625rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
}

/* Review Actions (removed) */

/* Available Spots and Task Full Messages */
.available-spots, .task-full {
  text-align: center;
  padding: 1.5rem;
  margin-top: 1.5rem;
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 4px 4px 0 #000;
}

.available-spots {
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border-color: #28a745;
}

.spots-message {
  font-size: 1.1rem;
  font-weight: 700;
  color: #155724;
}

.task-full {
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border-color: #dc3545;
}

.full-message {
  font-size: 1.1rem;
  font-weight: 700;
  color: #721c24;
}

/* No reviewable participants message (removed) */

/* Mobile responsive for participants section */
@media (max-width: 768px) {
  .participants-section {
    padding: 1.5rem;
    margin-top: 1.5rem;
    border-width: 3px;
    box-shadow: 6px 6px 0 #000;
  }

  .participants-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    align-items: stretch;
  }

  .participants-stats {
    flex-direction: column;
    gap: 0.75rem;
  }

  .participants-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .participant-card {
    padding: 1rem;
    border-width: 2px;
    box-shadow: 3px 3px 0 #000;
  }

  .participant-card:hover {
    transform: none;
    box-shadow: 3px 3px 0 #000;
  }

  .participant-header {
    flex-direction: column;
    gap: 0.75rem;
    text-align: center;
    align-items: stretch;
  }

  .participant-actions {
    flex-direction: column;
    gap: 0.5rem;
  }

  .navigation-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }


  .media-file-card {
    border-width: 2px;
    box-shadow: 2px 2px 0 #000;
  }

  .media-file-card:hover {
    transform: none;
    box-shadow: 2px 2px 0 #000;
  }

  .media-file-card.primary-file {
    box-shadow: 2px 2px 0 #ffc107;
  }

  .media-file-card.primary-file:hover {
    box-shadow: 2px 2px 0 #ffc107;
  }

  /* Mobile responsive for participant files */
  .files-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
  }

  .file-preview {
    height: 100px;
  }

  .file-info {
    padding: 0.5rem;
  }

  .file-name {
    font-size: 0.8rem;
  }

  .file-size {
    font-size: 0.7rem;
  }
}

</style>