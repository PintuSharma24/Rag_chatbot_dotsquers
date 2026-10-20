import json
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import TypedDict, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
COURSES_PATH = Path(__file__).resolve().parents[1] / "data" / "courses.json"
load_dotenv(COURSES_PATH.parents[2] / ".env")
TOKEN_PATTERN = re.compile(r"[\w+#.-]+", re.UNICODE)
STOP_WORDS = {
    "a", "about", "all", "an", "and", "are", "can", "detail", "details",
    "do", "for", "how", "i", "in", "is", "it", "me", "of", "on", "or",
    "please", "tell", "the", "to", "what", "which", "with", "you",
}
INTENT_TERMS = {
    "duration": {"long", "length", "time", "months"},
    "fees": {"fee", "cost", "price", "tuition"},
    "skills": {"skill", "technology", "technologies", "stack", "learn"},
    "career": {"job", "jobs", "role", "roles", "work"},
}


class OllamaError(Exception):
    pass


class Course(TypedDict):
    id: str
    category: str
    name: str
    duration: str
    level: str
    skills: list[str]
    description: str
    fees: str
    career: str


def _load_courses() -> list[Course]:
    with COURSES_PATH.open(encoding="utf-8") as course_file:
        courses = json.load(course_file)

    if not isinstance(courses, list) or not courses:
        raise ValueError(f"Course data must be a non-empty JSON list: {COURSES_PATH}")

    return cast(list[Course], courses)


def retrieve_courses(question: str, limit: int = 3) -> list[Course]:
    courses = _load_courses()
    if not question.strip():
        return courses

    query_terms = _tokenize(question)
    if not query_terms:
        return []
    query_term_set = set(query_terms)
    title_matches = [
        course for course in courses
        if query_term_set.intersection(_tokenize(course["name"]))
    ]

    documents = [
        _tokenize(" ".join(
            f"{key} {value}"
            for key, value in course.items()
            if key != "id"
        ))
        for course in courses
    ]
    document_frequency = Counter(
        term
        for terms in documents
        for term in set(terms)
    )
    average_length = sum(map(len, documents)) / len(documents)
    scored_courses = []

    for course, terms in zip(courses, documents):
        if len(title_matches) == 1 and course is not title_matches[0]:
            continue
        term_counts = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = term_counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            length_normalizer = 1.2 * (
                1 - 0.75 + 0.75 * len(terms) / average_length
            )
            score += inverse_frequency * (
                frequency * 2.2 / (frequency + length_normalizer)
            )

        if score > 0:
            scored_courses.append((score, course))

    scored_courses.sort(key=lambda result: result[0], reverse=True)
    if scored_courses and scored_courses[0][0] < 0.25:
        return []
    return [course for _, course in scored_courses[:limit]]


def answer_question(question: str) -> tuple[str, list[Course], str]:
    courses = _load_courses()
    if _is_catalog_request(question):
        matches = courses
    else:
        matches = retrieve_courses(question)

    if not matches:
        return (
            "I couldn't find that information in the current course catalog. "
            "Please check with Dotsquares Academy for the latest details.",
            [],
            "retrieval",
        )

    context = "\n\n".join(_format_course(course) for course in matches)
    model = os.getenv("OLLAMA_MODEL", "").strip()
    if model:
        return _generate_with_ollama(question, context, model), matches, "rag"

    return (
        "Based on the course information currently available:\n\n"
        f"{context}\n\n"
        "Course fees and other details not shown in this information should be "
        "confirmed with Dotsquares Academy.",
        matches,
        "retrieval",
    )


def _tokenize(text: str) -> list[str]:
    terms = [term.casefold() for term in TOKEN_PATTERN.findall(text)]
    terms = [term for term in terms if term not in STOP_WORDS]
    for intent, related_terms in INTENT_TERMS.items():
        if {intent}.union(related_terms).intersection(terms):
            terms.extend({intent}.union(related_terms))
    return terms


def _is_catalog_request(question: str) -> bool:
    terms = set(_tokenize(question))
    raw_terms = {
        term.casefold()
        for term in TOKEN_PATTERN.findall(question)
    }
    has_course_topic = bool(
        terms.intersection({
            "ai", "aws", "cloud", "data", "devops", "flutter", "machine",
            "python", "react", "web", "design", "testing",
        })
    )
    return not has_course_topic and bool(
        raw_terms.intersection({"all", "list", "catalog", "programs"})
    )


def _format_course(course: Course) -> str:
    skills = ", ".join(course["skills"])
    return (
        f"Course: {course['name']}\n"
        f"Duration: {course['duration']}\n"
        f"Level: {course['level']}\n"
        f"Topics and skills: {skills}\n"
        f"Description: {course['description']}\n"
        f"Career paths: {course['career']}\n"
        f"Fees: {course['fees']}"
    )


def _generate_with_ollama(question: str, context: str, model: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    payload = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0.1},
        "prompt": (
            "Answer the student's question using only the course information "
            "below. Do not invent prices, schedules, guarantees, or policies. "
            "If the information does not answer the question, say that it is "
            "not listed and recommend confirming with Dotsquares Academy. "
            "Keep the answer concise.\n\n"
            f"Course information:\n{context}\n\n"
            f"Student question: {question}\nAnswer:"
        ),
    }).encode("utf-8")
    request = Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.exception("Ollama generation failed")
        raise OllamaError(
            "The configured Ollama model could not answer. Check that Ollama "
            "is running, the model is installed, and OLLAMA_BASE_URL is correct."
        ) from exc

    if not isinstance(result, dict):
        raise OllamaError("Ollama returned an invalid response.")

    answer = result.get("response")
    if not isinstance(answer, str) or not answer.strip():
        raise OllamaError("Ollama returned an empty answer.")
    return answer.strip()
