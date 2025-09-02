# core/concurrency_optimizer.py
import os
import psutil
import math
from config.settings import CONCURRENCY_CONFIG


class ConcurrencyOptimizer:
    """并发优化器 - 智能计算最优并发数"""

    def __init__(self):
        self.system_cores = os.cpu_count() or 4
        self.config = CONCURRENCY_CONFIG

    def calculate_optimal_concurrency(self,
                                      total_slices: int,
                                      audio_duration: float,
                                      consider_system_load: bool = True) -> int:
        """
        计算最优并发数（针对长音频优化）

        Args:
            total_slices: 总切片数量
            audio_duration: 音频总时长（秒）
            consider_system_load: 是否考虑系统当前负载

        Returns:
            推荐的最大并发数
        """
        # 1. 基于CPU核心数的计算（基础限制）
        cpu_based = self._calculate_cpu_based()

        # 2. 基于切片数量的计算
        slice_based = self._calculate_slice_based(total_slices)

        # 3. 基于音频时长的计算（长音频优化）
        duration_based = self._calculate_duration_based(audio_duration)

        # 4. 考虑系统当前负载（可选）
        if consider_system_load:
            load_based = self._calculate_load_based()
            # 取更保守的值
            cpu_based = min(cpu_based, load_based)

        # 5. 综合计算（取各种计算的最小值）
        optimal = min(cpu_based, slice_based, duration_based, self.config["max_concurrent_limit"])

        # 6. 确保不低于最小值
        optimal = max(optimal, self.config["min_concurrent_limit"])

        return optimal

    def _calculate_cpu_based(self) -> int:
        """基于CPU核心数的计算"""
        # 留出1-2个核心给系统和其他进程
        if self.system_cores <= 4:
            return max(1, self.system_cores - 1)  # 小核心系统保守一些
        else:
            return max(2, self.system_cores - 2)  # 大核心系统可以多分配一些

    def _calculate_slice_based(self, total_slices: int) -> int:
        """基于切片数量的计算"""
        slices_per_thread = self.config["slices_per_thread"]

        if total_slices <= 5:
            return min(2, total_slices)  # 切片少时保守处理
        elif total_slices <= 15:
            return min(4, math.ceil(total_slices / slices_per_thread))
        else:
            return min(8, math.ceil(total_slices / (slices_per_thread * 1.5)))

    def _calculate_duration_based(self, audio_duration: float) -> int:
        """基于音频时长的计算（长音频优化）"""
        duration_minutes = audio_duration / 60

        if duration_minutes <= 10:  # 10分钟以内
            return 3
        elif duration_minutes <= 30:  # 10-30分钟
            return 4
        elif duration_minutes <= 60:  # 30-60分钟
            return 6
        elif duration_minutes <= 120:  # 1-2小时
            return 8
        else:  # 2小时以上
            return min(10, self.config["max_concurrent_limit"])

    def _calculate_load_based(self) -> int:
        """基于系统当前负载的计算"""
        try:
            # 获取当前CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent

            # 根据系统负载调整并发数
            if cpu_percent > 80 or memory_percent > 80:
                # 高负载时保守处理
                return max(1, self.system_cores // 2)
            elif cpu_percent > 60:
                # 中等负载
                return max(2, self.system_cores - 2)
            else:
                # 低负载，可以更积极
                return self.system_cores

        except Exception:
            # 如果获取系统信息失败，回退到保守策略
            return max(2, self.system_cores - 2)

    def get_system_info(self) -> dict:
        """获取系统信息（用于监控和调试）"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            return {
                "cpu_cores": self.system_cores,
                "cpu_usage_percent": cpu_percent,
                "memory_total_gb": round(memory.total / (1024 ** 3), 1),
                "memory_used_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024 ** 3), 1)
            }
        except Exception:
            return {"cpu_cores": self.system_cores, "error": "无法获取系统信息"}


# 全局实例
concurrency_optimizer = ConcurrencyOptimizer()


# 简化接口函数
def calculate_optimal_concurrency(total_slices: int,
                                  audio_duration: float,
                                  consider_system_load: bool = True) -> int:
    """
    计算最优并发数（简化接口）
    """
    return concurrency_optimizer.calculate_optimal_concurrency(
        total_slices, audio_duration, consider_system_load
    )