from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from app.services.rag import (
    Course,
    OllamaError,
    answer_question,
    retrieve_courses,
)


app = FastAPI(
    title="Dotsquares CodeAI",
    description="Course-advisor API with retrieval-grounded answers",
    version="1.0.0"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, question: str) -> str:
        question = question.strip()
        if len(question) < 2:
            raise ValueError("Question must contain at least two non-space characters.")
        return question


class ChatSource(BaseModel):
    course_id: str
    course_name: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    mode: str


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "second.html")


@app.get("/api/courses")
def list_courses() -> list[Course]:
    return retrieve_courses("")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        answer, courses, mode = answer_question(request.question)
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer,
        sources=[
            ChatSource(course_id=course["id"], course_name=course["name"])
            for course in courses
        ],
        mode=mode,
    )

@app.get("/health")
def health():
    try:
        from sqlalchemy import text
        from app.core.database import engine

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except (SQLAlchemyError, ValueError):
        return {
            "status": "unhealthy",
            "database": "disconnected"
        }