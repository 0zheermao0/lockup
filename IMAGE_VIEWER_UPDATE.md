# 图片查看器更新文档

## 更新概述

将任务详情页的图片查看功能从"新窗口打开"改为"模态框查看"，参考首页动态的大图查看样式，设计了精美的动画效果。

## 主要改动

### 1. 组件结构更新 (TaskDetailView.vue)

#### 模板部分
- 使用 `<Teleport to="body">` 将模态框渲染到 body 层级
- 使用 `<Transition name="image-modal">` 实现优雅的过渡动画
- 添加背景遮罩层 (`backdrop-filter: blur(20px)`)
- 添加加载状态显示
- 添加底部提示栏

#### 状态管理
```typescript
const showImageModal = ref(false)        // 控制模态框显示
const imageModalLoaded = ref(false)      // 图片加载状态
const selectedImage = ref<any>(null)     // 选中的图片
```

#### 方法更新
- `openImageModal(file)` - 打开提交文件图片
- `viewPhoto(url)` - 打开验证照片
- `closeImageModal()` - 关闭模态框
- `onImageModalLoad()` - 图片加载完成回调

### 2. 动画效果

#### 进入动画 (Enter)
- 背景遮罩：淡入 (opacity 0 → 1)
- 容器：缩放 + 上移 (scale 0.8 → 1, translateY 50px → 0)
- 图片：缩放 + 模糊消除 (scale 0.9 → 1, blur 10px → 0)
- 关闭按钮：旋转进入 (scale 0 → 1, rotate -180deg → 0)
- 底部提示：淡入上移 (translateY 20px → 0)

#### 离开动画 (Leave)
- 所有元素：反向动画，时长 0.3s

#### 缓动函数
- 进入：`cubic-bezier(0.34, 1.56, 0.64, 1)` (弹簧效果)
- 离开：`cubic-bezier(0.4, 0, 0.2, 1)` (平滑减速)

### 3. UI 设计

#### 关闭按钮
- 位置：右上角固定定位
- 样式：圆形白色背景，黑色边框，阴影
- 悬停：放大 + 旋转90度 + 变红
- 点击：缩小反馈

#### 图片展示
- 最大尺寸：90vw × 85vh
- 边框：4px 白色
- 圆角：12px (移动端 0px)
- 阴影：多层阴影营造立体感
- 加载前：模糊 + 缩小
- 加载后：清晰 + 正常大小

#### 背景遮罩
- 颜色：rgba(0, 0, 0, 0.85)
- 模糊：backdrop-filter blur(20px)

#### 底部提示栏
- 位置：图片下方
- 样式：半透明背景 + 毛玻璃效果
- 圆角：100px (胶囊形状)
- 文字："点击图片任意位置关闭"

#### Loading 状态
- 旋转的圆形 spinner
- 白色半透明
- "加载中..." 文字提示

### 4. 交互设计

- 点击背景关闭模态框
- 点击关闭按钮关闭模态框
- 图片加载完成前显示 Loading
- 图片加载完成后淡入显示

### 5. 移动端适配

#### 平板 (max-width: 768px)
- 关闭按钮缩小
- 图片边框减薄
- 底部提示栏调整内边距

#### 手机 (max-width: 480px)
- 关闭按钮进一步缩小
- 图片全屏显示（无边框、无圆角）
- 最大化显示区域

### 6. 使用方式

#### 查看提交文件图片
```typescript
openImageModal(file)  // file 包含 file_url
```

#### 查看验证照片
```typescript
viewPhoto(url)  // 直接传入图片 URL
```

## 动画演示

### 打开过程
1. 背景立即变暗并模糊
2. 图片区域从下方弹入并放大
3. 关闭按钮旋转进入
4. 底部提示栏淡入上移
5. 图片加载完成后从模糊变清晰

### 关闭过程
1. 所有元素同时反向动画
2. 背景淡出
3. 容器缩小上移消失
4. 关闭按钮旋转消失

## 性能优化

- 使用 `transform` 和 `opacity` 实现动画（GPU 加速）
- 使用 `Teleport` 避免层级问题
- 图片加载状态管理，避免闪烁
- 移动端减少动画复杂度

## 浏览器兼容性

- 支持 backdrop-filter 的现代浏览器
- 不支持 backdrop-filter 的浏览器回退到纯色背景
- 所有动画使用 CSS transition，性能优秀
