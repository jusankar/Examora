import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routes import evaluation_routes, question_routes

app = FastAPI(title="Examora API")

app.include_router(question_routes.router)
app.include_router(evaluation_routes.router)
teacher_dist_dir = os.path.join("frontend-shadcn", "dist")
legacy_frontend_dir = "frontend"
teacher_public_dir = os.path.join("frontend-shadcn", "public")

if os.path.isdir(teacher_dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(teacher_dist_dir, "assets")), name="teacher-assets")
    app.mount("/frontend", StaticFiles(directory=teacher_dist_dir), name="frontend")
else:
    app.mount("/frontend", StaticFiles(directory=legacy_frontend_dir), name="frontend")


@app.get("/")
def home():
    return {"message": "Examora API is running. Open /teacher for UI."}


@app.get("/teacher")
def teacher_ui():
    if os.path.exists(os.path.join(teacher_dist_dir, "index.html")):
        return FileResponse(os.path.join(teacher_dist_dir, "index.html"))
    return FileResponse(os.path.join(legacy_frontend_dir, "index.html"))


@app.get("/favicon.svg")
def favicon():
    dist_file = os.path.join(teacher_dist_dir, "favicon.svg")
    public_file = os.path.join(teacher_public_dir, "favicon.svg")
    if os.path.exists(dist_file):
        return FileResponse(dist_file)
    return FileResponse(public_file)


@app.get("/logo-mark.svg")
def logo_mark():
    dist_file = os.path.join(teacher_dist_dir, "logo-mark.svg")
    public_file = os.path.join(teacher_public_dir, "logo-mark.svg")
    if os.path.exists(dist_file):
        return FileResponse(dist_file)
    return FileResponse(public_file)
