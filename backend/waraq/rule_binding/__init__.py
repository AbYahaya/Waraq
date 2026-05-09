from waraq.rule_binding.service import (
    GlossaryMatch,
    RuleBindingApplied,
    RuleBindingConflict,
    RuleBindingResult,
    bind_glossary_to_segment,
    find_glossary_matches_in_segment,
    make_locked_segment_glossary_conflict_hook,
    make_translation_with_rule_binding_hook,
)

__all__ = [
    "GlossaryMatch",
    "RuleBindingApplied",
    "RuleBindingConflict",
    "RuleBindingResult",
    "bind_glossary_to_segment",
    "find_glossary_matches_in_segment",
    "make_locked_segment_glossary_conflict_hook",
    "make_translation_with_rule_binding_hook",
]
