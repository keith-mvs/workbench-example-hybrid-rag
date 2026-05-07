# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Structured lesson generation endpoint for upstream callers (apexlon, Custom GPT).

Implements RCT-003 (POST /lesson) and RCT-004 (X-API-Key auth dependency).
This module is deliberately structured-JSON only — no streaming. Governance
(scoring, ledgering, rubric application) lives in apexlon, not here.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import openai
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from chain_server import chains


# ---------------------------------------------------------------------------
# RCT-004: API-key auth dependency
# ---------------------------------------------------------------------------

def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """FastAPI dependency that enforces X-API-Key when RCT_API_KEY is set.

    Dev-mode (RCT_API_KEY unset) skips auth entirely so local Workbench use
    keeps working. Mirrors apexlon's pattern (see apexlon/CLAUDE.md
    "Auth and public URL").
    """
    expected = os.environ.get("RCT_API_KEY")
    if not expected:
        return  # dev mode — no auth required
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


# ---------------------------------------------------------------------------
# RCT-003: Request / response models
# ---------------------------------------------------------------------------

class LessonRequest(BaseModel):
    """Request body for POST /lesson.

    Defaults are chosen so a minimal call only requires ``essential_question``.
    """

    essential_question: str
    grade_band: str = "8"
    duration_minutes: int = 45
    inference_mode: str = "cloud"  # "cloud" | "local" | "microservice"
    nvcf_model_id: str = "mistralai/mixtral-8x22b-instruct-v0.1"
    nim_model_ip: str = "localhost"
    nim_model_port: str = "8000"
    nim_model_id: str = ""  # empty -> chains._DEFAULT_NIM_MODEL
    temp: float = 0.3
    top_p: float = 0.85
    freq_pen: float = 0.3
    pres_pen: float = 0.0
    max_tokens: int = 1500


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_CORPUS_LABELS = {
    "loc": "Library of Congress (Coverage)",
    "nara": "National Archives (Testimony)",
    "si": "Smithsonian (Object)",
}


def _format_source_block(corpus_key: str, item: Dict[str, Any]) -> str:
    """Render one Evidence-Triad source as a labeled block for the prompt."""
    label = _CORPUS_LABELS.get(corpus_key, corpus_key.upper())
    meta = item.get("metadata") or {}
    title = meta.get("source_title") or meta.get("title") or "(untitled)"
    url = meta.get("source_url") or meta.get("url") or ""
    # Pull whichever stable id is available for this corpus.
    id_value = (
        meta.get("naid")
        or meta.get("edan_id")
        or meta.get("lccn")
        or meta.get("id")
        or ""
    )
    text = item.get("text") or ""
    score = item.get("score")
    score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "n/a"

    lines = [
        f"### Source: {label}",
        f"- title: {title}",
        f"- url: {url}",
        f"- id: {id_value}",
        f"- similarity_score: {score_str}",
        "",
        "Excerpt:",
        text,
    ]
    return "\n".join(lines)


def build_lesson_prompt(req: LessonRequest, triad: Dict[str, Dict[str, Any]]) -> str:
    """Assemble the lesson-generation prompt from request + retrieved triad."""
    if triad:
        source_blocks = "\n\n".join(
            _format_source_block(k, v) for k, v in triad.items()
        )
    else:
        source_blocks = "(no sources retrieved)"

    return (
        "You are a Revolutionary-War-era social studies curriculum designer. "
        "Read the three primary sources below and produce a single classroom "
        f"lesson plan for grade band {req.grade_band}, total duration "
        f"{req.duration_minutes} minutes.\n\n"
        f"Essential question: {req.essential_question}\n\n"
        "Sources (one per corpus — Coverage, Testimony, Object):\n\n"
        f"{source_blocks}\n\n"
        "Instructions:\n"
        "1. Use ALL three sources. Cite each by source title and URL when "
        "you reference it.\n"
        "2. Output a numbered list of activity steps. Each step must include "
        "an explicit duration in minutes. The step durations MUST sum to "
        f"{req.duration_minutes}.\n"
        "3. Include: a learning objective, a hook, source-analysis activity, "
        "discussion prompts tied to the essential question, and an exit "
        "ticket.\n"
        "4. Return Markdown only — no preface, no JSON, no code fences.\n"
    )


# ---------------------------------------------------------------------------
# LLM dispatch
# ---------------------------------------------------------------------------

def _dispatch_cloud(req: LessonRequest, prompt: str) -> Tuple[str, str]:
    """Call NVIDIA API Catalog (cloud), non-streaming. Returns (text, model_id)."""
    openai.api_key = os.environ.get("NVIDIA_API_KEY")
    openai.base_url = "https://integrate.api.nvidia.com/v1/"
    model_id = req.nvcf_model_id
    completion = openai.chat.completions.create(
        model=model_id,
        temperature=req.temp,
        top_p=req.top_p,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=req.max_tokens,
        stream=False,
    )
    content = completion.choices[0].message.content or ""
    return content, model_id


def _dispatch_microservice(req: LessonRequest, prompt: str) -> Tuple[str, str]:
    """Call a local NIM microservice OpenAI-compatible endpoint, non-streaming."""
    openai.api_key = "xyz"
    openai.base_url = (
        f"http://{req.nim_model_ip}:{req.nim_model_port or '8000'}/v1/"
    )
    model_id = req.nim_model_id or chains._DEFAULT_NIM_MODEL
    completion = openai.chat.completions.create(
        model=model_id,
        temperature=req.temp,
        top_p=req.top_p,
        frequency_penalty=req.freq_pen,
        presence_penalty=req.pres_pen,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=req.max_tokens,
        stream=False,
    )
    content = completion.choices[0].message.content or ""
    return content, model_id


def generate_lesson(
    req: LessonRequest, triad: Dict[str, Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Build the prompt and dispatch to the configured inference backend.

    Returns ``(lesson_markdown, model_meta)`` where ``model_meta`` echoes the
    sampler/model fields actually used for the call.
    """
    prompt = build_lesson_prompt(req, triad)

    if req.inference_mode == "cloud":
        content, model_id = _dispatch_cloud(req, prompt)
    elif req.inference_mode == "microservice":
        content, model_id = _dispatch_microservice(req, prompt)
    elif req.inference_mode == "local":
        # Local TGI mode is not wired into /lesson v1. Cloud + microservice
        # are the supported upstream paths (see RCT-003).
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="inference_mode='local' is not implemented in /lesson v1",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown inference_mode: {req.inference_mode!r}",
        )

    model_meta: Dict[str, Any] = {
        "inference_mode": req.inference_mode,
        "model_id": model_id,
        "temp": req.temp,
        "top_p": req.top_p,
        "freq_pen": req.freq_pen,
        "pres_pen": req.pres_pen,
        "max_tokens": req.max_tokens,
    }
    return content, model_meta


# ---------------------------------------------------------------------------
# Top-level handler used by server.py
# ---------------------------------------------------------------------------

def handle_lesson(req: LessonRequest) -> Dict[str, Any]:
    """Run retrieval + generation and return the structured /lesson payload."""
    request_id = str(uuid.uuid4())
    started = time.perf_counter()

    triad = chains.retrieve_evidence_triad(req.essential_question, top_k=24)
    lesson_markdown, model_meta = generate_lesson(req, triad)

    generation_ms = (time.perf_counter() - started) * 1000.0

    return {
        "request_id": request_id,
        "essential_question": req.essential_question,
        "grade_band": req.grade_band,
        "duration_minutes": req.duration_minutes,
        "triad": {
            "loc": triad.get("loc"),
            "nara": triad.get("nara"),
            "si": triad.get("si"),
        },
        "lesson_markdown": lesson_markdown,
        "model": model_meta,
        "retrieval": {
            "top_k": 24,
            "corpora_returned": sorted(triad.keys()),
        },
        "generation_ms": round(generation_ms, 1),
    }
