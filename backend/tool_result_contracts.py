"""Versioned result contracts checked before a tool result becomes durable."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class ResultModel(BaseModel):
    model_config = {"extra": "forbid"}


class Coverage(ResultModel):
    processed_pages: int = Field(ge=0)
    total_pages: int = Field(ge=1)

    @model_validator(mode="after")
    def complete(self):
        if self.processed_pages != self.total_pages:
            raise ValueError("Tool coverage is incomplete")
        return self


class SummaryCitation(ResultModel):
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1, max_length=500)


class SummaryMetrics(ResultModel):
    source_words: int = Field(ge=0)
    result_words: int = Field(ge=1)
    compression_percent: float = Field(ge=0, le=100)


class SummaryResult(ResultModel):
    schema_version: Literal["summary.v1"]
    text: str = Field(min_length=1)
    bullets: list[str]
    citations: list[SummaryCitation]
    metrics: SummaryMetrics
    coverage: Coverage

    @field_validator("bullets")
    @classmethod
    def clean_bullets(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Summary bullets cannot be blank")
        return values


class EntityItem(ResultModel):
    text: str = Field(min_length=1)
    normalized: str = Field(min_length=1)
    type: Literal["person", "organization", "location", "date", "other"]
    count: int = Field(ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    pages: list[int]

    @field_validator("pages")
    @classmethod
    def pages_are_valid(cls, values: list[int]) -> list[int]:
        if any(value < 1 for value in values) or len(values) != len(set(values)):
            raise ValueError("Entity page references are invalid")
        return values


class ResearchSection(ResultModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    page_refs: list[int] = Field(min_length=1)


class EntitiesResult(ResultModel):
    schema_version: Literal["entities.v1"]
    method: Literal["fast", "llm", "research_sections"]
    items: list[EntityItem]
    research_sections: list[ResearchSection]
    coverage: Coverage


class GlossaryItem(ResultModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class TranslationPage(ResultModel):
    number: int = Field(ge=1)
    text: str
    has_text: bool = True

    @model_validator(mode="after")
    def text_state_matches(self):
        if self.has_text != bool(self.text.strip()):
            raise ValueError("Translation page text state does not match")
        return self


class TranslationResult(ResultModel):
    schema_version: Literal["translation.v1"]
    source_language: str = Field(min_length=2, max_length=16)
    target_language: str = Field(min_length=2, max_length=16)
    pages: list[TranslationPage] = Field(min_length=1)
    text: str = Field(min_length=1)
    glossary: list[GlossaryItem]
    coverage: Coverage

    @model_validator(mode="after")
    def valid_pages(self):
        numbers = [page.number for page in self.pages]
        if len(set(numbers)) != len(numbers):
            raise ValueError("Translation pages must be unique")
        if len(self.pages) != self.coverage.total_pages:
            raise ValueError("Translation pages do not match coverage")
        if self.text != "\n\n".join(page.text for page in self.pages):
            raise ValueError("Translation full text does not match its pages")
        return self


class FrequentTerm(ResultModel):
    term: str = Field(min_length=1)
    count: int = Field(ge=1)
    page_refs: list[int] = Field(default_factory=list)


class Topic(ResultModel):
    name: str = Field(min_length=1)
    page_refs: list[int] = Field(min_length=1)
    coverage_percent: float = Field(ge=0, le=100)


class AnalysisMetrics(ResultModel):
    words: int = Field(ge=0)
    characters_without_spaces: int = Field(ge=0)
    sentences: int = Field(ge=0)
    average_word_length: float = Field(ge=0)


class AnalysisDocument(ResultModel):
    document_version_id: str = Field(min_length=1)
    metrics: AnalysisMetrics
    frequent_terms: list[FrequentTerm]
    topics: list[Topic]


class AnalysisResult(ResultModel):
    schema_version: Literal["analysis.v1"]
    documents: list[AnalysisDocument] = Field(min_length=1)
    comparison: dict[str, Any]

    @field_validator("documents")
    @classmethod
    def unique_documents(cls, values: list[AnalysisDocument]) -> list[AnalysisDocument]:
        ids = [value.document_version_id for value in values]
        if len(ids) != len(set(ids)):
            raise ValueError("Analysis documents must be unique")
        return values


class MindmapNode(ResultModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    parent_id: str | None = None
    page_refs: list[int] = Field(default_factory=list)


class MindmapEdge(ResultModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class MindmapResult(ResultModel):
    schema_version: Literal["mindmap.v1"]
    central_topic: str = Field(min_length=1)
    nodes: list[MindmapNode] = Field(min_length=1)
    edges: list[MindmapEdge]
    coverage: Coverage

    @model_validator(mode="after")
    def valid_graph(self):
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("Mindmap node IDs must be unique")
        relations = {(edge.source, edge.target) for edge in self.edges}
        relations.update((node.parent_id, node.id) for node in self.nodes if node.parent_id)
        if any(source not in ids or target not in ids or source == target for source, target in relations):
            raise ValueError("Mindmap edge is invalid")
        adjacency = {node_id: set() for node_id in ids}
        directed = {node_id: set() for node_id in ids}
        for source, target in relations:
            adjacency[source].add(target)
            adjacency[target].add(source)
            directed[source].add(target)
        visited: set[str] = set()
        pending = [next(iter(ids))]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(adjacency[current] - visited)
        if visited != ids:
            raise ValueError("Mindmap graph must be connected")
        visiting: set[str] = set()
        complete: set[str] = set()

        def walk(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("Mindmap graph cannot contain a cycle")
            if node_id in complete:
                return
            visiting.add(node_id)
            for child in directed[node_id]:
                walk(child)
            visiting.remove(node_id)
            complete.add(node_id)

        for node_id in ids:
            walk(node_id)
        return self


class WebSearchItem(ResultModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=8)
    snippet: str
    engine: str = Field(min_length=1)
    authors: list[Any]
    doi: str | None = None
    published_at: Any = None
    score: float
    rank_score: float

    @field_validator("url")
    @classmethod
    def http_url(cls, value: str) -> str:
        if urlparse(value).scheme not in {"http", "https"}:
            raise ValueError("Search result URL is invalid")
        return value


class WebSearchResult(ResultModel):
    schema_version: Literal["web-search.v1"]
    query: str = Field(min_length=1)
    category: Literal["academic", "general", "news", "wikipedia"]
    language: str = Field(min_length=2, max_length=16)
    results: list[WebSearchItem] = Field(min_length=1)
    suggestions: list[Any]
    engines_used: list[str] = Field(min_length=1)


class WebAnalysisSource(ResultModel):
    index: int = Field(ge=1)
    url: str = Field(min_length=8)


class WebAnalysisResult(ResultModel):
    schema_version: Literal["web-analysis.v1"]
    text: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)
    sources: list[WebAnalysisSource] = Field(min_length=1)


RESULT_MODELS: dict[str, type[ResultModel]] = {
    "summary.v1": SummaryResult,
    "entities.v1": EntitiesResult,
    "translation.v1": TranslationResult,
    "analysis.v1": AnalysisResult,
    "mindmap.v1": MindmapResult,
    "web-search.v1": WebSearchResult,
    "web-analysis.v1": WebAnalysisResult,
}


def validate_tool_result(value: dict[str, Any]) -> dict[str, Any]:
    schema_version = value.get("schema_version")
    model = RESULT_MODELS.get(schema_version)
    if model is None:
        raise ValueError("Unsupported tool result schema")
    return model.model_validate(value).model_dump(mode="json")
