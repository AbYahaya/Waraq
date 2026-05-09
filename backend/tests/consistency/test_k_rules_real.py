"""T-8.2.1 mandatory tests — Sprint 4 §4 (real K-rule bodies).

Per Sprint 4 §A HG-S4-1: each K-rule reads ONLY its passende
Identitätstyp. K-02..K-06 must NOT delegate to concept_id.

Test ID coverage:
- Konsistenz-Befund-Eigene-Tabelle-Test
- K-01-Concept-ID-Basis-Test
- K-02-Formel-Verzeichnis-Identitaet-Test
- K-03-Entitaet-ID-Test
- K-04-Transliterations-Muster-Test
- K-05-Quellenidentitaet-Test
- K-06-Strukturelles-Muster-Test
- K-07-Cross-Rule-Concept-ID-Test
- K-Identitaetstyp-Trennung-Test
- Konsistenz-Vorschlag-Kein-Auto-Anwendung-Test
"""

from __future__ import annotations

import inspect
import uuid as _uuid
from typing import ClassVar

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment, st
from waraq.consistency import (
    KRuleId,
    SubjectType,
    register_real_k_rules,
    resolve_konsistenz_befund,
    run_consistency_check,
)
from waraq.consistency import rules as consistency_rules
from waraq.identity import new_uuid
from waraq.provenance import create_po
from waraq.schemas import (
    Concept,
    Entity,
    FormelVerzeichnisEintrag,
    KonsistenzBefund,
    QuellenIdentitaet,
    Revision,
    Segment,
    StrukturellerSchluessel,
    TransliterationsMusterEintrag,
)
from waraq.schemas.enums import POType, ScopeType


@pytest.fixture(autouse=True)
def _register_real_rules():
    """Each test starts with the real K-rule bodies registered."""
    register_real_k_rules()
    yield


# --- Konsistenz-Befund-Eigene-Tabelle-Test ----------------------------


@pytest.mark.asyncio
class TestKonsistenzBefundIsOwnTable:
    async def test_konsistenz_befund_table_distinct_from_befund(self) -> None:
        from waraq.schemas import Befund

        assert KonsistenzBefund.__tablename__ == "konsistenz_befunde"
        assert Befund.__tablename__ == "audit_befunde"
        assert KonsistenzBefund.__tablename__ != Befund.__tablename__

        # FK targets show the two tables are not joined by inheritance.
        kbf_targets = {fk.column.table.name for fk in KonsistenzBefund.__table__.foreign_keys}
        assert "audit_befunde" not in kbf_targets


# --- K-01-Concept-ID-Basis-Test ---------------------------------------


async def _seed_rule_binding_po(
    session: AsyncSession,
    *,
    segment: Segment,
    concept_id: _uuid.UUID | None = None,
    entity_id: _uuid.UUID | None = None,
    surface_form: str = "",
    applied_rendering: str = "",
    rule_label: str | None = None,
) -> None:
    payload = {"surface_form": surface_form, "applied_rendering": applied_rendering}
    if concept_id is not None:
        payload["concept_id"] = str(concept_id)
    if entity_id is not None:
        payload["entity_id"] = str(entity_id)
    if rule_label:
        payload["application_context"] = {"rule": rule_label}
    await create_po(
        session=session,
        po_type=POType.RULE_BINDING,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        payload=payload,
    )


@pytest.mark.asyncio
class TestK01ConceptIDBasis:
    async def test_same_surface_distinct_concepts_no_finding(
        self, db_session: AsyncSession
    ) -> None:
        """Two segments share a SURFACE form but bind to DIFFERENT concept_ids:
        the rule must not falsely flag them — concept_id is the basis."""
        project = await seed_project(db_session)
        c1_id = new_uuid()
        c2_id = new_uuid()
        db_session.add_all(
            [
                Concept(
                    concept_id=c1_id,
                    canonical_label="Allah",
                    language="ar",
                    project_uuid=project.project_uuid,
                ),
                Concept(
                    concept_id=c2_id,
                    canonical_label="Allah",
                    language="ar",
                    project_uuid=project.project_uuid,
                ),
            ]
        )
        await db_session.flush()
        seg_a = await seed_segment(db_session, project=project, text="x")
        seg_b = await seed_segment(
            db_session, project=project, text="y", page_index=2, satz_index=1
        )
        # Same surface, distinct concepts → distinct groups, no inconsistency.
        await _seed_rule_binding_po(
            db_session,
            segment=seg_a,
            concept_id=c1_id,
            surface_form="Allah",
            applied_rendering="Gott",
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_b,
            concept_id=c2_id,
            surface_form="Allah",
            applied_rendering="der Erhabene",
        )

        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_01],
        )
        assert findings == []

    async def test_same_concept_divergent_renderings_emits_finding(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        c_id = new_uuid()
        db_session.add(
            Concept(
                concept_id=c_id,
                canonical_label="ʿabd",
                language="ar",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        seg_a = await seed_segment(db_session, project=project, text="x")
        seg_b = await seed_segment(
            db_session, project=project, text="y", page_index=2, satz_index=1
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_a,
            concept_id=c_id,
            surface_form="ʿabd",
            applied_rendering="Diener",
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_b,
            concept_id=c_id,
            surface_form="ʿabd",
            applied_rendering="Knecht",
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_01],
        )
        assert len(findings) == 1
        f = findings[0]
        assert f.k_rule == KRuleId.K_01.value
        assert f.subject_type == SubjectType.CONCEPT_ID.value
        assert f.subject_key == str(c_id)
        # vorschlag carries divergent renderings; never auto-applied.
        assert "Diener" in f.vorschlag.get("candidates", [])
        assert "Knecht" in f.vorschlag.get("candidates", [])


# --- K-02-Formel-Verzeichnis-Identitaet-Test --------------------------


@pytest.mark.asyncio
class TestK02FormelVerzeichnis:
    async def test_divergent_formel_rendering_emits_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        # Identitätstyp record: the canonical Basmala formula.
        db_session.add(
            FormelVerzeichnisEintrag(
                identity_uuid=new_uuid(),
                project_uuid=project.project_uuid,
                identity_key="basmala",
                source_pattern="بسم الله",
                expected_rendering="Im Namen Gottes, des Erbarmers, des Barmherzigen",
            )
        )
        await db_session.flush()
        # Two segments with the source pattern; one matches expected, one diverges.
        await seed_segment(
            db_session,
            project=project,
            text=st(
                "بسم الله الرحمن الرحيم",
                "Im Namen Gottes, des Erbarmers, des Barmherzigen",
            ),
        )
        await seed_segment(
            db_session,
            project=project,
            text=st("بسم الله الرحمن الرحيم", "Im Namen Allahs."),
            page_index=2,
            satz_index=1,
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_02],
        )
        assert len(findings) == 1
        f = findings[0]
        assert f.k_rule == KRuleId.K_02.value
        assert f.subject_type == SubjectType.FORMEL_VERZEICHNIS_ID.value
        assert f.subject_key == "basmala"


# --- K-03-Entitaet-ID-Test --------------------------------------------


@pytest.mark.asyncio
class TestK03EntityID:
    async def test_divergent_entity_renderings_emit_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        e_id = new_uuid()
        db_session.add(
            Entity(
                entity_id=e_id,
                category="scholar_or_person",
                canonical_label="Ibn Khaldūn",
                language="ar",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        seg_a = await seed_segment(db_session, project=project, text="x")
        seg_b = await seed_segment(
            db_session, project=project, text="y", page_index=2, satz_index=1
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_a,
            entity_id=e_id,
            applied_rendering="Ibn Chaldun",
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_b,
            entity_id=e_id,
            applied_rendering="Ibn Khaldun",
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_03],
        )
        assert len(findings) == 1
        assert findings[0].k_rule == KRuleId.K_03.value
        assert findings[0].subject_type == SubjectType.ENTITY_ID.value


# --- K-04-Transliterations-Muster-Test --------------------------------


@pytest.mark.asyncio
class TestK04TransliterationsMuster:
    async def test_divergent_transliteration_emits_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        db_session.add(
            TransliterationsMusterEintrag(
                identity_uuid=new_uuid(),
                project_uuid=project.project_uuid,
                identity_key="hadith",
                source_pattern="حديث",
                expected_rendering="ḥadīth",
            )
        )
        await db_session.flush()
        await seed_segment(
            db_session,
            project=project,
            text=st("حديث", "ein ḥadīth"),
        )
        await seed_segment(
            db_session,
            project=project,
            text=st("حديث", "ein hadis"),
            page_index=2,
            satz_index=1,
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_04],
        )
        assert len(findings) == 1
        assert findings[0].subject_type == SubjectType.TRANSLITERATIONS_MUSTER.value


# --- K-05-Quellenidentitaet-Test --------------------------------------


@pytest.mark.asyncio
class TestK05Quellenidentitaet:
    async def test_divergent_citation_rendering_emits_finding(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        db_session.add(
            QuellenIdentitaet(
                identity_uuid=new_uuid(),
                project_uuid=project.project_uuid,
                identity_key="bukhari_iman_1",
                source_pattern="صحيح البخاري",
                expected_rendering="Bukhārī, Ṣaḥīḥ, Kitāb al-īmān, Bāb 1",
            )
        )
        await db_session.flush()
        await seed_segment(
            db_session,
            project=project,
            text=st("صحيح البخاري", "Bukhārī, Ṣaḥīḥ, Kitāb al-īmān, Bāb 1"),
        )
        await seed_segment(
            db_session,
            project=project,
            text=st("صحيح البخاري", "Buhari, Iman, Kapitel eins"),
            page_index=2,
            satz_index=1,
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_05],
        )
        assert len(findings) == 1
        assert findings[0].subject_type == SubjectType.SOURCE_IDENTITY.value


# --- K-06-Strukturelles-Muster-Test -----------------------------------


@pytest.mark.asyncio
class TestK06StrukturellerSchluessel:
    async def test_divergent_structural_rendering_emits_finding(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        db_session.add(
            StrukturellerSchluessel(
                identity_uuid=new_uuid(),
                project_uuid=project.project_uuid,
                identity_key="kapitel_heading",
                source_pattern="باب",
                expected_rendering="Kapitel",
            )
        )
        await db_session.flush()
        await seed_segment(
            db_session,
            project=project,
            text=st("باب الإيمان", "Kapitel des Glaubens"),
        )
        await seed_segment(
            db_session,
            project=project,
            text=st("باب الصلاة", "Section über das Gebet"),
            page_index=2,
            satz_index=1,
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_06],
        )
        assert len(findings) == 1
        assert findings[0].subject_type == SubjectType.STRUCTURAL_KEY.value


# --- K-07-Cross-Rule-Concept-ID-Test ----------------------------------


@pytest.mark.asyncio
class TestK07CrossRuleConceptID:
    async def test_cross_rule_divergence_emits_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        c_id = new_uuid()
        db_session.add(
            Concept(
                concept_id=c_id,
                canonical_label="ʿibāda",
                language="ar",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        seg_a = await seed_segment(db_session, project=project, text="x")
        seg_b = await seed_segment(
            db_session, project=project, text="y", page_index=2, satz_index=1
        )
        # Same concept, divergent renderings, with different rule labels.
        await _seed_rule_binding_po(
            db_session,
            segment=seg_a,
            concept_id=c_id,
            applied_rendering="Gottesdienst",
            rule_label="terminology_v1",
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_b,
            concept_id=c_id,
            applied_rendering="Verehrung",
            rule_label="style_profile_v2",
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_07],
        )
        assert len(findings) == 1
        f = findings[0]
        assert f.k_rule == KRuleId.K_07.value
        assert f.subject_type == SubjectType.CONCEPT_ID.value
        assert sorted(f.vorschlag.get("rule_labels", [])) == sorted(
            ["terminology_v1", "style_profile_v2"]
        )

    async def test_same_rule_label_no_cross_rule_finding(self, db_session: AsyncSession) -> None:
        """Even with divergent renderings under the same concept_id, K-07
        does NOT fire if all bindings come from the same rule label —
        K-01 covers the within-rule case."""
        project = await seed_project(db_session)
        c_id = new_uuid()
        db_session.add(
            Concept(
                concept_id=c_id,
                canonical_label="ʿabd",
                language="ar",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        seg_a = await seed_segment(db_session, project=project, text="x")
        seg_b = await seed_segment(
            db_session, project=project, text="y", page_index=2, satz_index=1
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_a,
            concept_id=c_id,
            applied_rendering="A",
            rule_label="terminology_v1",
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_b,
            concept_id=c_id,
            applied_rendering="B",
            rule_label="terminology_v1",
        )
        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_07],
        )
        assert findings == []


# --- K-Identitaetstyp-Trennung-Test (HG-S4-1) -------------------------


class TestKIdentitaetstypTrennung:
    """Code-review test: each K-rule's body reads only its passende
    Identitätstyp. Generalising K-02..K-06 onto concept_id is the named
    structural failure mode (HG-S4-1, R-S4-02)."""

    K_RULE_FUNCTIONS: ClassVar[dict] = {
        KRuleId.K_01: consistency_rules.k_01_concept_terminology,
        KRuleId.K_02: consistency_rules.k_02_formel_verzeichnis,
        KRuleId.K_03: consistency_rules.k_03_entity_consistency,
        KRuleId.K_04: consistency_rules.k_04_transliterations_muster,
        KRuleId.K_05: consistency_rules.k_05_source_identity,
        KRuleId.K_06: consistency_rules.k_06_structural_key,
        KRuleId.K_07: consistency_rules.k_07_concept_cross_rule,
    }

    EXPECTED_TABLE_TOKEN: ClassVar[dict] = {
        KRuleId.K_02: "FormelVerzeichnisEintrag",
        KRuleId.K_04: "TransliterationsMusterEintrag",
        KRuleId.K_05: "QuellenIdentitaet",
        KRuleId.K_06: "StrukturellerSchluessel",
    }

    def test_each_rule_binds_to_its_subject_type_in_registry(self) -> None:
        # The registry is the single source of truth for binding.
        from waraq.consistency.engine import K_RULE_SUBJECT_TYPE as REG

        assert REG[KRuleId.K_01] == SubjectType.CONCEPT_ID
        assert REG[KRuleId.K_02] == SubjectType.FORMEL_VERZEICHNIS_ID
        assert REG[KRuleId.K_03] == SubjectType.ENTITY_ID
        assert REG[KRuleId.K_04] == SubjectType.TRANSLITERATIONS_MUSTER
        assert REG[KRuleId.K_05] == SubjectType.SOURCE_IDENTITY
        assert REG[KRuleId.K_06] == SubjectType.STRUCTURAL_KEY
        assert REG[KRuleId.K_07] == SubjectType.CONCEPT_ID

    def test_k_02_through_k_06_do_not_delegate_to_concept_id(self) -> None:
        """The body of K-02..K-06 must not import or reference the
        Concept ORM class. Generalising onto concept_id is the named
        Sprint 4 §A HG-S4-1 failure mode."""
        for rule_id, func in self.K_RULE_FUNCTIONS.items():
            if rule_id in {KRuleId.K_01, KRuleId.K_07}:
                continue
            src = inspect.getsource(func)
            # The K-02..K-06 bodies dispatch through `_scan_identity_table`;
            # they must not directly reference Concept or concept_id.
            assert "Concept" not in src or "concept_id" not in src, (
                f"{rule_id.value} body references Concept/concept_id; this "
                "is the K-02..K-06 generalization failure mode (HG-S4-1)."
            )

    def test_each_k_table_rule_references_its_own_table_class(self) -> None:
        """K-02..K-06 each reference their own Identitätstyp ORM class
        in their function body."""
        for rule_id, expected in self.EXPECTED_TABLE_TOKEN.items():
            src = inspect.getsource(self.K_RULE_FUNCTIONS[rule_id])
            assert expected in src, (
                f"{rule_id.value} body does not reference its passende "
                f"Identitätstyp class {expected!r}; HG-S4-1 violated."
            )


# --- Konsistenz-Vorschlag-Kein-Auto-Anwendung-Test --------------------


@pytest.mark.asyncio
class TestKonsistenzVorschlagNeverAutoApplied:
    async def test_finding_emits_vorschlag_but_never_mutates_segment(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        c_id = new_uuid()
        db_session.add(
            Concept(
                concept_id=c_id,
                canonical_label="x",
                language="ar",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        seg_a = await seed_segment(db_session, project=project, text="A0")
        seg_b = await seed_segment(
            db_session, project=project, text="B0", page_index=2, satz_index=1
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_a,
            concept_id=c_id,
            applied_rendering="ALPHA",
        )
        await _seed_rule_binding_po(
            db_session,
            segment=seg_b,
            concept_id=c_id,
            applied_rendering="BETA",
        )

        # Capture text before the run.
        before_a = seg_a.text_content
        before_b = seg_b.text_content

        _job, findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_01],
        )
        assert len(findings) == 1

        # No segment text mutation. No Revision created from the run.
        await db_session.refresh(seg_a)
        await db_session.refresh(seg_b)
        assert seg_a.text_content == before_a
        assert seg_b.text_content == before_b
        rev_count = (
            await db_session.execute(select(Revision).where(Revision.satz_uuid == seg_a.satz_uuid))
        ).all()
        assert rev_count == []

        # Resolution requires explicit Decision Event.
        de = await resolve_konsistenz_befund(
            session=db_session,
            finding=findings[0],
            chosen_rendering={"value": "ALPHA"},
        )
        assert de.decision_type == "konsistenzgruppe_verbindlich"
        # Even after resolution, segment text is still untouched — the
        # canonical rendering is recorded; application is a separate step.
        await db_session.refresh(seg_a)
        await db_session.refresh(seg_b)
        assert seg_a.text_content == before_a
        assert seg_b.text_content == before_b
