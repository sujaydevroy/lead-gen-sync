"""ClaudeExtractor against a fake SDK client (no network, no API key)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from crawler.ai.claude import ClaudeExtractor, _chunks
from crawler.ai.extractor import BudgetExhausted, DealerList, ExtractedDealer


class FakeMessages:
    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []

    def parse(self, **kwargs):
        self.requests.append(kwargs)
        stop_reason, parsed = self.answers.pop(0)
        return SimpleNamespace(
            stop_reason=stop_reason, parsed_output=parsed, usage=SimpleNamespace(input_tokens=1000, output_tokens=200)
        )


def extractor(settings, answers):
    messages = FakeMessages(answers)
    return ClaudeExtractor(settings, client=SimpleNamespace(messages=messages)), messages


def test_structured_request_and_usage(settings):
    answer = DealerList(is_business_list=True, dealers=[ExtractedDealer(dealer_name="Rao Tobacco Traders")])
    ai, messages = extractor(settings, [("end_turn", answer)])
    result = ai.extract_dealers("Rao Tobacco Traders, Guntur", url="https://x.example", hint="members")
    assert [d.dealer_name for d in result.dealers] == ["Rao Tobacco Traders"]
    request = messages.requests[0]
    assert request["model"] == "claude-haiku-5-5" and request["output_format"] is DealerList
    assert request["output_config"] == {"effort": "low"} and "untrusted" in request["system"]
    assert ai.usage == {"calls": 1, "input_tokens": 1000, "output_tokens": 200}


def test_cut_off_answer_is_retried_on_the_retry_model(settings):
    answer = DealerList(is_business_list=True, dealers=[])
    ai, messages = extractor(settings, [("max_tokens", None), ("end_turn", answer)])
    ai.extract_dealers("text", url="https://x.example", hint="")
    assert [r["model"] for r in messages.requests] == ["claude-haiku-5-5", "claude-sonnet-5-5"]


def test_declined_page_is_not_retried(settings):
    ai, messages = extractor(settings, [("refusal", None)])
    result = ai.extract_dealers("text", url="https://x.example", hint="")
    assert result.dealers == [] and len(messages.requests) == 1 and "declined" in ai.failures[0]


def test_call_budget(settings):
    settings.llm_max_calls = 1
    ai, _ = extractor(settings, [("end_turn", DealerList(is_business_list=False))])
    ai.extract_dealers("a", url="https://x.example", hint="")
    with pytest.raises(BudgetExhausted):
        ai.extract_dealers("b", url="https://x.example", hint="")


def test_long_pages_are_split_at_line_breaks():
    text = "\n".join(f"line {i} " + "x" * 90 for i in range(1000))
    chunks = _chunks(text, size=10_000)
    assert len(chunks) > 5 and all(len(c) <= 10_000 for c in chunks) and "\n".join(chunks) == text
