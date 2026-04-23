import time
import json
import statistics
from collections import defaultdict, deque
from datetime import datetime
import threading
import logging
import os

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控类，用于追踪API调用性能和系统资源使用情况"""
    
    def __init__(self, max_history=1000, metrics_output_file="metrics.json"):
        self.max_history = max_history
        self.metrics_output_file = metrics_output_file
        
        # 存储各种性能指标
        self.api_latencies = defaultdict(lambda: deque(maxlen=max_history))
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 实时指标
        self.active_requests = 0
        self.total_requests = 0
        self.start_time = time.time()
        
        # 线程安全锁
        self._lock = threading.Lock()
        
        # 定期输出指标的线程
        self._metrics_thread = None
        self._stop_event = threading.Event()
        
    def start_monitoring(self, interval_seconds=60):
        """启动定期输出指标的线程"""
        if self._metrics_thread is None:
            self._metrics_thread = threading.Thread(
                target=self._periodic_report,
                args=(interval_seconds,),
                daemon=True
            )
            self._metrics_thread.start()
            logger.info(f"性能监控已启动，每 {interval_seconds} 秒输出一次指标")
    
    def stop_monitoring(self):
        """停止监控线程"""
        if self._metrics_thread:
            self._stop_event.set()
            self._metrics_thread.join()
            self._metrics_thread = None
            logger.info("性能监控已停止")
    
    def _periodic_report(self, interval):
        """定期输出性能报告"""
        while not self._stop_event.wait(interval):
            self.generate_report()
    
    def record_api_call(self, endpoint, latency, success=True, error_type=None):
        """记录API调用性能"""
        with self._lock:
            self.total_requests += 1
            self.api_latencies[endpoint].append(latency)
            
            if success:
                self.success_counts[endpoint] += 1
            else:
                self.error_counts[endpoint] += 1
                if error_type:
                    self.error_counts[f"{endpoint}_{error_type}"] += 1
    
    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self.cache_hits += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self.cache_misses += 1
    
    def increment_active_requests(self):
        """增加活跃请求计数"""
        with self._lock:
            self.active_requests += 1
    
    def decrement_active_requests(self):
        """减少活跃请求计数"""
        with self._lock:
            self.active_requests -= 1
    
    def get_statistics(self):
        """获取当前性能统计"""
        with self._lock:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "total_requests": self.total_requests,
                "active_requests": self.active_requests,
                "cache": {
                    "hits": self.cache_hits,
                    "misses": self.cache_misses,
                    "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) 
                                if (self.cache_hits + self.cache_misses) > 0 else 0
                },
                "endpoints": {}
            }
            
            # 计算每个端点的统计信息
            for endpoint, latencies in self.api_latencies.items():
                if latencies:
                    stats["endpoints"][endpoint] = {
                        "count": len(latencies),
                        "success": self.success_counts.get(endpoint, 0),
                        "errors": self.error_counts.get(endpoint, 0),
                        "latency": {
                            "mean": statistics.mean(latencies),
                            "median": statistics.median(latencies),
                            "p95": self._percentile(list(latencies), 95),
                            "p99": self._percentile(list(latencies), 99),
                            "min": min(latencies),
                            "max": max(latencies)
                        }
                    }
            
            # 请求速率
            if stats["uptime_seconds"] > 0:
                stats["requests_per_second"] = self.total_requests / stats["uptime_seconds"]
            
            return stats
    
    def _percentile(self, data, percentile):
        """计算百分位数"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[lower]
        return sorted_data[lower] + (index - lower) * (sorted_data[upper] - sorted_data[lower])
    
    def generate_report(self):
        """生成并保存性能报告"""
        stats = self.get_statistics()
        
        # 输出到日志
        logger.info("=== 性能监控报告 ===")
        logger.info(f"运行时间: {stats['uptime_seconds']:.2f}秒")
        logger.info(f"总请求数: {stats['total_requests']}")
        logger.info(f"活跃请求: {stats['active_requests']}")
        logger.info(f"请求速率: {stats.get('requests_per_second', 0):.2f} req/s")
        logger.info(f"缓存命中率: {stats['cache']['hit_rate']:.2%}")
        
        # 保存到文件
        try:
            with open(self.metrics_output_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存性能指标失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，生成最终报告"""
        self.stop_monitoring()
        self.generate_report()


class APICallTimer:
    """用于计时API调用的上下文管理器"""
    
    def __init__(self, monitor, endpoint, increment_active=True):
        self.monitor = monitor
        self.endpoint = endpoint
        self.increment_active = increment_active
        self.start_time = None
        self.success = True
        self.error_type = None
    
    def __enter__(self):
        self.start_time = time.time()
        if self.increment_active:
            self.monitor.increment_active_requests()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        
        if exc_type:
            self.success = False
            self.error_type = exc_type.__name__
        
        self.monitor.record_api_call(
            self.endpoint,
            latency,
            self.success,
            self.error_type
        )
        
        if self.increment_active:
            self.monitor.decrement_active_requests()
        
        # 不抑制异常
        return False