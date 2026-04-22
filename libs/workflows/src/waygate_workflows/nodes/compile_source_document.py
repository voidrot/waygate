from __future__ import annotations

from waygate_core import get_app_context

from waygate_workflows.agents.source_analysis import analyze_source_document
from waygate_workflows.schema import ClaimLedgerEntry
from waygate_workflows.schema import ContinuityMentionModel
from waygate_workflows.schema import DocumentAnalysisPromptContext
from waygate_workflows.schema import DocumentMetadataState
from waygate_workflows.schema import DocumentSummaryState
from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import EntityRegistryEntry
from waygate_workflows.schema import GlossaryEntry
from waygate_workflows.schema import ProcessedDocumentBrief
from waygate_workflows.schema import ReferenceIndexEntry
from waygate_workflows.schema import claim_id_for_text, normalize_key
from waygate_workflows.content.guidance import load_agent_guidance_instructions
from waygate_workflows.runtime.text import normalize_string_list


def _supporting_source_uris(
    document_uri: str, document_source_uri: str | None
) -> list[str]:
    """Build the supporting source URI set for one analyzed document.

    Args:
        document_uri: Storage URI of the active document.
        document_source_uri: Optional upstream source URI from frontmatter.

    Returns:
        Deduplicated URI list used for durable provenance tracking.
    """
    return normalize_string_list([document_source_uri, document_uri])


def _upsert_named_entries(
    existing_entries: list[dict[str, object]],
    values: list[str],
    *,
    name_key: str,
    supporting_source_uris: list[str],
) -> list[dict[str, object]]:
    """Upsert canonical named entries such as topics, tags, or glossary terms.

    Args:
        existing_entries: Existing durable entries.
        values: New names to merge into the durable set.
        name_key: Field name holding the canonical value.
        supporting_source_uris: Provenance URIs for the current document.

    Returns:
        Updated durable entry list.
    """
    entries_by_key = {
        normalize_key(str(entry[name_key])): dict(entry) for entry in existing_entries
    }
    for value in values:
        normalized = normalize_key(value)
        if not normalized:
            continue
        current = entries_by_key.get(normalized)
        if current is None:
            entries_by_key[normalized] = {
                name_key: value,
                "aliases": [],
                "supporting_source_uris": supporting_source_uris,
            }
            continue
        current["supporting_source_uris"] = normalize_string_list(
            [*current.get("supporting_source_uris", []), *supporting_source_uris]
        )
    return list(entries_by_key.values())


def _upsert_entities(
    existing_entries: list[EntityRegistryEntry],
    values: list[str],
    *,
    kind: str,
    supporting_source_uris: list[str],
) -> list[EntityRegistryEntry]:
    """Upsert canonical entity registry entries for one entity kind.

    Args:
        existing_entries: Existing durable entity registry.
        values: New canonical names discovered in the active document.
        kind: Entity kind label.
        supporting_source_uris: Provenance URIs for the current document.

    Returns:
        Updated durable entity registry.
    """
    entries_by_key = {
        (str(entry["kind"]), normalize_key(entry["canonical_name"])): dict(entry)
        for entry in existing_entries
    }
    for value in values:
        normalized = normalize_key(value)
        if not normalized:
            continue
        current = entries_by_key.get((kind, normalized))
        if current is None:
            entries_by_key[(kind, normalized)] = {
                "kind": kind,
                "canonical_name": value,
                "aliases": [],
                "supporting_source_uris": supporting_source_uris,
            }
            continue
        current["supporting_source_uris"] = normalize_string_list(
            [*current.get("supporting_source_uris", []), *supporting_source_uris]
        )
    return list(entries_by_key.values())


def _upsert_claims(
    existing_entries: list[ClaimLedgerEntry],
    values: list[str],
    *,
    supporting_source_uris: list[str],
    related_entities: list[str],
    related_terms: list[str],
) -> list[ClaimLedgerEntry]:
    """Upsert grounded claims into the durable claim ledger.

    Args:
        existing_entries: Existing claim ledger entries.
        values: Claims extracted from the active document.
        supporting_source_uris: Provenance URIs for the current document.
        related_entities: Referenced entities connected to each claim.
        related_terms: Defined terms connected to each claim.

    Returns:
        Updated durable claim ledger.
    """
    entries_by_key = {
        normalize_key(entry["text"]): dict(entry) for entry in existing_entries
    }
    for value in values:
        normalized = normalize_key(value)
        if not normalized:
            continue
        current = entries_by_key.get(normalized)
        if current is None:
            entries_by_key[normalized] = {
                "claim_id": claim_id_for_text(value),
                "text": value,
                "supporting_source_uris": supporting_source_uris,
                "related_entities": related_entities,
                "related_terms": related_terms,
            }
            continue
        current["supporting_source_uris"] = normalize_string_list(
            [*current.get("supporting_source_uris", []), *supporting_source_uris]
        )
        current["related_entities"] = normalize_string_list(
            [*current.get("related_entities", []), *related_entities]
        )
        current["related_terms"] = normalize_string_list(
            [*current.get("related_terms", []), *related_terms]
        )
    return list(entries_by_key.values())


def _build_reference_index(
    *,
    glossary: list[GlossaryEntry],
    entity_registry: list[EntityRegistryEntry],
    claim_ledger: list[ClaimLedgerEntry],
    prior_document_briefs: list[ProcessedDocumentBrief],
) -> list[ReferenceIndexEntry]:
    """Build the durable reference index from accumulated compile context.

    Args:
        glossary: Accumulated glossary entries.
        entity_registry: Accumulated entity registry.
        claim_ledger: Accumulated claim ledger.
        prior_document_briefs: Prior processed document briefs.

    Returns:
        Reference index entries used for later continuity resolution.
    """
    processed_uris = [brief["uri"] for brief in prior_document_briefs]
    index: list[ReferenceIndexEntry] = []
    for entry in glossary:
        index.append(
            {
                "key": entry["term"],
                "kind": "term",
                "source_uris": entry["supporting_source_uris"],
                "processed_document_uris": processed_uris,
                "claim_ids": [],
            }
        )
    for entry in entity_registry:
        index.append(
            {
                "key": entry["canonical_name"],
                "kind": "entity",
                "source_uris": entry["supporting_source_uris"],
                "processed_document_uris": processed_uris,
                "claim_ids": [],
            }
        )
    for entry in claim_ledger:
        index.append(
            {
                "key": entry["text"],
                "kind": "claim",
                "source_uris": entry["supporting_source_uris"],
                "processed_document_uris": processed_uris,
                "claim_ids": [entry["claim_id"]],
            }
        )
    return index


def _merge_unresolved_mentions(
    existing_entries: list[dict[str, object]],
    mentions: list[ContinuityMentionModel],
    *,
    source_uri: str,
) -> list[dict[str, object]]:
    """Merge unresolved mentions from the current analysis pass.

    Args:
        existing_entries: Existing unresolved mention entries.
        mentions: Newly detected unresolved mentions.
        source_uri: Source URI associated with the active document.

    Returns:
        Updated unresolved mention list.
    """
    merged = {
        (normalize_key(str(entry["raw_text"])), str(entry["source_uri"])): dict(entry)
        for entry in existing_entries
    }
    for mention in mentions:
        raw_text = mention.raw_text.strip()
        if not raw_text:
            continue
        key = (normalize_key(raw_text), source_uri)
        current = merged.get(key)
        if current is None:
            merged[key] = {
                "raw_text": raw_text,
                "kind_hint": mention.kind_hint,
                "source_uri": source_uri,
                "status": "open",
            }
            continue
        if not current.get("kind_hint") and mention.kind_hint:
            current["kind_hint"] = mention.kind_hint
    return list(merged.values())


def _supporting_uris_overlap(
    candidate_uris: list[str],
    supporting_source_uris: list[str],
) -> bool:
    """Check whether two provenance URI sets overlap.

    Args:
        candidate_uris: Candidate provenance URIs.
        supporting_source_uris: Active document provenance URIs.

    Returns:
        ``True`` when the sets intersect.
    """
    return bool(set(candidate_uris).intersection(supporting_source_uris))


def _mention_matches_candidate(raw_text: str, candidate: str) -> bool:
    """Determine whether an unresolved mention is satisfied by a candidate.

    Args:
        raw_text: Raw unresolved mention text.
        candidate: Candidate term, entity, claim, or reference string.

    Returns:
        ``True`` when the candidate plausibly resolves the mention.
    """
    mention_key = normalize_key(raw_text)
    candidate_key = normalize_key(candidate)
    if not mention_key or not candidate_key:
        return False
    if mention_key == candidate_key:
        return True
    if mention_key in candidate_key or candidate_key in mention_key:
        return True
    mention_tokens = set(mention_key.split())
    candidate_tokens = set(candidate_key.split())
    return bool(mention_tokens) and mention_tokens.issubset(candidate_tokens)


def _build_resolution_candidates(
    *,
    glossary: list[GlossaryEntry],
    entity_registry: list[EntityRegistryEntry],
    claim_ledger: list[ClaimLedgerEntry],
    reference_index: list[ReferenceIndexEntry],
    supporting_source_uris: list[str],
) -> list[str]:
    """Collect candidate strings that may resolve prior unresolved mentions.

    Args:
        glossary: Accumulated glossary entries.
        entity_registry: Accumulated entity registry.
        claim_ledger: Accumulated claim ledger.
        reference_index: Accumulated reference index.
        supporting_source_uris: Provenance URIs for the active document.

    Returns:
        Deduplicated candidate strings associated with the active document.
    """
    candidates: list[str] = []
    for entry in glossary:
        if _supporting_uris_overlap(
            entry["supporting_source_uris"], supporting_source_uris
        ):
            candidates.extend([entry["term"], *entry["aliases"]])
    for entry in entity_registry:
        if _supporting_uris_overlap(
            entry["supporting_source_uris"], supporting_source_uris
        ):
            candidates.extend([entry["canonical_name"], *entry["aliases"]])
    for entry in claim_ledger:
        if _supporting_uris_overlap(
            entry["supporting_source_uris"], supporting_source_uris
        ):
            candidates.extend(
                [entry["text"], *entry["related_entities"], *entry["related_terms"]]
            )
    for entry in reference_index:
        if _supporting_uris_overlap(entry["source_uris"], supporting_source_uris):
            candidates.append(entry["key"])
    return normalize_string_list(candidates)


def _resolve_unresolved_mentions(
    entries: list[dict[str, object]],
    *,
    resolution_candidates: list[str],
) -> list[dict[str, object]]:
    """Resolve open unresolved mentions against the current candidate set.

    Args:
        entries: Existing unresolved mention entries.
        resolution_candidates: Candidate strings associated with the current
            document.

    Returns:
        Updated unresolved mention list with resolved statuses applied.
    """
    resolved_entries: list[dict[str, object]] = []
    for entry in entries:
        current = dict(entry)
        if current.get("status") == "open" and any(
            _mention_matches_candidate(str(current["raw_text"]), candidate)
            for candidate in resolution_candidates
        ):
            current["status"] = "resolved"
        resolved_entries.append(current)
    return resolved_entries


def _normalized_document_text(document: dict[str, object]) -> str:
    """Collapse key document fields into one normalized comparison string.

    Args:
        document: Active document mapping.

    Returns:
        Normalized searchable text used by prompt-context selection helpers.
    """
    parts = [
        document.get("uri"),
        document.get("content"),
        document.get("source_uri"),
        document.get("source_type"),
    ]
    return normalize_key(" ".join(str(part) for part in parts if part))


def _entry_matches_document(
    *,
    candidates: list[str],
    document_text: str,
    fallback_terms: set[str],
) -> bool:
    """Check whether any candidate term is relevant to the active document.

    Args:
        candidates: Candidate strings to test.
        document_text: Normalized searchable document text.
        fallback_terms: Terms derived from recent context when direct matching is
            insufficient.

    Returns:
        ``True`` when the active document or fallback context matches.
    """
    for candidate in candidates:
        normalized = normalize_key(candidate)
        if not normalized:
            continue
        if normalized in document_text or normalized in fallback_terms:
            return True
    return False


def _select_recent_prior_briefs(
    state: DraftGraphState,
    document_text: str,
    *,
    limit: int,
) -> list[ProcessedDocumentBrief]:
    """Select prior briefs that are most relevant to the active document.

    Args:
        state: Current draft workflow state.
        document_text: Normalized searchable document text.
        limit: Maximum number of briefs to return.

    Returns:
        Relevant recent briefs, with a recency fallback when none match.
    """
    relevant: list[ProcessedDocumentBrief] = []
    for brief in state["prior_document_briefs"]:
        candidates = [
            brief["summary"],
            *brief["key_claims"],
            *brief["defined_terms"],
            *brief["discovered_topics"],
            *brief["discovered_tags"],
            *brief["referenced_entities"],
        ]
        if _entry_matches_document(
            candidates=candidates,
            document_text=document_text,
            fallback_terms=set(),
        ):
            relevant.append(brief)
    if relevant:
        return relevant[-limit:]
    return state["prior_document_briefs"][-limit:]


def _fallback_terms_from_context(
    prior_briefs: list[ProcessedDocumentBrief],
    unresolved_mentions: list[dict[str, object]],
) -> set[str]:
    """Derive fallback search terms from the current rolling context.

    Args:
        prior_briefs: Relevant recent document briefs.
        unresolved_mentions: Relevant unresolved mentions.

    Returns:
        Normalized context terms used as a secondary relevance signal.
    """
    terms: set[str] = set()
    for brief in prior_briefs:
        terms.update(normalize_key(value) for value in brief["defined_terms"])
        terms.update(normalize_key(value) for value in brief["discovered_topics"])
        terms.update(normalize_key(value) for value in brief["discovered_tags"])
        terms.update(normalize_key(value) for value in brief["referenced_entities"])
    for mention in unresolved_mentions:
        if mention.get("status") == "open":
            terms.add(normalize_key(str(mention["raw_text"])))
    return {term for term in terms if term}


def _select_named_subset(
    entries: list[dict[str, object]],
    *,
    primary_key: str,
    document_text: str,
    fallback_terms: set[str],
    limit: int,
) -> list[dict[str, object]]:
    """Select relevant canonical entries for prompt-context reconstruction.

    Args:
        entries: Canonical entry mappings.
        primary_key: Field holding the canonical entry name.
        document_text: Normalized searchable document text.
        fallback_terms: Context-derived secondary relevance terms.
        limit: Maximum number of entries to return.

    Returns:
        Relevant canonical entries for the active pass.
    """
    relevant = [
        entry
        for entry in entries
        if _entry_matches_document(
            candidates=[
                str(entry[primary_key]),
                *[str(alias) for alias in entry.get("aliases", [])],
            ],
            document_text=document_text,
            fallback_terms=fallback_terms,
        )
    ]
    return relevant[:limit]


def _select_claim_subset(
    claims: list[ClaimLedgerEntry],
    *,
    document_text: str,
    fallback_terms: set[str],
    limit: int,
) -> list[ClaimLedgerEntry]:
    """Select relevant claims for prompt-context reconstruction.

    Args:
        claims: Durable claim ledger entries.
        document_text: Normalized searchable document text.
        fallback_terms: Context-derived secondary relevance terms.
        limit: Maximum number of claims to return.

    Returns:
        Relevant claim ledger entries for the active pass.
    """
    relevant = [
        claim
        for claim in claims
        if _entry_matches_document(
            candidates=[
                claim["text"],
                *claim["related_entities"],
                *claim["related_terms"],
            ],
            document_text=document_text,
            fallback_terms=fallback_terms,
        )
    ]
    return relevant[:limit]


def _select_reference_subset(
    references: list[ReferenceIndexEntry],
    *,
    document_text: str,
    fallback_terms: set[str],
    claim_subset: list[ClaimLedgerEntry],
    limit: int,
) -> list[ReferenceIndexEntry]:
    """Select relevant references for prompt-context reconstruction.

    Args:
        references: Durable reference index entries.
        document_text: Normalized searchable document text.
        fallback_terms: Context-derived secondary relevance terms.
        claim_subset: Already-selected claim subset for the active pass.
        limit: Maximum number of references to return.

    Returns:
        Relevant reference index entries for the active pass.
    """
    claim_ids = {claim["claim_id"] for claim in claim_subset}
    relevant = [
        entry
        for entry in references
        if _entry_matches_document(
            candidates=[entry["key"]],
            document_text=document_text,
            fallback_terms=fallback_terms,
        )
        or bool(claim_ids.intersection(entry["claim_ids"]))
    ]
    return relevant[:limit]


def _select_unresolved_mentions(
    entries: list[dict[str, object]],
    *,
    document_text: str,
    fallback_terms: set[str],
    limit: int,
) -> list[dict[str, object]]:
    """Select unresolved mentions relevant to the active document.

    Args:
        entries: Durable unresolved mention entries.
        document_text: Normalized searchable document text.
        fallback_terms: Context-derived secondary relevance terms.
        limit: Maximum number of mentions to return.

    Returns:
        Relevant open unresolved mentions, with an open-entry fallback.
    """
    relevant = [
        entry
        for entry in entries
        if entry.get("status") == "open"
        and _entry_matches_document(
            candidates=[str(entry["raw_text"])],
            document_text=document_text,
            fallback_terms=fallback_terms,
        )
    ]
    if relevant:
        return relevant[:limit]
    open_entries = [entry for entry in entries if entry.get("status") == "open"]
    return open_entries[:limit]


def build_document_analysis_prompt_context(
    state: DraftGraphState,
    document: dict[str, object],
) -> DocumentAnalysisPromptContext:
    """Reconstruct bounded prompt context for one source-analysis pass.

    Args:
        state: Current durable draft workflow state.
        document: Active document mapping.

    Returns:
        Prompt context slice tailored to the active document.
    """
    document_text = _normalized_document_text(document)
    prior_briefs_subset = _select_recent_prior_briefs(state, document_text, limit=5)
    unresolved_mentions_subset = _select_unresolved_mentions(
        state["unresolved_mentions"],
        document_text=document_text,
        fallback_terms=set(),
        limit=20,
    )
    fallback_terms = _fallback_terms_from_context(
        prior_briefs_subset,
        unresolved_mentions_subset,
    )
    canonical_topics_subset = _select_named_subset(
        state["canonical_topics"],
        primary_key="name",
        document_text=document_text,
        fallback_terms=fallback_terms,
        limit=20,
    )
    canonical_tags_subset = _select_named_subset(
        state["canonical_tags"],
        primary_key="name",
        document_text=document_text,
        fallback_terms=fallback_terms,
        limit=20,
    )
    glossary_subset = _select_named_subset(
        state["glossary"],
        primary_key="term",
        document_text=document_text,
        fallback_terms=fallback_terms,
        limit=20,
    )
    entity_subset = _select_named_subset(
        state["entity_registry"],
        primary_key="canonical_name",
        document_text=document_text,
        fallback_terms=fallback_terms,
        limit=20,
    )
    claim_subset = _select_claim_subset(
        state["claim_ledger"],
        document_text=document_text,
        fallback_terms=fallback_terms,
        limit=20,
    )
    reference_subset = _select_reference_subset(
        state["reference_index"],
        document_text=document_text,
        fallback_terms=fallback_terms,
        claim_subset=claim_subset,
        limit=20,
    )
    # Optional guidance is layered in last so storage-backed prompt packs can
    # refine the generic consistency rules without altering durable state.
    guidance_instructions = load_agent_guidance_instructions(
        workflow_name="compile",
        role_name="source-analysis",
        source_type=(
            str(document.get("source_type")) if document.get("source_type") else None
        ),
    )
    return {
        "active_document": document,
        "active_document_position": state["document_cursor"],
        "canonical_topics_subset": canonical_topics_subset,
        "canonical_tags_subset": canonical_tags_subset,
        "glossary_subset": glossary_subset,
        "entity_subset": entity_subset,
        "claim_subset": claim_subset,
        "reference_subset": reference_subset,
        "prior_briefs_subset": prior_briefs_subset,
        "unresolved_mentions_subset": unresolved_mentions_subset,
        "prompt_instructions": [
            "Reuse previously discovered topics, tags, terms, entities, and grounded claims when appropriate.",
            "Do not rediscover concepts from scratch when the current document clearly refers to prior context.",
            "Stay grounded in the active document while using prior discoveries only for consistency and reference resolution.",
            *guidance_instructions,
        ],
    }


def compile_source_document(state: DraftGraphState) -> dict[str, object]:
    """Analyze the active source document and merge results into durable state.

    Args:
        state: Current durable draft workflow state.

    Returns:
        Partial state update containing the next active document and the merged
        durable compile context.

    Raises:
        ValueError: If the workflow is missing an active document.
    """
    document = state.get("active_document")
    if document is None:
        raise ValueError("Compile worker requires an active source document")

    # Prompt context is rebuilt from durable state each pass so retries and
    # resumes do not depend on transient in-memory data.
    prompt_context = build_document_analysis_prompt_context(state, document)
    core_settings = get_app_context().config.core
    analysis = analyze_source_document(
        document,
        prompt_context,
        metadata_model_name=core_settings.metadata_model_name,
        draft_model_name=core_settings.draft_model_name,
    )
    metadata: DocumentMetadataState = {
        "uri": analysis.uri,
        "tags": normalize_string_list(analysis.metadata.tags),
        "topics": normalize_string_list(analysis.metadata.topics),
        "people": normalize_string_list(analysis.metadata.people),
        "organizations": normalize_string_list(analysis.metadata.organizations),
        "projects": normalize_string_list(analysis.metadata.projects),
    }
    key_claims = normalize_string_list(
        [*analysis.findings.key_claims, *analysis.summary.key_claims]
    )
    defined_terms = normalize_string_list(
        [*analysis.findings.defined_terms, *analysis.summary.defined_terms]
    )
    summary: DocumentSummaryState = {
        "uri": analysis.uri,
        "summary": analysis.summary.summary.strip(),
        "key_claims": key_claims,
        "defined_terms": defined_terms,
    }
    supporting_source_uris = _supporting_source_uris(
        str(document["uri"]),
        document.get("source_uri"),
    )
    referenced_entities = normalize_string_list(
        [
            *metadata["people"],
            *metadata["organizations"],
            *metadata["projects"],
            *analysis.continuity.referenced_entities,
        ]
    )

    # These reducers turn one document's analysis into the evolving durable
    # compile context used by later documents, synthesis, and review.
    canonical_topics = _upsert_named_entries(
        state["canonical_topics"],
        metadata["topics"],
        name_key="name",
        supporting_source_uris=supporting_source_uris,
    )
    canonical_tags = _upsert_named_entries(
        state["canonical_tags"],
        metadata["tags"],
        name_key="name",
        supporting_source_uris=supporting_source_uris,
    )
    glossary = _upsert_named_entries(
        state["glossary"],
        summary["defined_terms"],
        name_key="term",
        supporting_source_uris=supporting_source_uris,
    )
    for entry in glossary:
        entry.setdefault("definition_hint", None)

    entity_registry = state["entity_registry"]
    entity_registry = _upsert_entities(
        entity_registry,
        metadata["people"],
        kind="person",
        supporting_source_uris=supporting_source_uris,
    )
    entity_registry = _upsert_entities(
        entity_registry,
        metadata["organizations"],
        kind="organization",
        supporting_source_uris=supporting_source_uris,
    )
    entity_registry = _upsert_entities(
        entity_registry,
        metadata["projects"],
        kind="project",
        supporting_source_uris=supporting_source_uris,
    )
    claim_ledger = _upsert_claims(
        state["claim_ledger"],
        summary["key_claims"],
        supporting_source_uris=supporting_source_uris,
        related_entities=referenced_entities,
        related_terms=summary["defined_terms"],
    )

    brief: ProcessedDocumentBrief = {
        "uri": summary["uri"],
        "summary": summary["summary"],
        "key_claims": summary["key_claims"],
        "defined_terms": summary["defined_terms"],
        "discovered_topics": metadata["topics"],
        "discovered_tags": metadata["tags"],
        "referenced_entities": referenced_entities,
        "supporting_source_uris": supporting_source_uris,
    }
    prior_document_briefs = [*state["prior_document_briefs"], brief]
    reference_index = _build_reference_index(
        glossary=glossary,
        entity_registry=entity_registry,
        claim_ledger=claim_ledger,
        prior_document_briefs=prior_document_briefs,
    )
    unresolved_mentions = _merge_unresolved_mentions(
        state["unresolved_mentions"],
        analysis.continuity.unresolved_mentions,
        source_uri=str(document.get("source_uri") or document["uri"]),
    )
    # Later documents can resolve earlier open mentions when they introduce a
    # matching term, entity, claim, or reference key.
    resolution_candidates = _build_resolution_candidates(
        glossary=glossary,
        entity_registry=entity_registry,
        claim_ledger=claim_ledger,
        reference_index=reference_index,
        supporting_source_uris=supporting_source_uris,
    )
    unresolved_mentions = _resolve_unresolved_mentions(
        unresolved_mentions,
        resolution_candidates=resolution_candidates,
    )

    next_cursor = state["document_cursor"] + 1
    next_document = (
        state["source_documents"][next_cursor]
        if next_cursor < len(state["source_documents"])
        else None
    )
    return {
        "document_cursor": next_cursor,
        "active_document": next_document,
        "extracted_metadata": [*state["extracted_metadata"], metadata],
        "document_summaries": [*state["document_summaries"], summary],
        "prior_document_briefs": prior_document_briefs,
        "canonical_topics": canonical_topics,
        "canonical_tags": canonical_tags,
        "glossary": glossary,
        "entity_registry": entity_registry,
        "claim_ledger": claim_ledger,
        "reference_index": reference_index,
        "unresolved_mentions": unresolved_mentions,
        "scratchpad": {
            "terms": normalize_string_list(
                [*state["scratchpad"]["terms"], *summary["defined_terms"]]
            ),
            "claims": normalize_string_list(
                [*state["scratchpad"]["claims"], *summary["key_claims"]]
            ),
        },
    }


def route_compile_source_document(state: DraftGraphState) -> str:
    """Choose whether to continue source analysis or advance to synthesis.

    Args:
        state: Current draft workflow state after one analysis pass.

    Returns:
        ``compile_source_document`` while more source documents remain,
        otherwise ``synthesis``.
    """
    if state.get("active_document") is None:
        return "synthesis"
    return "compile_source_document"
