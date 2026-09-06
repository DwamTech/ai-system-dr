import pytest

from backend.tooling.common import MAX_INPUT_CHARS, ToolContext, ToolFailure, extract_json, hierarchical_reduce, page_chunks


def test_page_chunks_are_bounded_and_keep_original_page_numbers():
    pages = [
        {"number": 1, "text": "alpha " * 20},
        {"number": 2, "text": ""},
        {"number": 3, "text": "beta " * 20},
    ]
    result = page_chunks(pages, maximum=40)
    assert result
    assert all(len(chunk.text) <= 45 for chunk in result)
    assert {page for chunk in result for page in chunk.page_refs} == {1, 3}


def test_json_parser_ignores_markdown_and_trailing_prose_without_greedy_merge():
    parsed = extract_json('```json\n{"items": [1]}\n``` trailing {broken}')
    assert parsed == {"items": [1]}


def test_hierarchical_reduce_keeps_complete_provider_prompt_within_limit():
    class Context:
        def __init__(self):
            self.prompts = []

        def invoke(self, prompt, _feature):
            self.prompts.append(prompt)
            return "جزء مدمج"

        def checkpoint(self, _stage, _item, compute):
            return compute()

    context = Context()
    assert hierarchical_reduce(context, ["أ" * MAX_INPUT_CHARS, "ب" * MAX_INPUT_CHARS], "ادمج", "reduce")
    assert context.prompts
    assert max(map(len, context.prompts)) <= MAX_INPUT_CHARS


def test_provider_failure_is_not_reported_as_an_internal_bug():
    class ProviderError(RuntimeError):
        status_code = 503

    context = ToolContext(None, None, None, lambda *_: True, lambda *_: (_ for _ in ()).throw(ProviderError()))
    with pytest.raises(ToolFailure) as failure:
        context.invoke("prompt", "summary")
    assert failure.value.code == "provider_unavailable"
