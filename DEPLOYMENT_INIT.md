# 部署初始化指南

## 问题描述

线上部署时创建带锁任务报错："系统错误：钥匙道具类型不存在"

**根本原因**: 数据库缺少系统运行必需的基础数据（ItemType 和 StoreItem）

## 解决方案

### 1. 运行数据初始化命令

在线上服务器的Django项目目录中执行：

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行数据初始化命令
python manage.py init_store_data
```

### 2. 命令说明

`init_store_data` 命令会自动创建以下基础数据：

#### ItemType（道具类型）
- 📸 **相纸** (photo_paper) - 用于拍摄照片
- 🖼️ **照片** (photo) - 记录特殊时刻
- 🍾 **漂流瓶** (drift_bottle) - 传递消息和物品
- 🗝️ **钥匙** (key) - 解锁带锁任务的特殊钥匙
- 📝 **纸条** (note) - 记录文字信息

#### StoreItem（商店商品）
- 📝 **留言纸条** - 3积分
- 📸 **相纸** - 5积分
- 🍾 **漂流瓶** - 15积分
- 🗝️ **通用钥匙** - 50积分（等级要求2）

### 3. 验证初始化

运行以下命令验证数据是否正确创建：

```bash
python manage.py shell -c "
from store.models import ItemType, StoreItem
print(f'ItemType 记录数: {ItemType.objects.count()}')
print(f'StoreItem 记录数: {StoreItem.objects.count()}')

# 检查关键的钥匙类型是否存在
key_type = ItemType.objects.filter(name='key').first()
if key_type:
    print(f'✅ 钥匙道具类型存在: {key_type.display_name}')
else:
    print('❌ 钥匙道具类型不存在！')
"
```

### 4. 测试带锁任务创建

确认数据初始化成功后，测试创建带锁任务：

```bash
# 测试API（需要替换有效的token）
curl -X POST http://your-domain.com/api/tasks/ \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试任务",
    "description": "验证初始化数据",
    "task_type": "lock",
    "difficulty": "easy",
    "duration_type": "fixed",
    "duration_value": 30,
    "unlock_type": "time"
  }'
```

成功的响应应该包含任务数据，而不是错误消息。

## 命令特性

### 幂等性
- 命令可以安全地重复运行
- 不会重复创建已存在的数据
- 适合在CI/CD管道中使用

### 强制更新模式
如果需要强制更新所有数据：

```bash
python manage.py init_store_data --force
```

### 输出示例

```
🔧 初始化道具类型...
  ✅ 创建道具类型: 漂流瓶 (drift_bottle)
  ✅ 创建道具类型: 纸条 (note)
  ✓ 道具类型已存在: 相纸 (photo_paper)
  ✓ 道具类型已存在: 照片 (photo)
  ✓ 道具类型已存在: 钥匙 (key)
📊 道具类型初始化完成: 新创建 2 个，更新 0 个

🛒 初始化商店商品...
  ✅ 创建商店商品: 漂流瓶 - 15积分
  ✅ 创建商店商品: 留言纸条 - 3积分
  ✓ 商店商品已存在: 相纸 - 5积分
  ✓ 商店商品已存在: 通用钥匙 - 50积分
📊 商店商品初始化完成: 新创建 2 个，更新 0 个

✅ 所有基础数据初始化完成！
```

## 故障排除

### 如果命令执行失败

1. **检查数据库连接**
   ```bash
   python manage.py dbshell
   ```

2. **检查迁移状态**
   ```bash
   python manage.py showmigrations
   ```

3. **应用未执行的迁移**
   ```bash
   python manage.py migrate
   ```

### 如果带锁任务仍然创建失败

1. **检查ItemType表**
   ```bash
   python manage.py shell -c "
   from store.models import ItemType
   print('所有ItemType:')
   for it in ItemType.objects.all():
       print(f'  {it.name}: {it.display_name}')
   "
   ```

2. **检查错误日志**
   查看Django应用日志获取详细错误信息

3. **重新运行初始化**
   ```bash
   python manage.py init_store_data --force
   ```

## 生产环境注意事项

1. **备份数据库** - 在运行初始化命令前备份现有数据
2. **维护窗口** - 在低流量时段执行初始化
3. **监控日志** - 执行后监控应用日志确认无异常
4. **功能测试** - 在生产环境中测试带锁任务创建功能

---

📝 **创建时间**: 2025年10月13日
🔧 **维护者**: Claude Code Assistant
📋 **状态**: 测试完成，生产就绪