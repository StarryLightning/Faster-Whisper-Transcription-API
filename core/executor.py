import atexit
from concurrent.futures import ThreadPoolExecutor

from config.settings import MAX_WORKERS

# 全局线程池
executor = ThreadPoolExecutor(max_workers = MAX_WORKERS)

def shutdown_executor():
    executor.shutdown(wait=True)

atexit.register(shutdown_executor)