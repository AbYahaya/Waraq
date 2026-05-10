"""Phase 2 closeout — §4.16.1 two-tier orchestrator tests."""

from __future__ import annotations

import pytest

from waraq.hadith import (
    EXTENDED_SOURCE_SPECS,
    HadithCandidateHit,
    Quellenrolle,
    TwoTierVerificationOutcome,
    get_extended_source,
    run_two_tier_verification,
)
from waraq.hadith.extended_sources import ExtendedSourceState


def _hit(
    *,
    source: str,
    matn: str,
    role: Quellenrolle = Quellenrolle.PFLICHT,
    collection: str = "",
    grade: str | None = None,
) -> HadithCandidateHit:
    return HadithCandidateHit(
        source_name=source,
        quellen_rolle=role,
        matn_arabic=matn,
        collection_label=collection,
        authenticity_grade=grade,
    )


# --- Extended source registry --------------------------------------


class TestExtendedRegistry:
    def test_e1_through_e4_documented_suspended(self) -> None:
        for source_id in (
            "e_1_islamweb",
            "e_2_jami_sunnah",
            "e_3_maktabat_waqfia",
            "e_4_jami_kutub_tisa",
        ):
            spec = get_extended_source(source_id)
            assert spec.state == ExtendedSourceState.SUSPENDED
            assert spec.quellen_rolle == Quellenrolle.ERWEITERT_SUSPENDIERT

    def test_e5_active_special_role(self) -> None:
        spec = get_extended_source("e_5_mawsuat_ahadith")
        assert spec.state == ExtendedSourceState.ACTIVE_SPECIAL_ROLE
        assert spec.quellen_rolle == Quellenrolle.ERWEITERT_SONDERROLLE

    def test_all_five_present(self) -> None:
        ids = {s.source_id for s in EXTENDED_SOURCE_SPECS}
        assert ids == {
            "e_1_islamweb",
            "e_2_jami_sunnah",
            "e_3_maktabat_waqfia",
            "e_4_jami_kutub_tisa",
            "e_5_mawsuat_ahadith",
        }

    def test_unknown_id_raises(self) -> None:
        with pytest.raises(KeyError, match="unknown extended source"):
            get_extended_source("e_99_made_up")


# --- Robust hit predicate / escalation -----------------------------


@pytest.mark.asyncio
class TestEscalation:
    async def test_robust_mandatory_no_escalation(self) -> None:
        """Two mandatory sources agreeing on the matn → robust hit
        (carriage_count >= 1, score above threshold) → NO escalation."""
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
            _hit(
                source="dorar.net",
                matn="إنما الأعمال بالنيات",
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
        ]
        result = await run_two_tier_verification(
            mandatory_hits=hits,
            query="إنما الأعمال",
        )
        assert result.extended_set_triggered is False
        assert result.extended_trigger_reason is None
        assert result.extended_hits == []

    async def test_no_mandatory_candidates_triggers_escalation(self) -> None:
        result = await run_two_tier_verification(
            mandatory_hits=[],
            query="some query",
        )
        assert result.extended_set_triggered is True
        assert result.extended_trigger_reason == "no_mandatory_candidates"

    async def test_single_mandatory_hit_no_carriage_triggers_escalation(self) -> None:
        """A lone hit has carriage_count=0 (no other source agrees) →
        not robust → escalate."""
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                collection="Sahih al-Bukhari",
                grade="Sahih",
            )
        ]
        result = await run_two_tier_verification(
            mandatory_hits=hits,
            query="إنما الأعمال",
            robust_hit_min_carriage=1,
        )
        assert result.extended_set_triggered is True
        assert result.extended_trigger_reason == "no_robust_hit"

    async def test_low_score_triggers_escalation(self) -> None:
        """All hits have minimal signal (no isnād, no grade, no
        collection) → composite score below threshold → escalate."""
        hits = [
            _hit(source="sunnah.com", matn="x"),
            _hit(source="dorar.net", matn="x"),
        ]
        result = await run_two_tier_verification(
            mandatory_hits=hits,
            query="x",
            robust_hit_score_threshold=0.9,  # raise threshold to force escalation
        )
        assert result.extended_set_triggered is True
        assert result.extended_trigger_reason == "no_robust_hit"

    async def test_manual_trigger_overrides_robust_hit(self) -> None:
        """§4.16.1 'can also be triggered manually by the user at any
        time' — manual flag escalates even on a robust mandatory hit."""
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
            _hit(
                source="dorar.net",
                matn="إنما الأعمال بالنيات",
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
        ]
        result = await run_two_tier_verification(
            mandatory_hits=hits,
            query="إنما الأعمال",
            manually_trigger_extended=True,
        )
        assert result.extended_set_triggered is True
        assert result.extended_trigger_reason == "manual"


# --- Extended fetcher invocation -----------------------------------


@pytest.mark.asyncio
class TestExtendedFetcherInvocation:
    async def test_extended_fetchers_called_only_on_escalation(self) -> None:
        """Default fetchers are no-ops; the test verifies they ARE
        invoked when escalation triggers and NOT when no escalation."""
        invoked: list[str] = []

        async def fake_e5(query: str) -> list[HadithCandidateHit]:
            invoked.append(f"e5:{query}")
            return []

        async def silent_suspended(query: str) -> list[HadithCandidateHit]:
            invoked.append(f"susp:{query}")
            return []

        fetchers = {
            "e_1_islamweb": silent_suspended,
            "e_2_jami_sunnah": silent_suspended,
            "e_3_maktabat_waqfia": silent_suspended,
            "e_4_jami_kutub_tisa": silent_suspended,
            "e_5_mawsuat_ahadith": fake_e5,
        }

        # No escalation case.
        invoked.clear()
        await run_two_tier_verification(
            mandatory_hits=[
                _hit(
                    source="sunnah.com",
                    matn="إنما الأعمال",
                    collection="Sahih al-Bukhari",
                    grade="Sahih",
                ),
                _hit(
                    source="dorar.net",
                    matn="إنما الأعمال",
                    collection="Sahih al-Bukhari",
                    grade="Sahih",
                ),
            ],
            query="إنما الأعمال",
            extended_fetchers=fetchers,
        )
        assert invoked == []

        # Escalation case.
        invoked.clear()
        await run_two_tier_verification(
            mandatory_hits=[],
            query="some query",
            extended_fetchers=fetchers,
        )
        # All 5 extended sources called.
        assert len(invoked) == 5

    async def test_e5_extended_hit_joins_consensus(self) -> None:
        """When E-5 returns a hit during escalation, that hit lands in
        the final consensus alongside any mandatory hits."""

        async def e5_returns_hit(query: str) -> list[HadithCandidateHit]:
            return [
                HadithCandidateHit(
                    source_name="e_5_mawsuat_ahadith",
                    quellen_rolle=Quellenrolle.ERWEITERT_SONDERROLLE,
                    matn_arabic="إنما الأعمال بالنيات",
                    collection_label="Mawsuat al-Ahadith",
                    authenticity_grade="Sahih",
                )
            ]

        async def silent(_query: str) -> list[HadithCandidateHit]:
            return []

        fetchers = {
            "e_1_islamweb": silent,
            "e_2_jami_sunnah": silent,
            "e_3_maktabat_waqfia": silent,
            "e_4_jami_kutub_tisa": silent,
            "e_5_mawsuat_ahadith": e5_returns_hit,
        }

        # Empty mandatory → escalation → E-5 contributes the only hit.
        result = await run_two_tier_verification(
            mandatory_hits=[],
            query="إنما الأعمال",
            extended_fetchers=fetchers,
        )
        assert result.extended_set_triggered is True
        assert len(result.extended_hits) == 1
        assert result.extended_hits[0].source_name == "e_5_mawsuat_ahadith"
        # Final consensus has the E-5 hit.
        assert result.consensus is not None
        assert result.consensus.reference_matn == "إنما الأعمال بالنيات"
        # E-5 source_id appears in invoked list (active source always invoked).
        assert "e_5_mawsuat_ahadith" in result.extended_sources_invoked

    async def test_no_hits_anywhere_returns_none_consensus(self) -> None:
        """Empty mandatory + no extended hits = no consensus (caller
        gets a graceful empty-result outcome rather than a crash)."""
        result = await run_two_tier_verification(
            mandatory_hits=[],
            query="missing query",
        )
        assert result.consensus is None
        assert result.extended_set_triggered is True


# --- Outcome shape -------------------------------------------------


@pytest.mark.asyncio
class TestOutcomeShape:
    async def test_outcome_carries_full_provenance(self) -> None:
        result = await run_two_tier_verification(
            mandatory_hits=[
                _hit(source="sunnah.com", matn="x", collection="Sahih al-Bukhari", grade="Sahih"),
                _hit(source="dorar.net", matn="x", collection="Sahih al-Bukhari", grade="Sahih"),
            ],
            query="x",
        )
        assert isinstance(result, TwoTierVerificationOutcome)
        assert result.consensus is not None
        assert len(result.mandatory_hits) == 2
        assert result.extended_hits == []
        assert result.extended_set_triggered is False
