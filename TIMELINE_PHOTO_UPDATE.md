# 任务时间线验证照片显示更新

## 更新内容

### 1. 后端更新

#### 新增时间线事件类型 (tasks/models.py)
- `temporary_unlock_requested` - 临时开锁请求
- `temporary_unlock_approved` - 临时开锁批准
- `temporary_unlock_rejected` - 临时开锁拒绝
- `temporary_unlock_started` - 临时开锁开始
- `temporary_unlock_ended` - 临时开锁结束
- `temporary_unlock_cancelled` - 临时开锁取消
- `temporary_unlock_timeout` - 临时开锁超时

#### 序列化器更新 (tasks/serializers.py)
- `TaskTimelineEventSerializer` 新增 `verification_photo_url` 字段
- 动态获取临时开锁记录的验证照片URL

#### 视图更新 (tasks/views.py)
所有临时开锁相关视图现在都创建时间线事件：
- 请求临时开锁 → 创建 `task_frozen` 和 `temporary_unlock_requested/started` 事件
- 批准请求 → 创建 `temporary_unlock_approved` 和 `temporary_unlock_started` 事件
- 拒绝请求 → 创建 `temporary_unlock_rejected` 和 `task_unfrozen` 事件
- 结束开锁 → 创建 `temporary_unlock_ended` 和 `task_unfrozen` 事件
- 取消请求 → 创建 `temporary_unlock_cancelled` 和 `task_unfrozen` 事件

#### 定时任务更新 (tasks/cron.py)
- 超时检测创建 `temporary_unlock_timeout`、`task_unfrozen` 和 `user_pinned` 事件

### 2. 前端更新

#### 新增辅助方法 (TaskDetailView.vue)
- `isTemporaryUnlockEvent()` - 判断事件类型是否为临时开锁事件
- `getVerificationPhotoUrl()` - 获取验证照片URL（支持缓存）
- `onTimelinePhotoLoad()` - 照片加载完成回调

#### 计算属性
- `canViewVerificationPhoto` - 判断当前用户是否有权限查看验证照片（任务本人或钥匙持有者）

#### 时间线模板更新
桌面端和移动端时间线都添加了验证照片显示：
- 有权限用户：显示照片，悬停显示"查看"按钮，点击可查看原图
- 无权限用户：显示打码效果（24px高斯模糊 + 噪点纹理），点击显示权限提示

#### 样式设计

##### 时间线圆点颜色
- `unlock-pending` (黄色) - 等待批准
- `unlock-success` (绿色) - 已批准
- `unlock-rejected` (红色) - 已拒绝
- `unlock-active` (青色 + 脉冲动画) - 进行中
- `unlock-ended` (灰色) - 已结束
- `unlock-cancelled` (灰色) - 已取消
- `unlock-timeout` (红色) - 超时

##### 验证照片样式
- 桌面端：最大宽度120px，悬停显示查看按钮
- 移动端：最大宽度100px，简化提示

##### 打码效果
参考首页动态图片打码风格：
- 24px 高斯模糊
- 噪点纹理覆盖
- 白色背景提示框，黑色边框，阴影效果
- 锁图标 + 提示文字

##### 动画效果
- `slide-in-photo` - 照片区域滑入动画
- `pulse-unlock` - 进行中状态脉冲动画
- `highlight-unlock` - 高亮动画

### 3. 权限控制
- 任务本人（task.user）可以查看验证照片
- 钥匙持有者（task.key.holder）可以查看验证照片
- 其他用户看到打码效果，点击显示"无权查看"提示

## 测试建议

1. 创建带照片验证的临时开锁任务
2. 执行临时开锁流程（请求→批准→结束）
3. 检查时间线是否正确显示所有事件
4. 验证照片是否在时间线中显示（有权限用户）
5. 用其他账号查看，验证打码效果
6. 测试移动端显示效果
