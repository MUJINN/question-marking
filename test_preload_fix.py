#!/usr/bin/env python3

import os

def extract_subject_and_question_id(folder_path):
    """测试ID提取函数"""
    normalized_path = folder_path.replace('\\\\', '/').replace(chr(92), '/')
    path_parts = [part for part in normalized_path.split('/') if part]
    numeric_parts = [part for part in path_parts if part and part.isdigit()]
    
    if len(numeric_parts) >= 2:
        subject_id = numeric_parts[-2]
        question_id = numeric_parts[-1]
        return subject_id, question_id
    elif len(numeric_parts) == 1:
        return 'unknown', numeric_parts[0]
    else:
        folder_name = path_parts[-1] if path_parts else 'unknown'
        return 'unknown', folder_name

def test_preload_logic():
    """测试预加载阶段的ID映射逻辑"""
    print("=== 测试预加载ID映射逻辑 ===")
    
    # 1. 从folders.txt建立题目ID到科目ID的映射
    question_to_subject_map = {}
    try:
        with open('/home/wangdi5/question-marking/folders.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    subject_id, question_id = extract_subject_and_question_id(line)
                    if subject_id != "unknown" and question_id != "unknown":
                        question_to_subject_map[question_id] = subject_id
        print(f"建立题目ID到科目ID映射: {len(question_to_subject_map)} 个映射关系")
        for q_id, s_id in question_to_subject_map.items():
            print(f"  题目ID {q_id} -> 科目ID {s_id}")
    except Exception as e:
        print(f"无法读取folders.txt建立ID映射: {e}")
        return
    
    print()
    
    # 2. 模拟api_responses路径的ID提取
    test_paths = [
        'api_responses/21958448/202315005.json',
        'api_responses/21072798/student123.json',
        'api_responses/21072799/student456.json'
    ]
    
    for file_path in test_paths:
        print(f"处理路径: {file_path}")
        
        # 从路径提取题目ID
        normalized_path = file_path.replace('\\\\', '/').replace(chr(92), '/')
        path_parts = [part for part in normalized_path.split('/') if part]
        numeric_parts = [part for part in path_parts if part and part.isdigit()]
        
        subject_id, question_id = "unknown", "unknown"
        if numeric_parts:
            question_id = numeric_parts[0]
            subject_id = question_to_subject_map.get(question_id, "unknown")
        
        print(f"  提取的题目ID: {question_id}")
        print(f"  映射的科目ID: {subject_id}")
        
        # 测试缓存文件命名条件
        if subject_id and question_id and subject_id != "unknown":
            cache_filename = f"subject_{subject_id}_question_{question_id}.json"
            print(f"  缓存文件名: {cache_filename} (新格式)")
        else:
            print(f"  缓存文件名: MD5哈希.json (旧格式)")
        print()

if __name__ == "__main__":
    test_preload_logic()