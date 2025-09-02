# main.py
import uvicorn
import logging
from config.settings import HOST, PORT, RELOAD, WORKERS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        workers=WORKERS
    )