# Dotsquares CodeAI

Dotsquares CodeAI is a course-advisor chatbot for students exploring technology
training. The chat retrieves relevant courses from a maintained catalog and
answers from that retrieved information instead of relying on browser-side
keyword replies.

## How it works

1. The chat page sends a student's question to `POST /api/chat`.
2. The backend ranks course records from `backend/app/data/courses.json` with
   BM25 text retrieval.
3. With `OLLAMA_MODEL` configured, the retrieved course details are sent to
   that local Ollama model to produce a concise, grounded answer.
4. Without an Ollama model configured, the backend returns the retrieved
   course facts directly. Answers include the course records used as sources.
5. If no course information matches, the chatbot says so instead of guessing.

The catalog data is adapted from the original prototype and is not verified
official Academy information. Confirm course content, availability, fees, and
career claims with Dotsquares before publishing this chatbot to students.

## Run locally on Windows

From the project root, install the backend requirements:

```powershell
python -m pip install -r backend\requirements.txt
```

Start the API and web app:

```powershell
Set-Location backend
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The HTML page and API are served from the same
FastAPI process. The course assistant works in retrieval-only mode by default;
PostgreSQL is not required for chat.

## Optional local LLM answers

Install and start Ollama, then download a model, for example:

```powershell
ollama pull qwen2.5:3b
```

Copy `backend\.env.example` to `backend\.env` and set:

```dotenv
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Restart Uvicorn after changing environment settings. If Ollama is configured
but unavailable, chat returns a clear service error rather than silently
falling back to a different response mode.

## Maintain course information

Edit `backend/app/data/courses.json` to add or update course facts. The catalog
API, course browser, and RAG retriever all read this file. Keep fees, schedules,
placement support, and other claims precise and verified; unknown values should
be marked as not listed rather than estimated.

## Tests

Run the retrieval tests from the backend directory:

```powershell
python -m unittest discover -s tests -v
```

## Project structure

```text
second.html                      Chat interface
backend/app/main.py              FastAPI page and chat endpoints
backend/app/services/rag.py      Retrieval and optional Ollama generation
backend/app/data/courses.json    Course knowledge source
backend/tests/test_rag.py        Retrieval tests
```
