from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
DEFAULT_OPENAI_MODEL_CANDIDATES = [
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-5.5",
    "gpt-4o-mini",
    "gpt-4o",
]


@dataclass(frozen=True)
class LlmResponse:
    text: str
    provider: str
    model: str
    used_live_model: bool


class ReportingLlmClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_MODEL", "auto").strip() or "auto"
        self.model_candidates = self._model_candidates()

    def complete(self, system_prompt: str, context_pack: dict[str, Any], user_question: str) -> LlmResponse:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return self._preview_response(context_pack, user_question)

        payload = self._base_payload(system_prompt, context_pack, user_question)
        attempted: list[str] = []
        last_error: LlmResponse | None = None
        for model in self.model_candidates:
            attempted.append(model)
            payload["model"] = model
            response = self._request_completion(payload, model)
            if response.used_live_model:
                return response
            last_error = response
            if _is_terminal_error(response.text):
                return response

        if last_error:
            return LlmResponse(
                text=f"{last_error.text} Tried OpenAI models: {', '.join(attempted)}.",
                provider=last_error.provider,
                model=last_error.model,
                used_live_model=False,
            )
        return self._preview_response(context_pack, user_question)

    def _base_payload(self, system_prompt: str, context_pack: dict[str, Any], user_question: str) -> dict[str, Any]:
        return {
            "model": self.model_candidates[0],
            "instructions": system_prompt,
            "input": self._user_content(context_pack, user_question),
            "max_output_tokens": 1400,
        }

    def _request_completion(self, payload: dict[str, Any], model: str) -> LlmResponse:
        request = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            message = _openai_error_message(exc.code, body)
            return LlmResponse(
                text=message,
                provider="openai",
                model=model,
                used_live_model=False,
            )
        except Exception as exc:
            return LlmResponse(
                text=f"OpenAI is currently unavailable. I can still retrieve reporting rule context, but live drafting is paused. Error: {exc}",
                provider="openai",
                model=model,
                used_live_model=False,
            )

        text = _extract_openai_text(data)
        return LlmResponse(
            text=text or "OpenAI returned an empty response.",
            provider="openai",
            model=data.get("model") or model,
            used_live_model=True,
        )

    def _user_content(self, context_pack: dict[str, Any], user_question: str) -> str:
        return (
            "Use the following reporting context pack to answer the user. "
            "Cite retrieved_reporting_guidance citations when they support the answer. "
            "If the context is insufficient, say what is missing.\n\n"
            f"{json.dumps(context_pack, indent=2, default=str)}\n\n"
            f"User question: {user_question}"
        )

    def _model_candidates(self) -> list[str]:
        configured = os.environ.get("OPENAI_MODEL_CANDIDATES", "").strip()
        if configured:
            return _unique_models(configured.split(","))

        if self.model.lower() != "auto":
            return _unique_models([self.model, *DEFAULT_OPENAI_MODEL_CANDIDATES])

        listed_models = self._available_models()
        if listed_models:
            preferred = [model for model in DEFAULT_OPENAI_MODEL_CANDIDATES if model in listed_models]
            remaining = [model for model in listed_models if model.startswith("gpt-") and model not in preferred]
            return _unique_models([*preferred, *remaining])

        return DEFAULT_OPENAI_MODEL_CANDIDATES

    def _available_models(self) -> list[str]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return []
        request = urllib.request.Request(
            OPENAI_MODELS_URL,
            headers={"authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []
        models = data.get("data", [])
        if not isinstance(models, list):
            return []
        return [str(item.get("id")) for item in models if isinstance(item, dict) and item.get("id")]

    def _preview_response(self, context_pack: dict[str, Any], user_question: str) -> LlmResponse:
        guidance = context_pack.get("retrieved_reporting_guidance", [])
        uploads = context_pack.get("session_context", {}).get("uploads", [])
        citations = ", ".join(item.get("citation", "") for item in guidance[:3] if item.get("citation"))
        file_note = f" I also see {len(uploads)} uploaded file(s) in this session." if uploads else ""
        citation_note = f" Relevant rule context retrieved: {citations}." if citations else " No specific rule excerpt was retrieved."
        return LlmResponse(
            text=(
                "Local preview response: I am using the permanent reporting assistant prompt, "
                "retrieved ASC/SEC context, and this session's uploaded-file context for this answer."
                f"{citation_note}{file_note} "
                f"Your question was: {user_question}"
            ),
            provider="local-preview",
            model=self.model,
            used_live_model=False,
        )


def _extract_openai_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in data.get("output", []) if isinstance(data.get("output"), list) else []:
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if not isinstance(content, dict):
                continue
            if isinstance(content.get("text"), str):
                parts.append(content["text"])
            elif isinstance(content.get("output_text"), str):
                parts.append(content["output_text"])
    return "\n".join(part for part in parts if part).strip()


def _openai_error_message(status_code: int, body: str) -> str:
    try:
        payload = json.loads(body)
        message = str(payload.get("error", {}).get("message") or "")
        code = str(payload.get("error", {}).get("code") or "")
    except Exception:
        message = body
        code = ""

    lower = f"{message} {code}".lower()
    if "insufficient_quota" in lower or "quota" in lower or "billing" in lower or "credits" in lower:
        return (
            "OpenAI is connected, but the account needs quota or billing credits before live responses can run. "
            "I can still retrieve reporting rule context and keep the session context ready."
        )
    if status_code == 401:
        return "OpenAI could not authenticate. Check OPENAI_API_KEY in .env."
    if status_code == 429:
        return "OpenAI is rate limited right now. Try again shortly."
    if "model" in lower and ("not found" in lower or "does not exist" in lower or "access" in lower):
        return "The selected OpenAI model is unavailable to this API key."
    return "OpenAI is currently unavailable. I can still retrieve reporting rule context and keep the session context ready."


def _unique_models(models: list[str]) -> list[str]:
    seen = set()
    result = []
    for model in models:
        normalized = model.strip()
        if not normalized or normalized.lower() == "auto" or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result or DEFAULT_OPENAI_MODEL_CANDIDATES


def _is_terminal_error(message: str) -> bool:
    lower = message.lower()
    return (
        "needs quota" in lower
        or "billing credits" in lower
        or "could not authenticate" in lower
        or "rate limited" in lower
    )
