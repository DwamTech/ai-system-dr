"""Strict API contracts for durable document-tool jobs."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


TOOL_TYPES = {"summary", "entities", "translation", "analysis", "mindmap", "web_search", "web_analysis"}
ENTITY_TYPES = {"person", "organization", "location", "date", "other"}


class StrictModel(BaseModel):
    model_config = {"extra": "forbid"}


class SummaryOptions(StrictModel):
    summary_type: Literal["executive", "analytical", "quick"] = "executive"
    length: Literal["short", "medium", "detailed"] = "medium"
    include_bullets: bool = True


class EntityOptions(StrictModel):
    method: Literal["fast", "llm", "research_sections"] = "fast"
    entity_types: list[Literal["person", "organization", "location", "date", "other"]] = Field(default_factory=list)

    @field_validator("entity_types")
    @classmethod
    def unique_types(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Entity types must be unique")
        return value


class TranslationOptions(StrictModel):
    target_language: Literal["ar", "en", "fr", "de", "es", "tr"] = "en"
    style: Literal["academic", "literal", "simple"] = "academic"
    keep_formatting: bool = True
    scope: Literal["page", "range", "full"] = "full"
    page: int | None = Field(default=None, ge=1)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "page" and self.page is None:
            raise ValueError("A positive page number is required for page scope")
        if self.scope == "range":
            if self.start_page is None or self.end_page is None:
                raise ValueError("Both range boundaries are required")
            if self.start_page > self.end_page:
                raise ValueError("The range start must not exceed its end")
        if self.scope == "full" and any(value is not None for value in (self.page, self.start_page, self.end_page)):
            raise ValueError("Page options are not allowed for full scope")
        return self


class AnalysisOptions(StrictModel):
    include_topics: bool = True
    compare: bool = False


class MindmapOptions(StrictModel):
    target_nodes: int = Field(default=15, ge=5, le=30)


class WebSearchOptions(StrictModel):
    category: Literal["academic", "general", "news", "wikipedia"] = "academic"
    language: Literal["auto", "ar", "en"] = "auto"
    max_results: int = Field(default=10, ge=1, le=20)


class WebAnalysisOptions(StrictModel):
    language: Literal["ar", "en"] = "ar"


OPTION_MODELS: dict[str, type[StrictModel]] = {
    "summary": SummaryOptions,
    "entities": EntityOptions,
    "translation": TranslationOptions,
    "analysis": AnalysisOptions,
    "mindmap": MindmapOptions,
    "web_search": WebSearchOptions,
    "web_analysis": WebAnalysisOptions,
}


class ToolJobRequest(StrictModel):
    tool_type: Literal["summary", "entities", "translation", "analysis", "mindmap", "web_search", "web_analysis"]
    request_id: str = Field(min_length=8, max_length=64)
    document_version_id: str | None = None
    document_version_ids: list[str] = Field(default_factory=list, max_length=5)
    source_job_id: str | None = None
    input_text: str | None = Field(default=None, max_length=120000)
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("document_version_id", "source_job_id")
    @classmethod
    def valid_uuid(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                return str(UUID(value))
            except (ValueError, AttributeError) as exc:
                raise ValueError("Expected a UUID") from exc
        return value

    @field_validator("document_version_ids")
    @classmethod
    def valid_unique_version_ids(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            try:
                normalized.append(str(UUID(value)))
            except (ValueError, AttributeError) as exc:
                raise ValueError("Expected document version UUIDs") from exc
        if len(normalized) != len(set(normalized)):
            raise ValueError("Document versions must be unique")
        return normalized

    @field_validator("input_text")
    @classmethod
    def clean_input(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Input text cannot be empty")
        return value.strip() if value else None

    @model_validator(mode="after")
    def sources_match_tool(self):
        has_one_document = bool(self.document_version_id)
        has_many_documents = bool(self.document_version_ids)
        has_text = bool(self.input_text)
        has_source_job = bool(self.source_job_id)
        if self.tool_type in {"summary", "entities"}:
            if not has_one_document or has_many_documents or has_text or has_source_job:
                raise ValueError("This tool requires exactly one document version")
        elif self.tool_type == "analysis":
            if not has_many_documents or has_one_document or has_text or has_source_job:
                raise ValueError("Analysis requires one to five document versions")
        elif self.tool_type in {"translation", "mindmap"}:
            if has_many_documents or has_source_job or has_one_document == has_text:
                raise ValueError("Choose exactly one document or direct text source")
        elif self.tool_type == "web_search":
            if not has_text or has_one_document or has_many_documents or has_source_job:
                raise ValueError("Web search requires a query only")
        elif self.tool_type == "web_analysis":
            if not has_source_job or has_one_document or has_many_documents or has_text:
                raise ValueError("Web analysis requires a completed search job only")
        return self


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validated_options(request: ToolJobRequest) -> dict[str, Any]:
    model = OPTION_MODELS[request.tool_type].model_validate(request.options)
    options = model.model_dump(exclude_none=True)
    if request.tool_type == "analysis" and options["compare"] and len(request.document_version_ids) < 2:
        raise ValueError("Comparison needs at least two distinct documents")
    return options
