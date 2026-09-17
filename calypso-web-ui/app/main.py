import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Calypso AI 中文安全运营与体验控制台 BFF",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.api.system import router as system_router
from app.api.guardrails import router as guardrails_router
from app.api.projects import router as projects_router
from app.api.dashboard import router as dashboard_router
from app.api.redteam import router as redteam_router
from app.api.audit import router as audit_router

app.include_router(system_router, prefix="/api/v1")
app.include_router(guardrails_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(redteam_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


# 若存在前端打包静态目录，则挂载静态服务
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not Found")
