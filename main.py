# main.py
import uvicorn

from config.settings import HOST, PORT, RELOAD, WORKERS

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        workers=WORKERS
    )