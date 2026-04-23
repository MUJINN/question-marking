# 智能题目批改系统

这是一个基于AI的高性能批量题目批改系统，支持并发处理、智能缓存、性能监控等功能。

## 功能特点

- 🚀 **高性能并发处理**：支持配置最大并发数，批量处理大量题目
- 💾 **智能缓存机制**：内存缓存 + 磁盘持久化，避免重复调用API
- 📊 **性能监控**：实时监控API调用性能，生成详细的性能报告
- ✅ **数据验证**：严格模式下对输入数据进行类型和范围验证
- 🔄 **自动重试**：网络错误和超时自动重试，提高处理成功率
- 📝 **详细日志**：分级日志系统，支持调试模式
- 🔧 **灵活配置**：支持配置文件和环境变量，易于部署和管理

## 项目结构

```
question-marking/
├── marking.py              # 主程序
├── performance_monitor.py  # 性能监控模块
├── config.json            # 配置文件
├── .env                   # 环境变量文件（敏感信息）
├── .env.example           # 环境变量示例
├── folders.txt            # 待处理文件夹列表
├── api_responses/         # API响应缓存目录
│   └── dimension_response/# 评分维度响应
├── cache_output/          # 缓存输出目录
│   └── score_dimension_cache/ # 评分维度缓存
├── evaluation_results_dir/ # 评估结果CSV文件
├── logs/                  # 日志文件
│   ├── run_*.log         # 运行日志
│   └── metrics.json      # 性能指标
└── failed_samples.log     # 失败样本记录
```

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd question-marking
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

如果没有 requirements.txt，请安装以下依赖：

```bash
pip install pandas regex demjson3 aiohttp tenacity python-dotenv
```

### 3. 配置

#### 环境变量配置

复制环境变量示例文件并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置您的API密钥：

```env
# API配置
API_KEY=your-api-key-here
USER_ID=batch_user

# 可选配置（覆盖config.json中的默认值）
# MAX_CONCURRENT_REQUESTS=20
# API_TIMEOUT=90
```

#### 配置文件说明

`config.json` 包含所有可配置参数：

```json
{
  "api": {
    "url": "API端点URL",
    "timeout": 90,              // API超时时间（秒）
    "retry_attempts": 3,        // 重试次数
    "retry_wait_multiplier": 1, // 重试等待时间倍数
    "retry_wait_max": 10        // 最大重试等待时间（秒）
  },
  "concurrency": {
    "max_concurrent_requests": 20, // 最大并发请求数
    "batch_size": 20              // 批处理大小
  },
  "directories": {
    // 各种目录配置
  },
  "processing": {
    "max_global_retries": 3,      // 全局最大重试次数
    "enable_cache": true,         // 是否启用缓存
    "enable_preload": true        // 是否启用预加载
  },
  "monitoring": {
    "enable_performance_metrics": true, // 启用性能监控
    "metrics_interval_seconds": 60,     // 指标输出间隔
    "enable_detailed_logging": true     // 启用详细日志
  },
  "validation": {
    "strict_mode": true,          // 严格数据验证模式
    "required_fields": [...]      // 必需字段列表
  }
}
```

### 4. 准备数据

创建 `folders.txt` 文件，每行一个文件夹路径：

```
/path/to/folder1
/path/to/folder2
/path/to/folder3
```

每个文件夹应包含待批改的JSON文件，格式如下：

```json
{
  "ocr_results": {
    "question_stem": "题目内容",
    "answer": "标准答案",
    "best_result": "学生答案"
  },
  "evaluation": {
    "total_score": 10,
    "gt_score": 8
  }
}
```

## 使用方法

### 基本使用

```bash
python marking.py
```

### 查看日志

运行日志保存在 `logs/` 目录下：

```bash
# 查看最新日志
tail -f logs/run_*.log

# 查看性能指标
cat logs/metrics.json
```

### 查看结果

评估结果保存在 `evaluation_results_dir/` 目录下的CSV文件中：

```bash
ls evaluation_results_dir/
```

每个CSV文件包含以下字段：
- `file`: 文件名
- `breakdown_type`: 题目类型
- `score`: 预测分数
- `gt_score`: 真实分数
- `diff`: 分数差异
- `elapsed_time`: API响应时间
- `total_tokens`: 使用的token数

## 性能优化建议

### 1. 并发控制

根据API服务器的限制调整并发数：

```json
"max_concurrent_requests": 20  // 增加可提高速度，但可能触发限流
```

### 2. 缓存策略

- **启用缓存**：对于重复的题目，缓存可以大幅提升性能
- **预加载**：在处理前预加载所有题目的评分维度，减少重复请求

### 3. 批处理优化

调整批处理大小以平衡内存使用和处理效率：

```json
"batch_size": 20  // 根据内存情况调整
```

### 4. 性能监控

查看性能报告以识别瓶颈：

```bash
# 实时查看性能指标
watch -n 1 cat logs/metrics.json
```

## 故障排除

### 1. API密钥错误

```
ValueError: 未设置 API_KEY 环境变量
```

解决方法：确保 `.env` 文件存在且包含正确的API密钥。

### 2. 连接超时

增加超时时间：

```json
"timeout": 120  // 增加到120秒
```

### 3. 内存不足

减少并发数和批处理大小：

```json
"max_concurrent_requests": 10,
"batch_size": 10
```

### 4. 缓存问题

清理缓存目录：

```bash
rm -rf cache_output/score_dimension_cache/*
```

## 高级功能

### 性能监控API

`performance_monitor.py` 提供了完整的性能监控功能：

```python
from performance_monitor import PerformanceMonitor, APICallTimer

# 初始化监控器
monitor = PerformanceMonitor(max_history=1000)
monitor.start_monitoring(interval_seconds=60)

# 使用计时器
with APICallTimer(monitor, "api_endpoint"):
    # API调用代码
    pass

# 获取统计信息
stats = monitor.get_statistics()
```

### 数据验证

在严格模式下，系统会验证所有输入数据：

```python
# 验证字段类型
validate_field_type(value, "field_name", (str, int))

# 验证数值范围
validate_numeric_range(score, "score", 0, 100)
```

### 自定义错误处理

系统会记录所有解析失败的样本到 `failed_samples.log`：

```
时间: 2024-01-20 10:30:45
文件名: test_001
错误类型: JSON解析失败
原始响应内容:
...
```

## 输出说明

### 汇总报告

程序会生成带时间戳的汇总CSV文件：

```
summary_results_20240120_103045.csv
```

包含以下信息：
- 文件夹名称
- 题目类型
- 总分统计
- 准确率统计（0分差、1分内、2分内的比例）
- 平均响应时间
- 平均token使用量

### 性能指标

`metrics.json` 包含详细的性能指标：

```json
{
  "timestamp": "2024-01-20T10:30:45",
  "uptime_seconds": 3600,
  "total_requests": 1000,
  "active_requests": 5,
  "cache": {
    "hits": 800,
    "misses": 200,
    "hit_rate": 0.8
  },
  "endpoints": {
    "dimension_api": {
      "count": 200,
      "success": 195,
      "errors": 5,
      "latency": {
        "mean": 1.2,
        "median": 1.0,
        "p95": 2.5,
        "p99": 3.0
      }
    }
  },
  "requests_per_second": 0.28
}
```

## 注意事项

1. **API限流**：请根据API提供商的限制合理设置并发数
2. **数据隐私**：`.env` 文件包含敏感信息，请勿提交到版本控制
3. **磁盘空间**：缓存和日志会占用磁盘空间，定期清理
4. **内存使用**：大批量处理时注意监控内存使用

## 开发指南

### 添加新的验证规则

在 `marking.py` 中添加验证函数：

```python
def validate_custom_rule(value, field_name, file_path=None):
    # 自定义验证逻辑
    if not custom_condition:
        logger.warning(f"自定义验证失败: {field_name}")
        return False
    return True
```

### 扩展性能监控

在 `performance_monitor.py` 中添加新的指标：

```python
def record_custom_metric(self, metric_name, value):
    with self._lock:
        self.custom_metrics[metric_name].append(value)
```

## 许可证

本项目遵循 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请联系项目维护者。