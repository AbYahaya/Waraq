"""Phase 4 sub-batch D — Stage-3 AI consensus harness."""

from __future__ import annotations

import pytest

from waraq.ocr.stage3_ai import (
    NEUTRAL_SCORE,
    AiEngineVerdict,
    Stage3AiResult,
    run_ai_consensus,
)


def _verdict(*, engine: str, confidence: float, note: str | None = None) -> AiEngineVerdict:
    return AiEngineVerdict(
        engine=engine,
        confidence=confidence,
        correction_note=note,
    )


def _stub_validator(verdict: AiEngineVerdict):
    async def _fn(_text: str, _ctx: dict[str, str]) -> AiEngineVerdict:
        return verdict

    return _fn


def _raising_validator(exc: Exception):
    async def _fn(_text: str, _ctx: dict[str, str]) -> AiEngineVerdict:
        raise exc

    return _fn


@pytest.mark.asyncio
class TestRunAiConsensusEdgeCases:
    async def test_empty_text_short_circuits_to_no_engine(self) -> None:
        result = await run_ai_consensus(candidate_text="   ")
        assert isinstance(result, Stage3AiResult)
        assert result.agreement == "no_engine"
        assert result.score == NEUTRAL_SCORE
        assert result.verdicts == ()

    async def test_default_validators_return_neutral(self) -> None:
        result = await run_ai_consensus(candidate_text="بسم الله")
        # Both default stubs are neutral 0.5 → agreement.
        assert result.agreement == "agree"
        assert result.score == NEUTRAL_SCORE


@pytest.mark.asyncio
class TestAgreementClassification:
    async def test_agree_when_within_delta(self) -> None:
        result = await run_ai_consensus(
            candidate_text="بسم الله",
            openai_validator=_stub_validator(_verdict(engine="gpt-4o", confidence=0.90)),
            gemini_validator=_stub_validator(_verdict(engine="gemini", confidence=0.85)),
        )
        # Delta 0.05 ≤ 0.20 tolerance.
        assert result.agreement == "agree"
        assert abs(result.score - 0.875) < 1e-9

    async def test_disagree_when_outside_delta_collapses(self) -> None:
        result = await run_ai_consensus(
            candidate_text="بسم الله",
            openai_validator=_stub_validator(_verdict(engine="gpt-4o", confidence=0.95)),
            gemini_validator=_stub_validator(_verdict(engine="gemini", confidence=0.40)),
        )
        # Delta 0.55 > 0.20 → disagree → mean × 0.7.
        assert result.agreement == "disagree"
        mean = (0.95 + 0.40) / 2
        assert abs(result.score - mean * 0.7) < 1e-9

    async def test_single_engine_when_other_errors(self) -> None:
        result = await run_ai_consensus(
            candidate_text="بسم الله",
            openai_validator=_stub_validator(_verdict(engine="gpt-4o", confidence=0.80)),
            gemini_validator=_raising_validator(RuntimeError("rate-limited")),
        )
        assert result.agreement == "single_engine"
        # Surviving engine's confidence carries through.
        assert result.score == pytest.approx(0.80)
        # The error survivor still has both verdict slots — one with
        # error_class set.
        assert len(result.verdicts) == 2
        errors = [v for v in result.verdicts if v.error_class is not None]
        assert len(errors) == 1
        assert errors[0].error_class == "RuntimeError"

    async def test_no_engine_when_both_error(self) -> None:
        result = await run_ai_consensus(
            candidate_text="بسم الله",
            openai_validator=_raising_validator(RuntimeError("a")),
            gemini_validator=_raising_validator(RuntimeError("b")),
        )
        assert result.agreement == "no_engine"
        assert result.score == NEUTRAL_SCORE
        assert all(v.error_class is not None for v in result.verdicts)


@pytest.mark.asyncio
class TestVerdictFields:
    async def test_correction_note_passes_through(self) -> None:
        result = await run_ai_consensus(
            candidate_text="بسم الله",
            openai_validator=_stub_validator(
                _verdict(engine="gpt-4o", confidence=0.85, note="diacritic mismatch on word 2")
            ),
            gemini_validator=_stub_validator(_verdict(engine="gemini", confidence=0.85)),
        )
        notes = [v.correction_note for v in result.verdicts]
        assert "diacritic mismatch on word 2" in notes

    async def test_context_dict_forwarded(self) -> None:
        captured: list[dict[str, str]] = []

        async def _capturing(text: str, ctx: dict[str, str]) -> AiEngineVerdict:
            captured.append(ctx.copy())
            _ = text
            return _verdict(engine="capture", confidence=0.7)

        await run_ai_consensus(
            candidate_text="بسم",
            context={"block_class": "main_text", "neighbour": "x"},
            openai_validator=_capturing,
            gemini_validator=_capturing,
        )
        assert all(ctx == {"block_class": "main_text", "neighbour": "x"} for ctx in captured)
