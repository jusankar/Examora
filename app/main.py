from fastapi import FastAPI
from app.routes import question_routes

app = FastAPI(title="Examora API")

app.include_router(question_routes.router)