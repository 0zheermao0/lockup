#!/usr/bin/env python3
"""
设置定时任务脚本
用于配置自动处理小时奖励的cron job
"""

import os
import sys
import subprocess
from pathlib import Path

# 获取项目路径
PROJECT_DIR = Path(__file__).resolve().parent.parent
MANAGE_PY = PROJECT_DIR / "manage.py"
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"

def create_cron_entry():
    """创建cron条目"""
    # 每小时执行一次奖励处理
    cron_command = f"0 * * * * {VENV_PYTHON} {MANAGE_PY} process_rewards >> /tmp/lockup_rewards.log 2>&1"

    return cron_command

def setup_cron():
    """设置cron任务"""
    print("设置定时任务...")

    # 检查文件是否存在
    if not MANAGE_PY.exists():
        print(f"错误: 找不到 {MANAGE_PY}")
        return False

    if not VENV_PYTHON.exists():
        print(f"错误: 找不到虚拟环境 Python {VENV_PYTHON}")
        return False

    cron_entry = create_cron_entry()

    print("\n建议的cron条目:")
    print("-" * 60)
    print(cron_entry)
    print("-" * 60)

    print("\n要手动设置cron任务，请执行以下步骤:")
    print("1. 运行命令: crontab -e")
    print("2. 添加上面的条目到文件末尾")
    print("3. 保存并退出")

    print("\n或者运行以下命令自动添加:")
    print(f'echo "{cron_entry}" | crontab -')

    # 询问是否自动添加
    try:
        choice = input("\n是否自动添加到crontab? (y/N): ").lower().strip()
        if choice == 'y':
            # 获取现有的crontab
            try:
                current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL)
                current_crontab = current_crontab.decode('utf-8')
            except subprocess.CalledProcessError:
                current_crontab = ""

            # 检查是否已经存在相同的条目
            if "process_rewards" in current_crontab:
                print("警告: 似乎已经存在相关的cron任务")
                overwrite = input("是否覆盖? (y/N): ").lower().strip()
                if overwrite != 'y':
                    print("取消操作")
                    return True

            # 添加新的cron条目
            new_crontab = current_crontab.strip() + "\n" + cron_entry + "\n"

            # 写入新的crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
            process.communicate(input=new_crontab.encode('utf-8'))

            if process.returncode == 0:
                print("✅ Cron任务添加成功!")
                print("任务将每小时自动运行一次")
            else:
                print("❌ 添加cron任务失败")
                return False
        else:
            print("请手动添加cron任务")
    except KeyboardInterrupt:
        print("\n操作取消")
        return False

    return True

def test_command():
    """测试命令是否正常工作"""
    print("测试奖励处理命令...")

    try:
        result = subprocess.run([
            str(VENV_PYTHON),
            str(MANAGE_PY),
            'process_rewards'
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ 命令执行成功!")
            print("输出:", result.stdout)
        else:
            print("❌ 命令执行失败!")
            print("错误:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("⚠️ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        return False

    return True

def main():
    print("Lockup 奖励系统定时任务设置")
    print("=" * 40)

    # 首先测试命令
    if not test_command():
        print("请先修复命令执行问题")
        sys.exit(1)

    # 设置cron任务
    if setup_cron():
        print("\n🎉 设置完成!")
        print("\n提示:")
        print("- 可以运行 'crontab -l' 查看当前的cron任务")
        print("- 日志文件位置: /tmp/lockup_rewards.log")
        print("- 如需删除任务，运行 'crontab -e' 并删除相关行")
    else:
        print("设置失败")
        sys.exit(1)

if __name__ == "__main__":
    main()