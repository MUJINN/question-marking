#!/usr/bin/env python3
import os
import re

def extract_subject_and_question_id_improved(folder_path):
    """
    改进的路径提取函数，支持多种路径格式
    """
    # 去除空格
    folder_path = folder_path.strip()
    
    # 检测是否是Windows格式路径
    is_windows_path = bool(re.match(r'^[A-Z]:\\', folder_path)) or '\\' in folder_path
    
    if is_windows_path:
        # 将Windows路径的反斜杠替换为正斜杠
        folder_path = folder_path.replace('\\', '/')
    
    # 分割路径
    parts = folder_path.split('/')
    parts = [p for p in parts if p]  # 移除空部分
    
    # 查找所有数字部分
    numeric_parts = []
    for i, part in enumerate(parts):
        if part.isdigit():
            numeric_parts.append((i, part))
    
    print(f"[调试] 原始路径: {folder_path}")
    print(f"[调试] 路径部分: {parts}")
    print(f"[调试] 数字部分: {numeric_parts}")
    
    # 策略1: 查找特定目录后的数字ID
    key_dirs = ['chemistry', 'sample', 'ocr', 'prompt_debug']
    for key_dir in key_dirs:
        if key_dir in parts:
            key_index = parts.index(key_dir)
            # 获取关键目录后的所有数字部分
            nums_after_key = [(i, num) for i, num in numeric_parts if i > key_index]
            if len(nums_after_key) >= 2:
                subject_id = nums_after_key[-2][1]
                question_id = nums_after_key[-1][1]
                print(f"[策略1] 基于{key_dir}目录: 科目ID={subject_id}, 题目ID={question_id}")
                return subject_id, question_id
            elif len(nums_after_key) == 1 and len(numeric_parts) >= 2:
                # 如果关键目录后只有一个数字，尝试使用前一个数字作为科目ID
                for i, num in reversed(numeric_parts):
                    if i < nums_after_key[0][0]:
                        subject_id = num
                        question_id = nums_after_key[0][1]
                        print(f"[策略1b] 基于{key_dir}目录: 科目ID={subject_id}, 题目ID={question_id}")
                        return subject_id, question_id
    
    # 策略2: 直接使用最后两个数字
    if len(numeric_parts) >= 2:
        subject_id = numeric_parts[-2][1]
        question_id = numeric_parts[-1][1]
        print(f"[策略2] 使用最后两个数字: 科目ID={subject_id}, 题目ID={question_id}")
        return subject_id, question_id
    
    # 策略3: 只有一个数字的情况
    if len(numeric_parts) == 1:
        print(f"[策略3] 只有一个数字，作为题目ID: {numeric_parts[0][1]}")
        return "unknown", numeric_parts[0][1]
    
    # 策略4: 没有数字的情况
    folder_name = parts[-1] if parts else "unknown"
    print(f"[策略4] 未找到数字，使用文件夹名: {folder_name}")
    return "unknown", folder_name


def validate_and_convert_path_improved(path_str):
    """
    改进的路径验证和转换函数
    """
    path_str = path_str.strip()
    
    # 检测是否是Windows格式路径
    is_windows_path = bool(re.match(r'^[A-Z]:\\', path_str)) or '\\' in path_str
    
    if is_windows_path:
        # 将Windows路径转换为正斜杠格式
        path_str = path_str.replace('\\', '/')
        
        # 尝试提取有意义的部分
        parts = path_str.split('/')
        
        # 查找关键目录
        for key_dir in ['chemistry', 'sample', 'ocr']:
            if key_dir in parts:
                key_index = parts.index(key_dir)
                # 构建相对路径
                relative_path = os.path.join(*parts[key_index:])
                if os.path.exists(relative_path):
                    print(f"[路径转换] 找到存在的路径: {relative_path}")
                    return relative_path
        
        # 如果没找到关键目录，尝试基于数字ID构建路径
        numeric_parts = [p for p in parts if p.isdigit()]
        if len(numeric_parts) >= 2:
            # 尝试chemistry目录结构
            chemistry_path = os.path.join('chemistry', numeric_parts[-2], numeric_parts[-1])
            if os.path.exists(chemistry_path):
                print(f"[路径转换] 构建chemistry路径: {chemistry_path}")
                return chemistry_path
    
    # 对于本地路径，检查是否存在
    if os.path.exists(path_str):
        return path_str
    
    # 如果路径不存在，尝试构建可能的路径
    parts = path_str.split('/')
    numeric_parts = [p for p in parts if p.isdigit()]
    if len(numeric_parts) >= 2:
        # 尝试chemistry目录结构
        chemistry_path = os.path.join('chemistry', numeric_parts[-2], numeric_parts[-1])
        if os.path.exists(chemistry_path):
            print(f"[路径转换] 构建chemistry路径: {chemistry_path}")
            return chemistry_path
    
    return path_str


# 测试用例
test_cases = [
    "chemistry/9051349/20066939",
    "D:\\Work\\problem_analysis\\ocr\\sample\\9438222\\prompt_debug\\21958448",
    "sample/9438222/prompt_debug/21958448",
    "D:\\Work\\problem_analysis\\ocr\\sample\\9327634\\prompt_debug\\21403423",
    "chemistry/9134808/20066940",
    "9438222/21958448",
    "./chemistry/9245623/20066941"
]

print("=" * 80)
print("测试改进的路径提取函数")
print("=" * 80)

for test_path in test_cases:
    print(f"\n测试路径: {test_path}")
    print("-" * 40)
    
    # 先进行路径转换
    converted_path = validate_and_convert_path_improved(test_path)
    print(f"转换后路径: {converted_path}")
    
    # 然后提取ID
    subject_id, question_id = extract_subject_and_question_id_improved(test_path)
    print(f"最终结果: 科目ID={subject_id}, 题目ID={question_id}")
    print("=" * 80)