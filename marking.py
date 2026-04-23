#  asyncio.Semaphore 并发控制
#  模块级信号量定义与传参方式可选支持
#  任务函数封装
#  预加载和主处理阶段都加入并发限制
#  完整日志说明便于调试

import os
import pandas as pd
import regex as re
import json
import demjson3 as demjson
import csv
from collections import defaultdict, Counter
import asyncio
import aiohttp
import signal
import sys
import datetime
import logging
import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, Dict, List, Tuple, Any
import atexit
from contextlib import nullcontext
from dotenv import load_dotenv
from performance_monitor import PerformanceMonitor, APICallTimer

def extract_subject_and_question_id(folder_path):
    r"""
    从folder路径中提取科目ID和题目ID
    支持多种路径格式：
    - Windows: D:\Work\problem_analysis\ocr\sample\9438222\prompt_debug\21958448
    - Linux: chemistry/9051349/20066939
    返回: (subject_id, question_id)
    
    增强版本：更健壮的路径处理，支持多种路径格式和工作区
    """
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
    """
    验证并转换路径，处理Windows和Linux路径格式
    支持本地路径和远程路径的转换，能够智能识别不同工作区的目录结构
    """
    import os
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

# ===== 配置加载 =====
def load_config():
    """加载配置文件和环境变量"""
    # 加载环境变量
    load_dotenv()
    
    # 加载配置文件
    config_path = "config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 从环境变量获取敏感信息
    api_key = os.getenv('API_KEY')
    if not api_key:
        raise ValueError("未设置 API_KEY 环境变量，请创建 .env 文件或设置环境变量")
    
    user_id = os.getenv('USER_ID', 'batch_user')
    
    # 允许环境变量覆盖配置文件
    max_concurrent = int(os.getenv('MAX_CONCURRENT_REQUESTS', config['concurrency']['max_concurrent_requests']))
    
    return {
        'api_url': config['api']['url'],
        'api_key': api_key,
        'user_id': user_id,
        'api_timeout': config['api']['timeout'],
        'retry_attempts': config['api']['retry_attempts'],
        'retry_wait_multiplier': config['api']['retry_wait_multiplier'],
        'retry_wait_max': config['api']['retry_wait_max'],
        'max_concurrent_requests': max_concurrent,
        'batch_size': config['concurrency']['batch_size'],
        'directories': config['directories'],
        'processing': config['processing'],
        'monitoring': config['monitoring'],
        'validation': config['validation']
    }

# 加载配置
config = load_config()

# ===== 配置部分 =====
api_url = config['api_url']
api_key = config['api_key']
user_id = config['user_id']
output_response_dir = config['directories']['output_response_dir']
dimension_response_dir = config['directories']['dimension_response_dir']
cache_output_dir = config['directories']['cache_output_dir']
score_dimension_cache_dir = config['directories']['score_dimension_cache_dir']

# ⬇⬇⬇ 设置最大并发请求数，防止服务器限流或资源耗尽
semaphore = asyncio.Semaphore(config['max_concurrent_requests'])

# 注释掉根目录的创建，所有输出都在 run_* 目录中
# os.makedirs(output_response_dir, exist_ok=True)
# os.makedirs(dimension_response_dir, exist_ok=True)
# os.makedirs(score_dimension_cache_dir, exist_ok=True)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# ==== 配置日志系统 ====
os.makedirs(config['directories']['logs_dir'], exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
log_file = os.path.join(config['directories']['logs_dir'], f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
log_level = logging.DEBUG if config['monitoring']['enable_detailed_logging'] else logging.INFO
logging.basicConfig(level=log_level, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# ==== 初始化性能监控 ====
performance_monitor = None
if config['monitoring']['enable_performance_metrics']:
    performance_monitor = PerformanceMonitor(
        metrics_output_file=os.path.join(config['directories']['logs_dir'], 'metrics.json')
    )
    performance_monitor.start_monitoring(config['monitoring']['metrics_interval_seconds'])

# 错误类型映射表（英文 -> 中文）
ERROR_TYPE_MAP = {
    "NON_STRING_ANSWER": "非字符串回答",
    "MISSING_JSON_STRUCTURE": "未找到有效 JSON 结构",
    "JSON_PARSE_ERROR": "JSON 解析失败",
    "MISSING_SCORE_FIELD": "缺少 score 字段"
}

# ✅ 全局缓存与统计
dimension_cache = {}  # key: (question_stem, standard_answer) -> (score_dimension_list, breakdown_type)
dimension_request_locks = {}  # key: (question_stem, standard_answer) -> asyncio.Lock
cache_hit_count = 0  # 缓存命中计数器
error_stats = Counter()  # 错误类型统计

def validate_field_type(value: Any, field_name: str, expected_types: tuple, file_path: str = None) -> bool:
    """验证字段类型"""
    if not isinstance(value, expected_types):
        logger.warning(
            f"字段 '{field_name}' 类型错误: 期望 {expected_types}, 实际 {type(value)}"
            + (f" in {file_path}" if file_path else "")
        )
        return False
    return True

def validate_numeric_range(value: Any, field_name: str, min_val: float = None, max_val: float = None, file_path: str = None) -> bool:
    """验证数值范围"""
    try:
        num_value = float(value)
        if min_val is not None and num_value < min_val:
            logger.warning(f"字段 '{field_name}' 值 {num_value} 小于最小值 {min_val}" + (f" in {file_path}" if file_path else ""))
            return False
        if max_val is not None and num_value > max_val:
            logger.warning(f"字段 '{field_name}' 值 {num_value} 大于最大值 {max_val}" + (f" in {file_path}" if file_path else ""))
            return False
        return True
    except (TypeError, ValueError):
        logger.warning(f"字段 '{field_name}' 无法转换为数值: {value}" + (f" in {file_path}" if file_path else ""))
        return False

def normalize_score_dimension(score_dimension):
    if isinstance(score_dimension, list):
        return score_dimension
    elif isinstance(score_dimension, str):
        items = [item.strip() for item in score_dimension.strip().split('。') if item.strip()]
        return items
    else:
        return None


def load_cache_from_disk():
    """从全局缓存目录加载已有缓存到内存"""
    global dimension_cache
    
    # 只从全局缓存加载（根目录的缓存）
    global_cache_dir = "cache_output/score_dimension_cache"
    
    if os.path.exists(global_cache_dir):
        cache_files = [f for f in os.listdir(global_cache_dir) if f.endswith('.json')]
        logger.info(f"正在从全局缓存加载文件共 {len(cache_files)} 个...")
        loaded_count = load_cache_from_directory(global_cache_dir)
        logger.info(f"成功从全局缓存加载 {loaded_count} 条记录")
    else:
        logger.info("未找到全局缓存文件夹")
        os.makedirs(global_cache_dir, exist_ok=True)
        logger.info(f"已创建全局缓存目录: {global_cache_dir}")

def load_cache_from_directory(cache_dir):
    """从指定目录加载缓存文件"""
    global dimension_cache
    loaded_count = 0
    
    cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
    for filename in cache_files:
        file_path = os.path.join(cache_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                raw_key = data["cache_key"]
                if len(raw_key) == 3:
                    cache_key = (raw_key[0], raw_key[1], raw_key[2])
                else:
                    cache_key = (raw_key[0], raw_key[1], "0")

                # 如果缓存中已存在该key，跳过（避免重复加载）
                if cache_key not in dimension_cache:
                    dimension_cache[cache_key] = (data["score_dimension"], data["breakdown_type"])
                    loaded_count += 1
        except Exception as e:
            logger.warning(f"加载缓存文件 {filename} 失败: {str(e)}")
    
    return loaded_count

def save_cache_to_disk(cache_key, normalized_score_dimension, breakdown_type, subject_id=None, question_id=None):
    """保存缓存到磁盘，同时保存到全局缓存（供复用）和当前运行缓存（供记录）"""
    import datetime
    
    # 生成缓存文件名
    if subject_id and question_id and subject_id != "unknown":
        cache_filename = f"subject_{subject_id}_question_{question_id}.json"
    else:
        # 兼容旧版本，使用MD5哈希
        key_hash = hashlib.md5(f"{cache_key[0]}|{cache_key[1]}|{cache_key[2]}".encode("utf-8")).hexdigest()
        cache_filename = f"{key_hash}.json"
    
    cache_data = {
        "cache_key": list(cache_key),
        "score_dimension": normalized_score_dimension,
        "breakdown_type": breakdown_type,
        "subject_id": subject_id,
        "question_id": question_id,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    # 1. 保存到全局缓存目录
    global_cache_dir = "cache_output/score_dimension_cache"
    os.makedirs(global_cache_dir, exist_ok=True)
    global_cache_path = os.path.join(global_cache_dir, cache_filename)
    try:
        with open(global_cache_path, 'w', encoding='utf-8') as f_out:
            json.dump(cache_data, f_out, ensure_ascii=False, indent=2)
        logger.debug(f"已保存到全局缓存: {global_cache_path}")
    except Exception as e:
        logger.warning(f"保存全局缓存失败: {str(e)}")
    
    # 2. 保存到当前运行缓存目录
    current_cache_dir = config['directories']['score_dimension_cache_dir']
    if current_cache_dir != global_cache_dir:
        current_cache_path = os.path.join(current_cache_dir, cache_filename)
        try:
            with open(current_cache_path, 'w', encoding='utf-8') as f_out:
                json.dump(cache_data, f_out, ensure_ascii=False, indent=2)
            logger.debug(f"已保存到当前缓存: {current_cache_path}")
        except Exception as e:
            logger.warning(f"保存当前缓存失败: {str(e)}")

def get_folder_hash(folder_path):
    folder_name = os.path.basename(os.path.normpath(folder_path))
    hash_suffix = hashlib.md5(folder_path.encode("utf-8")).hexdigest()[:8]
    return f"{folder_name}_{hash_suffix}"

@retry(
    stop=stop_after_attempt(config['retry_attempts']),
    wait=wait_exponential(multiplier=config['retry_wait_multiplier'], max=config['retry_wait_max']),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    reraise=True
)
async def get_score_dimension_and_breakdown_type(file_path, session, subject_id=None, question_id=None):
    global cache_hit_count

    try:
        logger.debug(f"[维度API] 正在处理: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        question_stem = content.get("ocr_results", {}).get("question_stem")
        subject = "历史"
        standard_answer = content.get("ocr_results", {}).get("answer")
        total_score = content.get("evaluation", {}).get("total_score")

        if not all([question_stem, standard_answer, total_score]):
            logger.info(f"在 {file_path} 中缺少首次 API 调用所需的必填字段.")
            return None, None

        cache_key = (question_stem, standard_answer, total_score)
        if cache_key in dimension_cache:
            cache_hit_count += 1
            if performance_monitor:
                performance_monitor.record_cache_hit()
            logger.debug(f"[缓存命中 #{cache_hit_count}] 使用缓存中的 score_dimension 和 breakdown_type: {cache_key}")
            return dimension_cache[cache_key]
        
        if performance_monitor:
            performance_monitor.record_cache_miss()

        lock = dimension_request_locks.get(cache_key)
        if not lock:
            lock = asyncio.Lock()
            dimension_request_locks[cache_key] = lock

        async with lock:
            if cache_key in dimension_cache:
                return dimension_cache[cache_key]

            data = {
                "inputs": {
                    "question_stem": question_stem,
                    "subject": subject,
                    "standard_answer": standard_answer,
                    "total_score": str(total_score)
                },
                "response_mode": "blocking",
                "user": user_id
            }

            async with semaphore:  # ⬅⬅⬅ 在这里加锁，限制并发数量
                with APICallTimer(performance_monitor, "dimension_api") if performance_monitor else nullcontext():
                    async with session.post(api_url, json=data, ssl=False, timeout=config['api_timeout']) as response:
                        if response.status == 200:
                            response_json = await response.json()

                            # 使用 subject_id_question_id 命名，保持一致性
                            if subject_id and question_id and subject_id != "unknown":
                                dimension_filename = f"{subject_id}_{question_id}_dimension.json"
                            else:
                                # 降级使用原始文件名
                                file_name = os.path.splitext(os.path.basename(file_path))[0]
                                dimension_filename = f"{file_name}_dimension.json"
                            
                            dimension_output_path = os.path.join(config['directories']['dimension_response_dir'], dimension_filename)
                            with open(dimension_output_path, 'w', encoding='utf-8') as f_out:
                                json.dump(response_json, f_out, ensure_ascii=False, indent=2)

                            outputs = response_json.get("data", {}).get("outputs", {})
                            score_dimension = outputs.get("score_dimension")
                            breakdown_type = outputs.get("breakdown_type")

                            if not score_dimension or not breakdown_type:
                                logger.error(f"API returned missing score_dimension or breakdown_type for {file_path}")
                                raise ValueError("Missing required output fields from API.")

                            normalized_score_dimension = normalize_score_dimension(score_dimension)
                            if not normalized_score_dimension:
                                logger.error(f"Failed to parse score_dimension from {file_path}")
                                return None, None

                            dimension_cache[cache_key] = (normalized_score_dimension, breakdown_type)

                            # 使用统一的缓存保存函数，同时保存到全局缓存和当前运行缓存
                            save_cache_to_disk(cache_key, normalized_score_dimension, breakdown_type, subject_id, question_id)

                            return normalized_score_dimension, breakdown_type
                        else:
                            logger.error(f"Initial API call failed for {file_path}, status: {response.status}")
                            return None, None

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning(f"Network error during initial API call for {file_path}: {str(e)}. Retrying...")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in initial API call for {file_path}: {str(e)}")
        return None, None


def extract_score_from_answer_str(answer_str, file_name=None):
    if not isinstance(answer_str, str):
        error_stats["NON_STRING_ANSWER"] += 1
        log_failed_sample(file_name, answer_str, "NON_STRING_ANSWER")
        return None

    logger.debug(f"[解析分数] 开始解析回答字符串: {file_name}")

    # 第一步：清理特殊字符和非标准结构
    clean_str = answer_str
    clean_str = re.sub(r'<think>.*?</think>', '', clean_str, flags=re.DOTALL).strip()
    clean_str = re.sub(r'\\([^\nrtbf"\\])', r'\\\\\1', clean_str)  # 替换非法转义字符
    clean_str = re.sub(r'[\x00-\x1F\x7F]', '', clean_str)         # 移除控制字符
    clean_str = re.sub(r'```json\s*', '', clean_str).strip()       # 去掉代码块包裹

    logger.debug(f"[预处理完成] 清洗后的字符串长度: {len(clean_str)}")

    # 尝试提取最外层 JSON
    raw_json_match = re.search(r'\{(?:[^{}]|(?R))*\}|\$$(?:[^\$$]|(?R))*\$$', clean_str, re.DOTALL)
    if raw_json_match:
        json_str = raw_json_match.group(0)
        try:
            answer_data = demjson.decode(json_str)
            score = answer_data.get("score")
            if score is not None:
                logger.debug(f"[JSON解析成功] 提取到 score: {score}")
                return int(score)
        except demjson.JSONDecodeError as e:
            logger.warning(f"[JSON解析失败] 第一次尝试失败: {str(e)}")

    # 第二步：进一步清理 reason 字段中的裸引号和其他干扰
    try:
        # 强制修复带中文引号的字段
        clean_str = re.sub(r'"([^"]*?)"', lambda m: '"%s"' % m.group(1).replace('"', '\\"'), clean_str, count=1)
        answer_data = demjson.decode(clean_str)
        score = answer_data.get("score")
        if score is not None:
            logger.debug(f"[二次解析成功] 提取到 score: {score}")
            return int(score)
    except demjson.JSONDecodeError:
        logger.warning(f"[二次解析失败] 无法从回答中提取 JSON 内容")

    # 第三步：兜底策略 —— 手动提取 score 数值
    score_match = re.search(r'"score"\s*:\s*(\d+)', clean_str)
    if score_match:
        logger.warning(f"[回退提取] 成功从 {file_name} 提取到 score: {score_match.group(1)}")
        return int(score_match.group(1))

    # 第四步：最终失败处理
    logger.warning("[WARNING] 未找到有效的 JSON 结构")
    error_stats["MISSING_JSON_STRUCTURE"] += 1
    log_failed_sample(file_name, answer_str, "MISSING_JSON_STRUCTURE")
    return None
def log_failed_sample(file_name, answer_str, error_type, error_details=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    zh_type = ERROR_TYPE_MAP.get(error_type, error_type)
    with open("failed_samples.log", "a", encoding="utf-8") as f:
        f.write(f"时间: {timestamp}\n")
        f.write(f"文件名: {file_name}\n")
        f.write(f"错误类型: {zh_type}\n")
        if error_details:
            f.write(f"错误详情: {error_details}\n")

        f.write(f"原始响应内容:\n{answer_str}\n")
        f.write("-" * 50 + "\n")


async def process_file(file_path, session, output_dir, subject_id=None, question_id=None):
    try:
        logger.debug(f"[开始处理] 文件: {file_path}")

        file_name = os.path.splitext(os.path.basename(file_path))[0]
        logger.debug(f"[加载文件] 正在读取 JSON 文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        # 提取字段
        student_answer = content.get("ocr_results", {}).get("best_result")
        answer = content.get("ocr_results", {}).get("answer")
        total_score = content.get("evaluation", {}).get("total_score")
        question_stem = content.get("ocr_results", {}).get("question_stem")
        gt_score = content.get("evaluation", {}).get("gt_score", 0)
        
        # 严格模式下进行数据验证
        if config['validation']['strict_mode']:
            validations = [
                validate_field_type(student_answer, "student_answer", (str,), file_path),
                validate_field_type(answer, "answer", (str,), file_path),
                validate_field_type(question_stem, "question_stem", (str,), file_path),
                validate_numeric_range(total_score, "total_score", 0, 100, file_path),
                validate_numeric_range(gt_score, "gt_score", 0, 100, file_path)
            ]
            if not all(validations):
                logger.warning(f"数据验证失败: {file_path}")
                return None

        if not all([student_answer, answer, total_score, question_stem]):
            logger.info(f"Missing required fields in {file_path}. Skipping.")
            return None

        logger.debug(f"[调用维度API] 获取评分维度和题型: {file_path}")
        score_dimension_list, breakdown_type = await get_score_dimension_and_breakdown_type(file_path, session, subject_id, question_id)
        if not score_dimension_list or not breakdown_type:
            logger.info(f"Failed to retrieve score_dimension or breakdown_type for {file_path}. Skipping.")
            return None

        score_dimension_str = json.dumps(score_dimension_list, ensure_ascii=False)

        data = {
            "inputs": {
                "student_answer": student_answer,
                "standard_answer": answer,
                "total_score": str(total_score),
                "question_stem": question_stem,
                "subject": "历史",
                "score_dimension": score_dimension_str,
                "breakdown_type": breakdown_type
            },
            "response_mode": "blocking",
            "user": user_id
        }

        logger.debug(f"[调用评分API] 向 API 发送请求: {file_path}")
        async with semaphore:  # ⬅ 主流程中也加锁
            with APICallTimer(performance_monitor, "scoring_api") if performance_monitor else nullcontext():
                async with session.post(api_url, json=data, ssl=False, timeout=config['api_timeout']) as response:
                    if response.status == 200:
                        logger.debug(f"[API返回] 成功收到响应: {file_path}")
                        response_json = await response.json()

                        response_output_path = os.path.join(output_dir, f"{file_name}.json")
                        with open(response_output_path, 'w', encoding='utf-8') as f_out:
                            json.dump(response_json, f_out, ensure_ascii=False, indent=2)

                        answer_str = response_json.get("data", {}).get("outputs", {}).get("text", "")
                        elapsed_time = response_json.get("data", {}).get("elapsed_time", 0)
                        total_tokens = response_json.get("data", {}).get("total_tokens", 0)

                        logger.debug(f"[提取分数] 解析回答文本中的 score 字段: {file_path}")
                        score = extract_score_from_answer_str(answer_str, file_name=file_name)

                        if score is not None:
                            score = float(score)
                            diff = abs(score - gt_score)
                            logger.info(f"[成功处理] 文件: {file_path} | Score: {score}, GT Score: {gt_score}, Diff: {diff:.2f}")
                            return {
                                "file": file_name,
                                "score": score,
                                "gt_score": gt_score,
                                "diff": diff,
                                "elapsed_time": elapsed_time,
                                "total_tokens": total_tokens,
                                "breakdown_type": breakdown_type
                            }
                        else:
                            logger.warning(f"[评分失败] 未找到有效 score 字段: {file_path}")
                    else:
                        logger.warning(f"[HTTP错误] 请求失败: {file_path}, 状态码: {response.status}")
    except Exception as e:
        logger.error(f"[异常捕获] 处理文件时出错: {file_path} | 错误: {str(e)}", exc_info=True)
    return "retry"


async def process_folder(folder, session, evaluation_results_dir="evaluation_results_dir"):
    folder = folder.strip()
    
    # 验证并转换路径
    folder = validate_and_convert_path(folder)
    
    if not folder or not os.path.isdir(folder):
        logger.info(f"跳过无效路径: {folder}")
        return None

    logger.info(f"\n=== 开始处理文件夹: {folder} ===")
    
    # 提取科目ID和题目ID
    subject_id, question_id = extract_subject_and_question_id(folder)
    
    # 如果提取失败，尝试从文件内容中获取
    if subject_id == "unknown" or question_id == "unknown":
        logger.warning(f"[ID提取] 从路径提取失败，尝试从文件内容提取...")
        # 尝试读取文件夹中的第一个JSON文件来获取ID信息
        try:
            sample_files = [f for f in os.listdir(folder) if f.endswith('.json')][:1]
            if sample_files:
                sample_path = os.path.join(folder, sample_files[0])
                with open(sample_path, 'r', encoding='utf-8') as f:
                    sample_content = json.load(f)
                    # 尝试从文件内容中提取ID（如果有的话）
                    if 'subject_id' in sample_content:
                        subject_id = str(sample_content['subject_id'])
                    if 'question_id' in sample_content:
                        question_id = str(sample_content['question_id'])
        except Exception as e:
            logger.debug(f"[ID提取] 从文件内容提取失败: {e}")
    
    logger.info(f"[ID提取] 最终结果 - 科目ID: {subject_id}, 题目ID: {question_id}")
    
    # 使用 subject_id_question_id 作为文件夹名，避免不同科目的题目ID冲突
    if subject_id != "unknown" and question_id != "unknown":
        folder_name = f"{subject_id}_{question_id}"
    else:
        # 如果无法提取ID，则使用原始文件夹名
        folder_name = os.path.basename(os.path.normpath(folder))
    
    folder_output_dir = os.path.join(config['directories']['output_response_dir'], folder_name)
    os.makedirs(folder_output_dir, exist_ok=True)

    file_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(folder)
        for file in files if file.endswith(".json")
    ]

    logger.debug(f"[{folder}] 找到 {len(file_paths)} 个 JSON 文件")

    if not file_paths:
        logger.info(f"文件夹中没有 JSON 文件: {folder}")
        return None

    stats_output_dir = evaluation_results_dir
    os.makedirs(stats_output_dir, exist_ok=True)
    output_csv = os.path.join(stats_output_dir, f"{folder_name}.csv")
    results = []

    start_time = datetime.datetime.now()

    tasks = [process_file(file_path, session, folder_output_dir, subject_id, question_id) for file_path in file_paths]
    batch_size = config['batch_size']
    retry_files = []
    for i in range(0, len(file_paths), batch_size):
        try:
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            for idx, r in enumerate(batch_results):
                if isinstance(r, Exception):
                    logger.error(f"处理文件时出错 {file_paths[i + idx]}: {r}")
                    retry_files.append(file_paths[i + idx])
                elif r and r != "retry":
                    results.append(r)
                elif r == "retry":
                    retry_files.append(file_paths[i + idx])
            logger.info(f"Processing files [{i + 1}/{len(file_paths)}]")
        except Exception as e:
            logger.error(f"批处理过程中出错: {e}")
            # 将当前批次的所有文件加入重试列表
            retry_files.extend(file_paths[i:i + batch_size])

    retry_count = 0
    max_retries = config['processing']['max_global_retries']
    while retry_files and retry_count < max_retries:
        retry_count += 1
        logger.info(f"\n=== 第 {retry_count} 次重试处理失败文件 ===")
        try:
            retry_tasks = [process_file(file_path, session, folder_output_dir, subject_id, question_id) for file_path in retry_files]
            retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)
            new_retry_files = []
            for idx, result in enumerate(retry_results):
                if isinstance(result, Exception):
                    logger.error(f"重试处理文件时出错 {retry_files[idx]}: {result}")
                    new_retry_files.append(retry_files[idx])
                elif result == "retry":
                    new_retry_files.append(retry_files[idx])
                elif result:
                    results.append(result)
        except Exception as e:
            logger.error(f"重试批处理过程中出错: {e}")
            new_retry_files = retry_files  # 保留所有文件用于下次重试
        retry_files = new_retry_files

    if retry_files:
        logger.info(f"仍有 {len(retry_files)} 个文件未能成功处理。")

    with open(output_csv, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["file", "breakdown_type","score", "gt_score", "diff", "elapsed_time", "total_tokens"])
        writer.writeheader()
        writer.writerows(results)

    total_score_sum = sum(r['score'] for r in results)
    diff_count = defaultdict(int)
    for r in results:
        diff = round(abs(r['score'] - r['gt_score']), 2)
        diff_count[diff] += 1

    total = len(results)
    zero_count = diff_count.get(0, 0)
    within_1_count = sum(diff_count.get(i, 0) for i in range(0, 2))
    within_2_count = sum(diff_count.get(i, 0) for i in range(0, 3))

    zero_ratio = zero_count / total if total > 0 else 0
    within_1_ratio = within_1_count / total if total > 0 else 0
    within_2_ratio = within_2_count / total if total > 0 else 0

    avg_elapsed_time = (sum(r['elapsed_time'] for r in results) / total) if total > 0 else 0
    avg_total_tokens = (sum(r['total_tokens'] for r in results) / total) if total > 0 else 0
    end_time = datetime.datetime.now()
    total_seconds = (end_time - start_time).total_seconds()
    avg_time = total_seconds / total if total > 0 else 0

    sample_breakdown_type = results[0]['breakdown_type'] if results else '未知'

    logger.info(f"完成处理文件夹: {folder}")
    logger.info(f"总分: {total_score_sum}")
    logger.info(f"差值为 0 的占比: {zero_ratio:.2%}")
    logger.info(f"差值不超过 1 的占比: {within_1_ratio:.2%}")
    logger.info(f"差值不超过 2 的占比: {within_2_ratio:.2%}")
    logger.info(f"共命中缓存 {cache_hit_count} 次")

    return {
        "folder": folder,
        "total_score_sum": round(total_score_sum, 2),
        "zero_ratio": round(zero_ratio, 4),
        "within_1_ratio": round(within_1_ratio, 4),
        "within_2_ratio": round(within_2_ratio, 4),
        "avg_elapsed_time": round(avg_elapsed_time, 2),
        "avg_total_tokens": round(avg_total_tokens, 2),
        "avg_time": round(avg_time, 2),
        "breakdown_type": sample_breakdown_type
    }


async def pre_fetch_all_dimensions(file_paths, session):
    unique_questions = set()
    logger.info(" 开始扫描所有文件以提取唯一题目...")
    
    # 首先从folders.txt建立题目ID到科目ID的映射
    question_to_subject_map = {}
    try:
        with open("folders.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    subject_id, question_id = extract_subject_and_question_id(line)
                    if subject_id != "unknown" and question_id != "unknown":
                        question_to_subject_map[question_id] = subject_id
        logger.info(f"建立题目ID到科目ID映射: {len(question_to_subject_map)} 个映射关系")
    except Exception as e:
        logger.warning(f"无法读取folders.txt建立ID映射: {e}")

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)

            question_stem = content.get("ocr_results", {}).get("question_stem")
            standard_answer = content.get("ocr_results", {}).get("answer")
            total_score = content.get("evaluation", {}).get("total_score")

            if question_stem and standard_answer and total_score:
                # 从文件路径中提取科目ID和题目ID用于预加载
                # file_path结构是 api_responses/question_id/student_id.json
                # 从路径中提取question_id作为题目ID
                normalized_path = file_path.replace('\\\\', '/').replace(chr(92), '/')
                path_parts = [part for part in normalized_path.split('/') if part]
                numeric_parts = [part for part in path_parts if part and part.isdigit()]
                
                subject_id, question_id = "unknown", "unknown"
                if numeric_parts:
                    # 第一个数字作为题目ID（从api_responses文件夹结构）
                    question_id = numeric_parts[0]
                    # 根据题目ID查找科目ID
                    subject_id = question_to_subject_map.get(question_id, "unknown")
                unique_questions.add((question_stem, standard_answer, total_score, subject_id, question_id))
        except Exception as e:
            logger.warning(f"读取文件失败 {file_path}: {str(e)}")

    logger.info(f"发现 {len(unique_questions)} 个唯一题目需要预加载评分维度...")

    # 检查哪些题目需要API加载（只比较前3个元素，忽略ID信息）
    remaining_questions = [q for q in unique_questions if q[:3] not in dimension_cache]
    logger.info(f"需要通过 API 加载的题目数: {len(remaining_questions)}")

    tasks = [fetch_with_semaphore_enhanced(q, session) for q in remaining_questions]
    await asyncio.gather(*tasks)
    logger.info("✅ 所有评分维度已预加载完毕")


async def fetch_with_semaphore_enhanced(question_tuple, session):
    """处理包含ID信息的题目tuple进行预加载"""
    question_stem, standard_answer, total_score, subject_id, question_id = question_tuple
    cache_key = (question_stem, standard_answer, total_score)
    
    async with semaphore:  # ⬅⬅⬅ 使用全局信号量控制并发
        return await fetch_and_cache_dimension_enhanced(cache_key, session, subject_id, question_id)

async def fetch_with_semaphore(cache_key, session):
    async with semaphore:  # ⬅⬅⬅ 使用全局信号量控制并发
        return await fetch_and_cache_dimension(cache_key, session)


async def fetch_and_cache_dimension_enhanced(cache_key, session, subject_id=None, question_id=None):
    """增强版cache函数，支持新的文件命名格式"""
    global score_dimension_cache_dir
    if cache_key in dimension_cache:
        logger.debug(f"[缓存命中] 已跳过API请求: {cache_key}")
        return

    question_stem, standard_answer, total_score = cache_key

    data = {
        "inputs": {
            "question_stem": question_stem,
            "subject": "历史",
            "standard_answer": standard_answer,
            "total_score": str(total_score)
        },
        "response_mode": "blocking",
        "user": user_id
    }

    try:
        async with session.post(api_url, json=data, ssl=False, timeout=60) as response:
            if response.status == 200:
                response_json = await response.json()
                outputs = response_json.get("data", {}).get("outputs", {})
                score_dimension = outputs.get("score_dimension")
                breakdown_type = outputs.get("breakdown_type")

                normalized_score_dimension = normalize_score_dimension(score_dimension)
                if not normalized_score_dimension:
                    logger.error(f"无法解析 score_dimension: {cache_key}")
                    return

                dimension_cache[cache_key] = (normalized_score_dimension, breakdown_type)

                # 使用统一的缓存保存函数，同时保存到全局缓存和当前运行缓存
                save_cache_to_disk(cache_key, normalized_score_dimension, breakdown_type, subject_id, question_id)

                logger.info(f"✅ 预加载完成: subject_{subject_id}_question_{question_id}")
            else:
                logger.error(f"预加载API请求失败: {cache_key}, 状态码: {response.status}")
    except Exception as e:
        logger.error(f"预加载过程出错: {cache_key}, 错误: {str(e)}")

async def fetch_and_cache_dimension(cache_key, session):
    global score_dimension_cache_dir
    if cache_key in dimension_cache:
        logger.debug(f"[缓存命中] 已跳过API请求: {cache_key}")
        return

    question_stem, standard_answer, total_score = cache_key

    data = {
        "inputs": {
            "question_stem": question_stem,
            "subject": "历史",
            "standard_answer": standard_answer,
            "total_score": str(total_score)
        },
        "response_mode": "blocking",
        "user": user_id
    }

    try:
        async with session.post(api_url, json=data, ssl=False, timeout=60) as response:
            if response.status == 200:
                response_json = await response.json()
                outputs = response_json.get("data", {}).get("outputs", {})
                score_dimension = outputs.get("score_dimension")
                breakdown_type = outputs.get("breakdown_type")

                normalized_score_dimension = normalize_score_dimension(score_dimension)
                if not normalized_score_dimension:
                    logger.error(f"无法解析 score_dimension: {cache_key}")
                    return

                dimension_cache[cache_key] = (normalized_score_dimension, breakdown_type)

                # 使用统一的缓存保存函数，同时保存到全局缓存和当前运行缓存
                save_cache_to_disk(cache_key, normalized_score_dimension, breakdown_type)

                logger.debug(f"[预加载完成] 已缓存题目: {cache_key}")
            else:
                logger.warning(f"预加载失败，HTTP 状态码: {response.status}, 题目: {cache_key}")
    except Exception as e:
        logger.warning(f"预加载失败 {cache_key}: {str(e)}")


def sort_csv_by_diff(folder_path, in_place=False):
    """
    对指定文件夹下的所有 .csv 文件按 'diff' 列从大到小排序
    False
    参数:
        folder_path: str - 文件夹路径
        in_place: bool - 是否覆盖原文件，默认 True；若 False，则生成 _sorted.csv 文件
    """
    csv_files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]
    
    if not csv_files:
        logger.info("未找到任何 CSV 文件")
        return

    logger.info(f"开始对 {len(csv_files)} 个 CSV 文件按 diff 排序...")

    for filename in csv_files:
        file_path = os.path.join(folder_path, filename)
        try:
            df = pd.read_csv(file_path)

            # 检查是否存在 diff 列
            if "diff" not in df.columns:
                logger.warning(f"[跳过] 文件 {filename} 中无 'diff' 列，无法排序。")
                continue

            # 排序
            df_sorted = df.sort_values(by="diff", ascending=False).reset_index(drop=True)

            # 输出路径
            if in_place:
                output_path = file_path
            else:
                output_path = os.path.join(folder_path, filename.replace(".csv", "_sorted.csv"))

            # 写回文件
            df_sorted.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"[排序完成] 已处理: {filename}")

        except Exception as e:
            logger.error(f"[排序失败] 处理文件 {filename} 出错: {str(e)}")
async def main_async():
    global score_dimension_cache_dir
    txt_file = "folders.txt"
    if not os.path.exists(txt_file):
        logger.info(f"找不到路径文件: {txt_file}")
        exit(1)
    logger.info(f"[配置加载] API URL: {api_url}")
    logger.info(f"[配置加载] 输出目录: {output_response_dir}")
    logger.info(f"[配置加载] 缓存目录: {score_dimension_cache_dir}")
    logger.info(f"[配置加载] 最大并发数: {semaphore._value}")
    logger.info(f"[配置加载] 批处理大小: {config['batch_size']}")
    logger.info(f"[配置加载] 性能监控: {'启用' if performance_monitor else '禁用'}")

    with open(txt_file, "r", encoding="utf-8") as f:
        folders = [line.strip() for line in f.readlines()]

    logger.info(f"[任务启动] 即将处理以下文件夹: {', '.join(folders)}")

    # 创建带时间戳和科目名称的总输出文件夹
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    subject_name = "历史"  # 当前固定为历史科目
    run_output_dir = f"run_{subject_name}_{timestamp}"
    os.makedirs(run_output_dir, exist_ok=True)
    
    # 在总输出文件夹中创建各个子文件夹
    run_api_responses_dir = os.path.join(run_output_dir, "api_responses")
    run_cache_output_dir = os.path.join(run_output_dir, "cache_output") 
    run_evaluation_results_dir = os.path.join(run_output_dir, "evaluation_results_dir")
    os.makedirs(run_api_responses_dir, exist_ok=True)
    os.makedirs(run_cache_output_dir, exist_ok=True)
    os.makedirs(run_evaluation_results_dir, exist_ok=True)
    
    # 更新配置中的输出目录路径，不修改全局变量
    config['directories']['output_response_dir'] = run_api_responses_dir
    config['directories']['cache_output_dir'] = run_cache_output_dir
    config['directories']['score_dimension_cache_dir'] = os.path.join(run_cache_output_dir, "score_dimension_cache")
    os.makedirs(config['directories']['score_dimension_cache_dir'], exist_ok=True)
    
    # 更新 dimension_response 目录到 run 目录中
    config['directories']['dimension_response_dir'] = os.path.join(run_api_responses_dir, "dimension_response")
    os.makedirs(config['directories']['dimension_response_dir'], exist_ok=True)
    
    # 注意：score_dimension_cache_dir 和 dimension_response_dir 已经是全局变量
    # 直接更新它们的值即可，无需 global 声明
    
    summary_csv_path = os.path.join(run_output_dir, f"summary_results_{timestamp}.csv")
    fieldnames = ["folder","breakdown_type", "total_score_sum", "zero_ratio", "within_1_ratio", "within_2_ratio",
                  "avg_elapsed_time", "avg_total_tokens", "avg_time"]

    with open(summary_csv_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    if config['processing']['enable_cache']:
        load_cache_from_disk()
    else:
        logger.info("缓存已禁用")

    all_file_paths = []
    for folder in folders:
        folder = folder.strip()
        # 验证并转换路径
        folder = validate_and_convert_path(folder)
        if not folder or not os.path.isdir(folder):
            logger.info(f"跳过无效路径: {folder}")
            continue
        file_paths = [
            os.path.join(root, file)
            for root, _, files in os.walk(folder)
            for file in files if file.endswith(".json")
        ]
        all_file_paths.extend(file_paths)

    if config['processing']['enable_preload']:
        logger.info(" 开始全局预加载所有题目维度信息...")
        async with aiohttp.ClientSession(headers=headers) as preload_session:
            await pre_fetch_all_dimensions(all_file_paths, preload_session)
        logger.info(" 全局预加载完成")
    else:
        logger.info("预加载已禁用")

    async with aiohttp.ClientSession(headers=headers) as session:
        for folder in folders:
            stats = await process_folder(folder, session, run_evaluation_results_dir)
            if stats:
                with open(summary_csv_path, mode='a', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerow(stats)
                logger.info(f"已写入 {summary_csv_path}：{stats['folder']}")

    if error_stats:
        logger.info("\n=== 错误类型统计 ===")
        for error_type, count in error_stats.items():
            zh_type = ERROR_TYPE_MAP.get(error_type, error_type)
            logger.info(f"{zh_type}: {count}")

    logger.info("\n所有文件夹处理完成，结果已逐步写入汇总文件。")

    # 自动对当前运行的 evaluation_results_dir 下所有 CSV 文件进行排序
    if os.path.exists(run_evaluation_results_dir):
        sort_csv_by_diff(run_evaluation_results_dir, in_place=True)
    else:
        logger.warning(f"未找到文件夹 {run_evaluation_results_dir}，跳过排序步骤")

def cleanup():
    """清理资源"""
    global performance_monitor
    if performance_monitor:
        logger.info("正在生成最终性能报告...")
        performance_monitor.stop_monitoring()
        performance_monitor.generate_report()
        performance_monitor = None
    logger.info("资源清理完成")

def signal_handler(sig, frame):
    logger.info("\nCaught KeyboardInterrupt, exiting gracefully...")
    cleanup()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup)
    
    try:
        asyncio.run(main_async())
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        cleanup()
        raise
    finally:
        cleanup()