#!/usr/bin/env python3
import os
import sys
import re

# 导入日志模块
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入修改后的函数
from marking import extract_subject_and_question_id, validate_and_convert_path

# 测试用例
test_cases = [
    # 当前工作区的chemistry路径
    "chemistry/9051349/20066939",
    "chemistry/9134808/20066940",
    
    # Windows路径格式
    "D:\\Work\\problem_analysis\\ocr\\sample\\9438222\\prompt_debug\\21958448",
    "D:\\Work\\problem_analysis\\ocr\\sample\\9327634\\prompt_debug\\21403423",
    
    # 相对路径
    "./chemistry/9245623/20066941",
    "sample/9438222/prompt_debug/21958448",
    
    # 只有数字的路径
    "9438222/21958448",
    
    # 混合格式
    "D:/Work/problem_analysis/ocr/sample/8221337/prompt_debug/16135392"
]

print("=" * 80)
print("测试更新后的路径处理函数")
print("=" * 80)

for test_path in test_cases:
    print(f"\n原始路径: {test_path}")
    print("-" * 40)
    
    # 1. 测试路径转换
    converted_path = validate_and_convert_path(test_path)
    print(f"转换后路径: {converted_path}")
    print(f"路径是否存在: {os.path.exists(converted_path)}")
    
    # 2. 测试ID提取
    subject_id, question_id = extract_subject_and_question_id(test_path)
    print(f"提取结果: 科目ID={subject_id}, 题目ID={question_id}")
    
    print("=" * 80)