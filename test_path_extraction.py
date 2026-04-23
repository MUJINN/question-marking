#!/usr/bin/env python3
import os

def extract_subject_and_question_id(folder_path):
    """测试路径提取函数"""
    # 使用os.path进行跨平台路径标准化
    folder_path = os.path.abspath(folder_path)
    normalized_path = os.path.normpath(folder_path)
    
    # 将路径分割成部分（自动处理不同操作系统的路径分隔符）
    path_parts = []
    current = normalized_path
    while current:
        head, tail = os.path.split(current)
        if tail:
            path_parts.insert(0, tail)
        if head == current:  # 到达根目录
            break
        current = head
    
    # 查找包含数字的路径部分
    numeric_parts = [part for part in path_parts if part and part.isdigit()]
    
    print(f"[ID提取] 原始路径: {folder_path}")
    print(f"[ID提取] 标准化路径: {normalized_path}")
    print(f"[ID提取] 路径部分: {path_parts}")
    print(f"[ID提取] 数字部分: {numeric_parts}")
    
    if len(numeric_parts) >= 2:
        # 假设倒数第二个数字是科目ID，最后一个是题目ID
        subject_id = numeric_parts[-2]
        question_id = numeric_parts[-1]
        print(f"[ID提取] 成功提取 - 科目ID: {subject_id}, 题目ID: {question_id}")
        return subject_id, question_id
    elif len(numeric_parts) == 1:
        # 只有一个数字，假设是题目ID
        print(f"[ID提取] 只找到一个数字，作为题目ID: {numeric_parts[0]}")
        return "unknown", numeric_parts[0]
    else:
        # 没有数字，使用folder名称
        folder_name = path_parts[-1] if path_parts else "unknown"
        print(f"[ID提取] 未找到数字ID，使用文件夹名: {folder_name}")
        return "unknown", folder_name

# 测试不同的路径格式
test_paths = [
    "chemistry/9051349/20066939",
    "/home/wangdi5/question-marking/chemistry/9051349/20066939",
    "chemistry/9134808/20066940",
    "D:\\Work\\problem_analysis\\ocr\\sample\\9438222\\prompt_debug\\21958448",
    "./chemistry/9245623/20066941",
    "sample/9438222/prompt_debug/21958448",
    "9438222/21958448"
]

print("=" * 80)
print("测试路径提取函数")
print("=" * 80)

for path in test_paths:
    print(f"\n测试路径: {path}")
    try:
        subject_id, question_id = extract_subject_and_question_id(path)
        print(f"结果 -> 科目ID: {subject_id}, 题目ID: {question_id}")
    except Exception as e:
        print(f"错误: {e}")
    print("-" * 40)