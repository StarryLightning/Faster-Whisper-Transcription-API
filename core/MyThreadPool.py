import atexit
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore

from config.settings import CONCURRENCY_CONFIG

MAX_CONCURRENT = CONCURRENCY_CONFIG["max_concurrent_limit"]
MIN_CONCURRENT = CONCURRENCY_CONFIG.get("min_concurrent_limit", 2)

transcribe_semaphore = Semaphore(MAX_CONCURRENT)
# 线程池大小：建议为最大并发数 + 1~2 缓冲，防阻塞
MAX_WORKERS = min(MAX_CONCURRENT + 2, 32)  # 上限 32，避免过多线程
# 全局线程池
executor = ThreadPoolExecutor(max_workers = MAX_WORKERS, thread_name_prefix = "WhisperWorker")
print("🚀 全局线程池已就绪")

def shutdown_executor():
    executor.shutdown(wait=True)

atexit.register(shutdown_executor)