import json
import os
import unittest
from contextlib import nullcontext
from unittest.mock import patch
from urllib.error import URLError

from fastapi import HTTPException
from app.main import ChatRequest, chat
from app.services.rag import answer_question, retrieve_courses


class StubResponse:
    def read(self):
        return b'{"response":"The Python course lasts 4 Months."}'


class CourseRetrievalTests(unittest.TestCase):
    def test_python_question_retrieves_python_course(self):
        courses = retrieve_courses("What duration is the Python course?")

        self.assertTrue(courses)
        self.assertEqual(courses[0]["id"], "python_ds")

    def test_unrelated_question_has_no_course_match(self):
        self.assertEqual(retrieve_courses("visa application advice"), [])

    def test_catalog_question_lists_all_courses(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": ""}):
            answer, courses, mode = answer_question("List all courses")

        self.assertEqual(len(courses), 7)
        self.assertEqual(mode, "retrieval")
        self.assertIn(courses[0]["name"], answer)

    def test_course_question_returns_source_citation(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": ""}):
            response = chat(ChatRequest(question="How long is the Python course?"))

        self.assertIn("4 Months", response.answer)
        self.assertEqual(response.sources[0].course_id, "python_ds")

    def test_specific_course_question_does_not_list_every_course(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": ""}):
            _, courses, _ = answer_question("Tell me all details about Python")

        self.assertEqual([course["id"] for course in courses], ["python_ds"])

    def test_ollama_receives_retrieved_course_context(self):
        settings = {
            "OLLAMA_MODEL": "test-model",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }
        with (
            patch.dict(os.environ, settings),
            patch(
                "app.services.rag.urlopen",
                return_value=nullcontext(StubResponse()),
            ) as request,
        ):
            response = chat(ChatRequest(question="How long is the Python course?"))

        payload = json.loads(request.call_args.args[0].data)
        self.assertIn("Duration: 4 Months", payload["prompt"])
        self.assertEqual(response.mode, "rag")

    def test_configured_ollama_failure_is_returned_as_service_error(self):
        settings = {"OLLAMA_MODEL": "test-model"}
        with (
            patch.dict(os.environ, settings),
            patch("app.services.rag.urlopen", side_effect=URLError("offline")),
            self.assertLogs("app.services.rag", level="ERROR"),
            self.assertRaises(HTTPException) as error,
        ):
            chat(ChatRequest(question="How long is the Python course?"))

        self.assertEqual(error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
