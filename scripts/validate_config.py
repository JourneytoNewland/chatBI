#!/usr/bin/env python3
"""配置验证脚本 - 确保所有敏感信息都通过环境变量配置"""

import os
import sys
from pathlib import Path

def validate_no_hardcoded_secrets():
    """检查代码中是否有硬编码的密钥"""
    import re
    
    # 定义敏感模式
    secret_patterns = [
        (r'api_key\s*=\s*["\'][^"\']{20,}["\']', 'API密钥硬编码'),
        (r'password\s*=\s*["\'][^"\']{8,}["\']', '密码硬编码'),
        (r'secret\s*=\s*["\'][^"\']{20,}["\']', '密钥硬编码'),
        (r'token\s*=\s*["\'][^"\']{20,}["\']', 'Token硬编码'),
    ]
    
    # 检查src目录
    src_path = Path('src')
    issues = []
    
    for py_file in src_path.rglob('*.py'):
        content = py_file.read_text()
        for pattern, desc in secret_patterns:
            # 排除环境变量读取
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line = content[:match.start()].count('\n') + 1
                if 'os.getenv' not in content[max(0, match.start()-100):match.start()]:
                    if 'os.environ' not in content[max(0, match.start()-100):match.start()]:
                        issues.append(f"  ❌ {py_file}:{line} - {desc}")
    
    return issues

def validate_gitignore():
    """验证.gitignore是否包含必要规则"""
    required_entries = [
        '.env',
        '.env.local',
        '*.log',
        '*.key',
        '*.pem',
        '*.secret',
        'credentials.json'
    ]
    
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        return ["  ❌ .gitignore文件不存在"]
    
    content = gitignore_path.read_text()
    issues = []
    
    for entry in required_entries:
        if entry not in content:
            issues.append(f"  ⚠️  .gitignore缺少: {entry}")
    
    return issues

def validate_env_example():
    """验证.env.example是否存在且完整"""
    env_example = Path('.env.example')
    if not env_example.exists():
        return ["  ⚠️  .env.example不存在"]
    
    content = env_example.read_text()
    issues = []
    
    # 检查是否有示例值
    if 'your_api_key_here' not in content and 'your_secret_here' not in content:
        issues.append("  ⚠️  .env.example缺少示例值标记")
    
    # 检查是否有真实密钥（不应该有）
    real_key_patterns = [
        r'[a-z0-9]{32,}',  # 可能是真实密钥
        r'sk-[a-zA-Z0-9]{48}',  # OpenAI格式
        r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'  # UUID格式
    ]
    
    import re
    for pattern in real_key_patterns:
        if re.search(pattern, content):
            issues.append(f"  🔴 .env.example可能包含真实密钥")
    
    return issues

def main():
    """主函数"""
    print("🔍 配置验证检查")
    print("=" * 60)
    
    all_passed = True
    
    # 1. 检查硬编码密钥
    print("\n1️⃣  检查硬编码密钥...")
    secret_issues = validate_no_hardcoded_secrets()
    if secret_issues:
        print("❌ 发现硬编码密钥:")
        for issue in secret_issues:
            print(issue)
        all_passed = False
    else:
        print("✅ 未发现硬编码密钥")
    
    # 2. 检查.gitignore
    print("\n2️⃣  检查.gitignore...")
    gitignore_issues = validate_gitignore()
    if gitignore_issues:
        print("⚠️  .gitignore需要改进:")
        for issue in gitignore_issues:
            print(issue)
    else:
        print("✅ .gitignore配置正确")
    
    # 3. 检查.env.example
    print("\n3️⃣  检查.env.example...")
    env_issues = validate_env_example()
    if env_issues:
        print("⚠️  .env.example需要改进:")
        for issue in env_issues:
            print(issue)
        all_passed = False
    else:
        print("✅ .env.example配置正确")
    
    # 4. 检查环境变量
    print("\n4️⃣  检查必需的环境变量...")
    required_vars = ['ZHIPUAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️  缺少环境变量: {', '.join(missing_vars)}")
        print("   提示: 开发环境请在.env.local中配置")
    else:
        print("✅ 所有必需环境变量已配置")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 配置验证通过")
        return 0
    else:
        print("❌ 配置验证失败，请修复上述问题")
        return 1

if __name__ == '__main__':
    sys.exit(main())
