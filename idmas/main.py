"""
IDMAS 应用入口。

启动方式（开发）:
    cd D:\\PanGu-Agent
    PYTHONPATH=. uvicorn idmas.main:app --host 0.0.0.0 --port 8080 --reload

启动方式（生产）:
    uvicorn idmas.main:app --host 0.0.0.0 --port 8080 --workers 2
"""
from idmas.api.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("idmas.main:app", host="0.0.0.0", port=8080, reload=True)
