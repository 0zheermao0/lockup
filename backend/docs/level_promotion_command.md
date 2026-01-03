# 等级晋升管理命令使用指南

## 概述

`process_level_promotions` 是一个Django管理命令，用于手动触发用户等级晋升。这个命令提供了比自动晋升系统更灵活的控制选项。

## 基本用法

```bash
# 激活虚拟环境
source venv/bin/activate

# 基本命令
python manage.py process_level_promotions
```

## 命令参数

### `--dry-run` (预览模式)
只检查哪些用户符合晋升条件，但不实际执行晋升。

```bash
# 预览所有符合条件的用户
python manage.py process_level_promotions --dry-run

# 预览并显示详细信息
python manage.py process_level_promotions --dry-run --verbose
```

### `--user-id` (指定用户)
只处理特定用户的等级晋升。

```bash
# 处理用户ID为123的用户
python manage.py process_level_promotions --user-id 123

# 预览用户ID为123的晋升情况
python manage.py process_level_promotions --user-id 123 --dry-run --verbose
```

### `--level` (指定等级)
只处理当前为特定等级的用户。

```bash
# 只处理当前1级的用户
python manage.py process_level_promotions --level 1

# 只处理当前2级的用户
python manage.py process_level_promotions --level 2 --dry-run
```

### `--batch-size` (批处理大小)
设置批处理大小，默认为1000。

```bash
# 设置批处理大小为500
python manage.py process_level_promotions --batch-size 500
```

### `--verbose` (详细输出)
显示详细的处理信息，包括不符合条件的用户和具体要求。

```bash
# 显示详细信息
python manage.py process_level_promotions --verbose

# 查看特定用户的详细晋升要求
python manage.py process_level_promotions --user-id 123 --dry-run --verbose
```

### `--force` (强制模式)
强制处理模式，忽略一些限制（预留参数，当前版本暂未使用）。

```bash
python manage.py process_level_promotions --force
```

## 使用场景

### 1. 日常维护检查
```bash
# 每日检查符合晋升条件的用户数量
python manage.py process_level_promotions --dry-run
```

### 2. 紧急晋升处理
```bash
# 立即处理所有符合条件的用户
python manage.py process_level_promotions --verbose
```

### 3. 特定用户晋升
```bash
# 检查特定用户是否符合晋升条件
python manage.py process_level_promotions --user-id 123 --dry-run --verbose

# 为特定用户执行晋升
python manage.py process_level_promotions --user-id 123
```

### 4. 分级处理
```bash
# 先处理1级用户
python manage.py process_level_promotions --level 1 --verbose

# 再处理2级用户
python manage.py process_level_promotions --level 2 --verbose

# 最后处理3级用户
python manage.py process_level_promotions --level 3 --verbose
```

### 5. 大量用户处理
```bash
# 使用较小的批处理大小避免数据库压力
python manage.py process_level_promotions --batch-size 100 --verbose
```

## 输出说明

### 成功输出示例
```
🎯 开始处理用户等级晋升...
📊 找到 150 个待检查用户
📦 处理批次 1/1 (150 个用户)
   ✅ alice 成功从 1 级晋升到 2 级
   ✅ bob 成功从 2 级晋升到 3 级
   ⚠️  charlie (等级1) - 暂不符合晋升条件

============================================================
📊 执行结果摘要
============================================================
⏱️  执行时间: 2.35 秒
👥 处理用户数: 150
🎉 成功晋升: 2
⚠️  跳过用户: 148
❌ 错误数量: 0
🎊 等级晋升处理完成！用户将收到晋升通知。
```

### 预览模式输出示例
```
🎯 开始处理用户等级晋升...
📊 找到 50 个待检查用户
🔍 预览模式 - 不会实际执行晋升
📦 处理批次 1/1 (50 个用户)
   ✨ [预览] alice 可以从 1 级晋升到 2 级
   ✨ [预览] bob 可以从 2 级晋升到 3 级

============================================================
📊 执行结果摘要
============================================================
🔍 预览模式 - 未实际执行晋升
👀 预览完成！发现 2 个用户符合晋升条件。
   使用不带 --dry-run 参数的命令来实际执行晋升。
```

### 详细信息输出示例
```bash
# 使用 --verbose 参数时的输出
python manage.py process_level_promotions --user-id 123 --dry-run --verbose
```

```
🔍 检查用户: alice (ID: 123, 当前等级: 1)
   ⚠️  用户 alice 暂不符合晋升条件
   📋 升级到2级的要求:
      ✅ 活跃度积分: 150/100
      ✅ 发布动态总数: 8/5
      ❌ 收到点赞总数: 5/10
      ✅ 带锁时长: 30.5小时/24小时
```

## 等级晋升条件

| 等级 | 活跃度积分 | 发布动态 | 收到点赞 | 带锁时长 | 任务完成率 |
|------|-----------|----------|----------|----------|------------|
| 1→2级 | ≥100 | ≥5 | ≥10 | ≥24小时 | - |
| 2→3级 | ≥300 | ≥20 | ≥50 | ≥7天 | ≥80% |
| 3→4级 | ≥1000 | ≥50 | ≥1000 | ≥30天 | ≥90% |

## 等级降级条件

**重要更新**：系统现在支持等级降级功能。如果用户不再满足其当前等级的要求，将被降级到合适的等级。

降级条件（不满足当前等级要求时触发）：
- **4级→3级**：不满足4级要求（活跃度<1000 或 动态<50 或 点赞<1000 或 带锁时长<30天 或 完成率<90%）
- **3级→2级**：不满足3级要求（活跃度<300 或 动态<20 或 点赞<50 或 带锁时长<7天 或 完成率<80%）
- **2级→1级**：不满足2级要求（活跃度<100 或 动态<5 或 点赞<10 或 带锁时长<24小时）

## 注意事项

1. **权限要求**：需要Django管理员权限或服务器访问权限
2. **数据库锁定**：命令使用数据库事务锁定防止并发修改
3. **通知系统**：晋升和降级成功后会自动发送相应通知给用户
4. **日志记录**：所有等级变更操作都会记录在 `UserLevelUpgrade` 表中
5. **安全性**：建议先使用 `--dry-run` 参数预览结果
6. **性能**：大量用户处理时建议使用较小的 `--batch-size`
7. **降级通知**：降级用户会收到友好的鼓励性通知，说明降级原因并鼓励重新努力

## 与自动等级处理系统的关系

- **自动处理**：每周三凌晨4:30自动执行晋升和降级检查
- **手动处理**：使用此命令可以随时执行等级变更
- **记录区分**：手动操作的记录标记为 `reason='manual_command'`，自动操作标记为 `reason='automatic'`，降级操作标记为 `reason='downgrade'`
- **全面检查**：现在所有等级的用户都会被检查，包括可能的降级

## 故障排除

### 常见错误

1. **用户不存在**
   ```
   CommandError: 用户ID 999 不存在
   ```
   解决方法：检查用户ID是否正确

2. **数据库连接错误**
   ```
   django.db.utils.OperationalError: ...
   ```
   解决方法：检查数据库连接配置

3. **权限错误**
   ```
   PermissionError: ...
   ```
   解决方法：确保有足够的文件系统权限

### 调试模式

使用 `--verbose` 参数可以获得更多调试信息：

```bash
python manage.py process_level_promotions --verbose --dry-run
```

如果遇到错误，可以查看详细的错误堆栈：

```bash
python manage.py process_level_promotions --user-id 123 --verbose
```