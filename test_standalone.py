#!/usr/bin/env python3
import os
import re
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 复制更新后的函数（独立版本）
def extract_subject_and_question_id(folder_path):
    """从folder路径中提取科目ID和题目ID"""
    # 去除空格
    folder_path = folder_path.strip()
    
    # 检测是否是Windows格式路径
    is_windows_path = bool(re.match(r'^[A-Z]:\\', folder_path)) or '\\' in folder_path
    
    if is_windows_path:
        # 将Windows路径的反斜杠替换为正斜杠
        folder_path = folder_path.replace('\\', '/')
    
    # 分割路径（不使用os.path.split，因为可能混合了Windows和Linux路径）
    parts = folder_path.split('/')
    parts = [p for p in parts if p]  # 移除空部分
    
    # 查找所有数字部分及其位置
    numeric_parts = []
    for i, part in enumerate(parts):
        if part.isdigit():
            numeric_parts.append((i, part))
    
    # 打印调试信息
    logger.debug(f"[ID提取] 原始路径: {folder_path}")
    logger.debug(f"[ID提取] 路径部分: {parts}")
    logger.debug(f"[ID提取] 数字部分: {numeric_parts}")
    
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
                logger.debug(f"[ID提取] 基于{key_dir}目录 - 科目ID: {subject_id}, 题目ID: {question_id}")
                return subject_id, question_id
            elif len(nums_after_key) == 1 and len(numeric_parts) >= 2:
                # 如果关键目录后只有一个数字，尝试使用前一个数字作为科目ID
                for i, num in reversed(numeric_parts):
                    if i < nums_after_key[0][0]:
                        subject_id = num
                        question_id = nums_after_key[0][1]
                        logger.debug(f"[ID提取] 基于{key_dir}目录(组合) - 科目ID: {subject_id}, 题目ID: {question_id}")
                        return subject_id, question_id
    
    # 策略2: 直接使用最后两个数字
    if len(numeric_parts) >= 2:
        subject_id = numeric_parts[-2][1]
        question_id = numeric_parts[-1][1]
        logger.debug(f"[ID提取] 使用最后两个数字 - 科目ID: {subject_id}, 题目ID: {question_id}")
        return subject_id, question_id
    
    # 策略3: 只有一个数字的情况
    if len(numeric_parts) == 1:
        logger.debug(f"[ID提取] 只找到一个数字，作为题目ID: {numeric_parts[0][1]}")
        return "unknown", numeric_parts[0][1]
    
    # 策略4: 没有数字的情况
    folder_name = parts[-1] if parts else "unknown"
    logger.warning(f"[ID提取] 未找到数字ID，使用文件夹名: {folder_name}")
    return "unknown", folder_name

def validate_and_convert_path(path_str):
    """验证并转换路径"""
    import platform
    
    # 去除空格
    path_str = path_str.strip()
    
    # 检测是否是Windows格式路径
    is_windows_path = bool(re.match(r'^[A-Z]:\\', path_str)) or '\\' in path_str
    
    if is_windows_path:
        # 将Windows路径转换为正斜杠格式
        path_str = path_str.replace('\\', '/')
        
        # 在非Windows系统上处理Windows路径
        if platform.system() != 'Windows':
            parts = path_str.split('/')
            parts = [p for p in parts if p]  # 移除空部分
            
            # 查找关键目录
            key_dirs = ['chemistry', 'sample', 'ocr', 'prompt_debug']
            for key_dir in key_dirs:
                if key_dir in parts:
                    key_index = parts.index(key_dir)
                    # 构建相对路径
                    relative_path = os.path.join(*parts[key_index:])
                    if os.path.exists(relative_path):
                        logger.debug(f"[路径转换] 找到存在的路径: {path_str} -> {relative_path}")
                        return relative_path
            
            # 如果没找到关键目录，尝试基于数字ID构建路径
            numeric_parts = [p for p in parts if p.isdigit()]
            if len(numeric_parts) >= 2:
                # 尝试chemistry目录结构
                chemistry_path = os.path.join('chemistry', numeric_parts[-2], numeric_parts[-1])
                if os.path.exists(chemistry_path):
                    logger.debug(f"[路径转换] 构建chemistry路径: {path_str} -> {chemistry_path}")
                    return chemistry_path
                
                # 尝试其他可能的目录结构
                for parent_dir in ['sample', 'ocr', '.']:
                    test_path = os.path.join(parent_dir, numeric_parts[-2], numeric_parts[-1])
                    if os.path.exists(test_path):
                        logger.debug(f"[路径转换] 构建{parent_dir}路径: {path_str} -> {test_path}")
                        return test_path
            
            # 最后尝试只使用数字部分
            if numeric_parts:
                # 构建最简单的路径
                simple_path = os.path.join(*numeric_parts[-2:]) if len(numeric_parts) >= 2 else numeric_parts[-1]
                logger.debug(f"[路径转换] 使用简化路径: {path_str} -> {simple_path}")
                return simple_path
    
    # 对于本地路径，检查是否存在
    if os.path.exists(path_str):
        return path_str
    
    # 如果路径不存在，尝试提取ID并构建可能的路径
    parts = path_str.split('/')
    numeric_parts = [p for p in parts if p.isdigit()]
    if len(numeric_parts) >= 2:
        # 尝试chemistry目录结构
        chemistry_path = os.path.join('chemistry', numeric_parts[-2], numeric_parts[-1])
        if os.path.exists(chemistry_path):
            logger.debug(f"[路径转换] 构建chemistry路径: {path_str} -> {chemistry_path}")
            return chemistry_path
    
    # 如果所有尝试都失败，返回原路径
    logger.debug(f"[路径转换] 无法转换路径，返回原路径: {path_str}")
    return path_str

# 测试用例
test_cases = [
    # 当前工作区的chemistry路径
    "chemistry/9051349/20066939",
    "chemistry/9134808/20066940",
    
    # Windows路径格式（来自folders.txt）
    "D:\\Work\\problem_analysis\\ocr\\sample\\9327634\\prompt_debug\\21403423",
    "D:\\Work\\problem_analysis\\ocr\\sample\\9438218\\prompt_debug\\21950820",
    
    # 其他格式
    "./chemistry/9245623/20066941",
    "9438222/21958448",
]

print("=" * 80)
print("测试更新后的路径处理函数")
print("=" * 80)

for test_path in test_cases:
    print(f"\n测试路径: {test_path}")
    print("-" * 40)
    
    # 1. 测试路径转换
    converted_path = validate_and_convert_path(test_path)
    print(f"转换后路径: {converted_path}")
    print(f"路径是否存在: {os.path.exists(converted_path)}")
    
    # 2. 测试ID提取
    subject_id, question_id = extract_subject_and_question_id(test_path)
    print(f"提取结果: 科目ID={subject_id}, 题目ID={question_id}")
    
    print("=" * 80)