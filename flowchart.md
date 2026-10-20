# Dotsquares CodeAI RAG flow

```mermaid
flowchart TD
    A[Student opens chat] --> B[Frontend loads course catalog from FastAPI]
    B --> C[Student asks a question]
    C --> D[POST /api/chat]
    D --> E[Normalize and tokenize question]
    E --> F[Rank course records with BM25]
    F --> G{Relevant courses found?}
    G -->|No| H[Return not-found answer without guessing]
    G -->|Yes| I[Build context from matched course records]
    I --> J{OLLAMA_MODEL configured?}
    J -->|Yes| K[Ollama generates answer from retrieved context]
    J -->|No| L[Return retrieved facts directly]
    K --> M[Return answer and course source citations]
    L --> M
    H --> N[Show answer in chat]
    M --> N
```

## Data source

`backend/app/data/courses.json` is the knowledge source for the course
directory, retrieval, and answer context. BM25 retrieval is lexical; it does
not require a vector database or embedding service. Configure a local Ollama
model to synthesize retrieved facts into conversational answers.

## API

- `GET /` serves the chatbot page.
- `GET /api/courses` returns the course records used by the UI.
- `POST /api/chat` accepts a question and returns an answer, source courses,
  and the response mode.
- `GET /health` checks the existing optional PostgreSQL connection.
