# core/concurrency_optimizer.py
import logging
import os
import psutil
import math
from config.settings import CONCURRENCY_CONFIG

# 配置日志
logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)
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
        else:
            load_based = cpu_based

        # 5. 综合计算 (取切片、时长、负载中的最大值)
        soft_recommend = max(slice_based, duration_based, load_based)
        # 6. 确保不大于cpu上限
        hard_limit = min(cpu_based, self.config["max_concurrent_limit"])

        optimal = min(hard_limit, soft_recommend)
        optimal = max(optimal, self.config["min_concurrent_limit"])

        logger.debug(f"并发计算详情: "
                     f"cpu_based={cpu_based}, "
                     f"slice_based={slice_based}, "
                     f"duration_based={duration_based}, "
                     f"load_based={load_based}, "
                     f"soft={soft_recommend}, hard={hard_limit}, 最终={optimal}")

        return optimal

    def _calculate_cpu_based(self) -> int:
        """基于CPU核心数的计算"""
        # 留出1-2个核心给系统和其他进程
        if self.system_cores <= 4:
            return max(1, self.system_cores - 1)  # 小核心系统保守一些
        elif self.system_cores <= 8:
            return max(2, self.system_cores - 2)  # 8核系统用6线程
        elif self.system_cores <= 16:
            return max(4, self.system_cores - 4)  # 16核系统用12线程
        elif self.system_cores <= 32:
            return max(8, self.system_cores - 8)  # 32核系统用24线程
        else:
            return min(32, int(self.system_cores * 0.75))  # 使用75%的核心


    def _calculate_slice_based(self, total_slices: int) -> int:
        """基于切片数量的计算"""
        slices_per_thread = self.config["slices_per_thread"]

        if total_slices <= 5:
            return min(2, total_slices)
        elif total_slices <= 20:
            return min(8, math.ceil(total_slices / slices_per_thread))
        elif total_slices <= 50:
            return min(16, math.ceil(total_slices / slices_per_thread))
        elif total_slices <= 100:
            return min(24, math.ceil(total_slices / slices_per_thread))
        else:
            return min(
                self.config["max_concurrent_limit"],
                math.ceil(total_slices / slices_per_thread)
            )

    def _calculate_duration_based(self, audio_duration: float) -> int:
        """基于音频时长的计算（长音频优化）"""
        duration_minutes = audio_duration / 60

        if duration_minutes > 60:
            # 1小时以上：建议使用 70%~90% 的 CPU 核心
            return min(
                self.config["max_concurrent_limit"],
                max(4, int(self.system_cores * 0.8))
            )
        elif duration_minutes > 30:
            return min(
                self.config["max_concurrent_limit"],
                max(3, int(self.system_cores * 0.6))
            )
        else:
            return min(
                self.config["max_concurrent_limit"],
                max(2, int(self.system_cores * 0.5))
            )

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