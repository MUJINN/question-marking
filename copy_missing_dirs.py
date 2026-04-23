#!/usr/bin/env python3
"""
将 api_responses/dimension_response/ 和 cache_output/score_dimension_cache/ 
复制到指定的运行目录中
"""

import os
import shutil
import sys

def copy_directories_to_run_dir(run_dir):
    """
    复制缺失的目录到运行目录
    """
    # 复制 api_responses/dimension_response/
    dimension_source = "api_responses/dimension_response"
    if os.path.exists(dimension_source):
        dimension_target = os.path.join(run_dir, "api_responses", "dimension_response")
        os.makedirs(os.path.dirname(dimension_target), exist_ok=True)
        if os.path.exists(dimension_target):
            shutil.rmtree(dimension_target)
        shutil.copytree(dimension_source, dimension_target)
        print(f"✅ 已复制 {dimension_source} 到 {dimension_target}")
    else:
        print(f"❌ 未找到源目录: {dimension_source}")
    
    # 复制 cache_output/score_dimension_cache/
    cache_source = "cache_output/score_dimension_cache"
    if os.path.exists(cache_source):
        cache_target = os.path.join(run_dir, "cache_output", "score_dimension_cache")
        os.makedirs(os.path.dirname(cache_target), exist_ok=True)
        if os.path.exists(cache_target):
            shutil.rmtree(cache_target)
        shutil.copytree(cache_source, cache_target)
        print(f"✅ 已复制 {cache_source} 到 {cache_target}")
    else:
        print(f"❌ 未找到源目录: {cache_source}")

if __name__ == "__main__":
    # 默认目标目录
    target_dir = "run_政治_20250722_141014"
    
    # 如果命令行提供了参数，使用命令行参数
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    
    if not os.path.exists(target_dir):
        print(f"❌ 目标目录不存在: {target_dir}")
        sys.exit(1)
    
    print(f"📁 正在将缺失的目录复制到: {target_dir}")
    copy_directories_to_run_dir(target_dir)
    print("✅ 复制完成！")