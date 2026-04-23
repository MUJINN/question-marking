# post_process_outputs.py
import os
import csv
import json
import hashlib
from datetime import datetime

def list_available_caches(cache_dir="cache_output/score_dimension_cache"):
    """
    列出所有可用的cache文件及其对应的题目信息
    """
    print("📋 可用的cache文件:")
    if not os.path.exists(cache_dir):
        print("❌ cache目录不存在")
        return
    
    cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
    if not cache_files:
        print("❌ 没有找到cache文件")
        return
    
    for cache_file in cache_files:
        cache_path = os.path.join(cache_dir, cache_file)
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                if 'cache_key' in cache_data and len(cache_data['cache_key']) > 0:
                    question = cache_data['cache_key'][0][:100] + "..." if len(cache_data['cache_key'][0]) > 100 else cache_data['cache_key'][0]
                    breakdown_type = cache_data.get('breakdown_type', 'Unknown')
                    subject_id = cache_data.get('subject_id', 'Unknown')
                    question_id = cache_data.get('question_id', 'Unknown')
                    created_at = cache_data.get('created_at', 'Unknown')
                    
                    print(f"  📄 {cache_file}")
                    print(f"     科目ID: {subject_id}")
                    print(f"     题目ID: {question_id}")
                    print(f"     题型: {breakdown_type}")
                    print(f"     创建时间: {created_at}")
                    print(f"     题目: {question}")
                    print()
        except:
            print(f"  ❌ {cache_file} (读取失败)")
            print()
def find_cache_info(question_stem, standard_answer, total_score, cache_dir="cache_output/score_dimension_cache"):
    """
    根据问题、标准答案和总分查找对应的cache文件
    """
    # 生成与marking.py中相同的hash
    cache_key_str = f"{question_stem}|{standard_answer}|{total_score}"
    key_hash = hashlib.md5(cache_key_str.encode("utf-8")).hexdigest()
    cache_file_path = os.path.join(cache_dir, f"{key_hash}.json")
    
    if os.path.exists(cache_file_path):
        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def extract_top_n_outputs(csv_path, api_root_dir, output_dir, top_n=None, specific_cache_file=None, run_base_dir=None):
    """
    从指定 CSV 文件中提取前 N 个 file 字段，并生成对应的结果 JSON 文件。
    """
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    results = []

    # 构建对应的 JSON 响应目录
    # base_name 可能是 "subject_id_question_id" 格式，也可能是旧格式的 "question_id"
    api_response_dir = os.path.join(api_root_dir, base_name)
    if not os.path.exists(api_response_dir):
        # 如果新格式的目录不存在，尝试旧格式（只有question_id）
        # 从 base_name 提取 question_id（如果是 subject_question 格式）
        if '_' in base_name:
            parts = base_name.split('_')
            if len(parts) >= 2:
                old_format_dir = os.path.join(api_root_dir, parts[-1])  # 尝试只用question_id
                if os.path.exists(old_format_dir):
                    api_response_dir = old_format_dir
                    print(f"📌 使用旧格式目录: {parts[-1]}")
                else:
                    print(f"⚠️ 路径不存在: {api_response_dir}")
                    return
        else:
            print(f"⚠️ 路径不存在: {api_response_dir}")
            return

    # 加载cache信息
    current_cache_info = None
    # 尝试多个可能的cache目录位置
    possible_cache_dirs = [
        "cache_output/score_dimension_cache",  # 根目录
    ]
    
    # 如果提供了run_base_dir，添加run目录中的cache路径
    if run_base_dir:
        run_cache_dir = os.path.join(run_base_dir, "cache_output", "score_dimension_cache")
        possible_cache_dirs.insert(0, run_cache_dir)  # 优先检查run目录
    
    print(f"🔍 将检查以下cache目录: {possible_cache_dirs}")
    
    cache_dir = None
    for possible_dir in possible_cache_dirs:
        if os.path.exists(possible_dir):
            cache_dir = possible_dir
            print(f"📁 找到cache目录: {cache_dir}")
            break
    
    if specific_cache_file:
        # 如果指定了特定的cache文件，直接使用
        if cache_dir:
            cache_path = os.path.join(cache_dir, specific_cache_file)
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        current_cache_info = json.load(f)
                        print(f"✅ 使用指定的cache文件: {specific_cache_file}")
                except:
                    print(f"❌ 读取指定cache文件失败: {specific_cache_file}")
            else:
                print(f"⚠️ 指定的cache文件不存在: {cache_path}")
    else:
        # 自动匹配cache信息
        cache_data = {}
        if cache_dir and os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
            print(f"🔍 在cache目录中找到 {len(cache_files)} 个文件")
            
            for cache_file in cache_files:
                cache_path = os.path.join(cache_dir, cache_file)
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache_content = json.load(f)
                        # 使用题目内容作为key来识别不同的题目
                        if 'cache_key' in cache_content and len(cache_content['cache_key']) > 0:
                            question_key = cache_content['cache_key'][0]  # 题目内容
                            cache_data[question_key] = cache_content
                except Exception as e:
                    print(f"⚠️ 读取cache文件失败 {cache_file}: {e}")
                    continue
            print(f"✅ 加载了 {len(cache_data)} 个不同题目的cache信息")
        else:
            print(f"⚠️ 未找到cache目录")
        
        # 通过分析API响应文件来识别当前CSV对应的题目
        sample_files = [f for f in os.listdir(api_response_dir) if f.endswith('.json')]
        if sample_files and cache_data:
            sample_path = os.path.join(api_response_dir, sample_files[0])
            try:
                with open(sample_path, 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)
                    sample_text = sample_data.get('data', {}).get('outputs', {}).get('text', '')
                    
                    # 尝试匹配每个cache，找到最佳匹配
                    best_match = None
                    best_score = 0
                    
                    for question_key, cache_content in cache_data.items():
                        if len(question_key) > 50:  # 确保是完整的题目
                            # 从cache中提取关键词
                            cache_words = set(question_key.replace('。', ' ').replace('，', ' ').replace('（', ' ').replace('）', ' ').split())
                            # 计算在API响应中出现的关键词数量
                            match_score = sum(1 for word in cache_words if len(word) > 1 and word in sample_text)
                            
                            if match_score > best_score:
                                best_score = match_score
                                best_match = cache_content
                    
                    if best_match and best_score > 5:  # 至少匹配5个关键词
                        current_cache_info = best_match
                        print(f"✅ 找到匹配的题目cache信息 (匹配分数: {best_score})")
                    elif cache_data:
                        # 如果没有找到好的匹配，使用第一个可用的
                        current_cache_info = list(cache_data.values())[0]
                        print(f"⚠️ 未找到匹配的cache，使用第一个可用的cache信息")
            except Exception as e:
                if cache_data:
                    current_cache_info = list(cache_data.values())[0]
                    print(f"⚠️ cache匹配过程出错，使用第一个可用的cache信息: {e}")

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if top_n is not None and i >= top_n:
                break
            file_name = row['file']
            json_path = os.path.join(api_response_dir, f"{file_name}.json")

            if not os.path.exists(json_path):
                print(f"未找到文件: {json_path}")
                continue

            try:
                with open(json_path, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
                    outputs = data.get('data', {}).get('outputs', {})
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败: {json_path} | 错误: {e}")
                continue


            result_item = {
                "file": file_name,
                "breakdown_type": row["breakdown_type"],
                "score": float(row["score"]),
                "gt_score": int(row["gt_score"]),
                "diff": float(row["diff"]),
                "elapsed_time": float(row["elapsed_time"]),
                "total_tokens": int(row["total_tokens"]),
                "outputs": outputs
            }
                
            results.append(result_item)

    # 输出路径：{csv_name}_{file}_process.json
    # output_json_path = os.path.join(output_dir, f"{base_name}_{file_name}_process.json")
    #文件名加上时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 格式：年月日_时分秒
    output_json_path = os.path.join(output_dir, f"{base_name}_{file_name}_{timestamp}.json")
        
    # 构建最终的输出结构，将cache信息放在开头
    output_data = {}
    
    # 如果有cache信息，放在最前面
    if current_cache_info:
        output_data["question_info"] = current_cache_info
    
    output_data["results"] = results
    
    with open(output_json_path, 'w', encoding='utf-8') as out_file:
        json.dump(output_data, out_file, ensure_ascii=False, indent=4)

    print(f"✅ 处理完成: {csv_path} -> {output_json_path}")


def copy_main_directories(source_root, target_root):
    """
    复制主要的源数据目录（api_responses 和 evaluation_results_dir）到目标目录
    """
    import shutil
    
    # 复制 api_responses 目录（不包括 dimension_response）
    api_source = os.path.join(source_root, "api_responses")
    if os.path.exists(api_source):
        api_target = os.path.join(target_root, "api_responses")
        os.makedirs(api_target, exist_ok=True)
        
        # 遍历 api_responses 目录，复制每个子目录（跳过 dimension_response）
        for item in os.listdir(api_source):
            if item == "dimension_response":
                continue  # dimension_response 由 copy_additional_directories 处理
            
            item_source = os.path.join(api_source, item)
            if os.path.isdir(item_source):
                item_target = os.path.join(api_target, item)
                if os.path.exists(item_target):
                    shutil.rmtree(item_target)
                shutil.copytree(item_source, item_target)
                print(f"✅ 已复制 API 响应目录: {item}")
    
    # 复制 evaluation_results_dir 目录
    eval_source = os.path.join(source_root, "evaluation_results_dir")
    if os.path.exists(eval_source):
        eval_target = os.path.join(target_root, "evaluation_results_dir")
        if os.path.exists(eval_target):
            shutil.rmtree(eval_target)
        shutil.copytree(eval_source, eval_target)
        print(f"✅ 已复制评估结果目录到汇总结果")

def copy_additional_directories(source_root, target_root, show_warnings=True):
    """
    复制 dimension_response 和 score_dimension_cache 目录到目标目录
    """
    import shutil
    
    # 复制 api_responses/dimension_response/ 目录
    dimension_source = os.path.join(source_root, "api_responses", "dimension_response")
    if os.path.exists(dimension_source):
        dimension_target = os.path.join(target_root, "api_responses", "dimension_response")
        os.makedirs(os.path.dirname(dimension_target), exist_ok=True)
        if os.path.exists(dimension_target):
            shutil.rmtree(dimension_target)
        shutil.copytree(dimension_source, dimension_target)
        print(f"✅ 已复制 dimension_response 目录到汇总结果")
    elif show_warnings:
        print(f"⚠️ 未找到 {dimension_source}")
    
    # 复制 cache_output/score_dimension_cache/ 目录
    cache_source = os.path.join(source_root, "cache_output", "score_dimension_cache")
    if os.path.exists(cache_source):
        cache_target = os.path.join(target_root, "cache_output", "score_dimension_cache")
        os.makedirs(os.path.dirname(cache_target), exist_ok=True)
        if os.path.exists(cache_target):
            shutil.rmtree(cache_target)
        shutil.copytree(cache_source, cache_target)
        print(f"✅ 已复制 score_dimension_cache 目录到汇总结果")
    elif show_warnings:
        print(f"⚠️ 未找到 {cache_source}")

def process_all_csvs(evaluation_dir, api_root_dir, output_dir, top_n=None, cache_mapping=None, run_base_dir=None):
    """
    批量处理 evaluation_dir 下的所有 CSV 文件。
    每个 CSV 对应 api_root_dir 下的同名文件夹。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    csv_files = [f for f in os.listdir(evaluation_dir) if f.endswith(".csv")]
    if not csv_files:
        print("⚠️ 未找到任何 CSV 文件")
        return

    print(f"📊 发现 {len(csv_files)} 个 CSV 文件，开始批量处理...")

    for csv_file in csv_files:
        csv_path = os.path.join(evaluation_dir, csv_file)
        base_name = os.path.splitext(csv_file)[0]
        
        # 检查是否有指定的cache映射
        specific_cache = None
        if cache_mapping and base_name in cache_mapping:
            specific_cache = cache_mapping[base_name]
        else:
            # 尝试使用新的命名规范自动查找cache文件
            # 尝试多个可能的cache目录位置
            possible_cache_dirs = [
                "cache_output/score_dimension_cache",  # 根目录
            ]
            
            # 如果提供了run_base_dir，添加run目录中的cache路径
            if run_base_dir:
                run_cache_dir = os.path.join(run_base_dir, "cache_output", "score_dimension_cache")
                possible_cache_dirs.insert(0, run_cache_dir)  # 优先检查run目录
            
            for cache_dir in possible_cache_dirs:
                if os.path.exists(cache_dir):
                    cache_files = os.listdir(cache_dir)
                    
                    # base_name 可能是 "subject_id_question_id" 或 "question_id"
                    # 提取 subject_id 和 question_id 进行匹配
                    if '_' in base_name:
                        # 新格式：subject_id_question_id
                        parts = base_name.split('_')
                        if len(parts) >= 2:
                            subject_id = parts[0]
                            question_id = parts[1]
                            # 优先匹配新格式的cache文件名
                            target_cache_name = f"subject_{subject_id}_question_{question_id}.json"
                            if target_cache_name in cache_files:
                                specific_cache = target_cache_name
                                print(f"🎯 自动匹配到cache文件: {target_cache_name} (从{cache_dir})")
                                break
                    else:
                        # 旧格式：只有 question_id
                        question_id = base_name
                    
                    # 尝试匹配包含 question_id 的cache文件
                    for cache_file in cache_files:
                        if cache_file.endswith('.json') and f'question_{question_id}.json' in cache_file:
                            specific_cache = cache_file
                            print(f"🎯 自动匹配到cache文件: {cache_file} (从{cache_dir})")
                            break
                    if specific_cache:
                        break
            
        extract_top_n_outputs(csv_path, api_root_dir, output_dir, top_n, specific_cache, run_base_dir)

    print("✅ 所有 CSV 文件处理完成！")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='处理评估结果并生成汇总文件')
    parser.add_argument('--run-dir', type=str, help='指定run目录（例如：run_政治_20250722_180251）')
    parser.add_argument('--list-runs', action='store_true', help='列出所有可用的run目录')
    args = parser.parse_args()
    
    # 列出所有run目录
    if args.list_runs:
        run_dirs = [d for d in os.listdir('.') if d.startswith('run_') and os.path.isdir(d)]
        if run_dirs:
            print("📂 可用的run目录:")
            for run_dir in sorted(run_dirs, reverse=True):
                print(f"  - {run_dir}")
        else:
            print("❌ 没有找到run目录")
        sys.exit(0)
    
    # 确定要处理的目录
    if args.run_dir:
        # 使用指定的run目录
        base_dir = args.run_dir
        if not os.path.exists(base_dir):
            print(f"❌ 指定的run目录不存在: {base_dir}")
            sys.exit(1)
        evaluation_dir = os.path.join(base_dir, "evaluation_results_dir")
        api_root_dir = os.path.join(base_dir, "api_responses")
    else:
        # 尝试自动检测最新的run目录
        run_dirs = [d for d in os.listdir('.') if d.startswith('run_') and os.path.isdir(d)]
        if run_dirs:
            # 使用最新的run目录
            base_dir = sorted(run_dirs, reverse=True)[0]
            evaluation_dir = os.path.join(base_dir, "evaluation_results_dir")
            api_root_dir = os.path.join(base_dir, "api_responses")
            print(f"🔍 自动使用最新的run目录: {base_dir}")
        else:
            # 兼容旧的目录结构
            evaluation_dir = "evaluation_results_dir"
            api_root_dir = "api_responses"
            base_dir = "."
            print("📌 使用传统目录结构")
    
    # 检查必要的目录是否存在
    if not os.path.exists(evaluation_dir):
        print(f"❌ 评估结果目录不存在: {evaluation_dir}")
        sys.exit(1)
    
    if not os.path.exists(api_root_dir):
        print(f"❌ API响应目录不存在: {api_root_dir}")
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"processed_outputs_{timestamp}"
    top_n = None  # 处理所有记录

    # Cache映射配置 (可选)
    cache_mapping = {}
    
    # 开始处理
    process_all_csvs(evaluation_dir, api_root_dir, output_dir, top_n, 
                    cache_mapping if cache_mapping else None, 
                    run_base_dir=base_dir if base_dir != "." else None)
    
    # 复制主要目录（api_responses 和 evaluation_results_dir）
    if base_dir != ".":
        copy_main_directories(base_dir, output_dir)
    
    # 复制额外的目录（dimension_response 和 score_dimension_cache）
    # 注意：这些目录可能在根目录或run目录中
    if base_dir != ".":
        # 如果是run目录，先尝试从run目录复制
        copy_additional_directories(base_dir, output_dir)
    # 总是尝试从根目录复制（如果存在），但不显示警告
    copy_additional_directories(".", output_dir, show_warnings=False)