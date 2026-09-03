"""
Static configuration: index-name mappings, intent-to-strategy profiles, and
fusion/rerank weights. Centralizing these here is what keeps the ranking
system "simple enough to be adjusted later" per the design brief — retuning
never requires touching pipeline logic.
"""
from __future__ import annotations

# --- node label -> full-text index -----------------------------------------------
FULLTEXT_INDEX_BY_LABEL: dict[str, str] = {
    "ticket": "ticket_full_text_index",
    "investigationReport": "investigation_report_full_text_index",
    "repositoryObjects": "repository_objects_full_text_index",
    "comment": "comment_full_text_index",
    "person": "person_full_text_index",
    "label": "label_full_text_index",
    "system": "system_full_text_index",
    "environment": "environment_full_text_index",
    "track": "track_full_text_index",
}

# --- node label -> vector index ---------------------------------------------------
VECTOR_INDEX_BY_LABEL: dict[str, str] = {
    "ticket": "ticket_embedding_index",
    "investigationReport": "investigation_report_embedding_index",
    "repositoryObjects": "repository_objects_embedding_index",
    "comment": "comment_embedding_index",
}

SEMANTIC_FALLBACK_INDEX = "semantic_search_index"

INTENT_PROFILES: dict[str, dict] = {
    "METADATA": {
        "lexical_labels": ["ticket", "person", "system", "environment", "track", "label"],
        "vector_labels": [],
        "graph_ops": ["get_node_details_tool", "count_tickets_by_metadata_tool"],
        "priority": ["graph", "lexical", "vector"],
    },
    "ANALYSIS": {
        "lexical_labels": ["ticket", "investigationReport", "comment"],
        "vector_labels": ["investigationReport", "ticket", "comment"],
        "graph_ops": ["get_ticket_relations_tool", "get_all_connected_nodes_content_tool"],
        "priority": ["vector", "graph", "lexical"],
    },
    "ROOT_CAUSE": {
        "lexical_labels": ["investigationReport", "ticket"],
        "vector_labels": ["investigationReport", "ticket", "comment"],
        "graph_ops": ["get_ticket_relations_tool", "get_all_connected_nodes_content_tool"],
        "priority": ["vector", "graph", "lexical"],
    },
    "RESOLUTION": {
        "lexical_labels": ["investigationReport", "repositoryObjects", "ticket"],
        "vector_labels": ["investigationReport", "repositoryObjects", "ticket"],
        "graph_ops": ["get_ticket_relations_tool", "get_all_connected_nodes_content_tool"],
        "priority": ["vector", "graph", "lexical"],
    },
    "COMMENTS": {
        "lexical_labels": ["comment"],
        "vector_labels": ["comment"],
        "graph_ops": ["get_all_connected_nodes_content_tool"],
        "priority": ["lexical", "vector", "graph"],
    },
    "CODE_CHANGES": {
        "lexical_labels": ["repositoryObjects"],
        "vector_labels": ["repositoryObjects"],
        "graph_ops": ["get_all_connected_nodes_content_tool"],
        "priority": ["lexical", "vector", "graph"],
    },
    "RELATED_TICKETS": {
        "lexical_labels": ["ticket"],
        "vector_labels": ["ticket"],
        "graph_ops": ["traverse_ticket_network_tool", "get_ticket_relations_tool"],
        "priority": ["graph", "vector", "lexical"],
    },
    "SEMANTIC_SEARCH": {
        "lexical_labels": ["ticket"],
        "vector_labels": [],  # empty -> broad semantic_search_index fallback
        "graph_ops": [],
        "priority": ["vector", "lexical", "graph"],
    },
    "EXACT_SEARCH": {
        "lexical_labels": ["ticket", "person", "system", "environment", "track", "label"],
        "vector_labels": [],
        "graph_ops": [],
        "priority": ["lexical", "graph", "vector"],
    },
    "AGGREGATION": {
        "lexical_labels": ["ticket", "person"],
        "vector_labels": [],
        "graph_ops": ["count_tickets_by_metadata_tool", "get_ticket_relations_tool"],
        "priority": ["graph", "lexical", "vector"],
    },
    "GENERAL": {
        "lexical_labels": ["ticket"],
        "vector_labels": [],  # semantic fallback
        "graph_ops": [],
        "priority": ["vector", "lexical", "graph"],
    },
}

# --- required_evidence keyword -> node label ---------------------------------------
# Maps free-text QueryIntentResult.required_evidence strings onto concrete
# graph labels / index choices whenever they name a type.
EVIDENCE_KEYWORD_TO_LABEL: dict[str, str] = {
    "ticket": "ticket",
    "investigation": "investigationReport",
    "investigationreport": "investigationReport",
    "report": "investigationReport",
    "repository": "repositoryObjects",
    "code": "repositoryObjects",
    "comment": "comment",
    "person": "person",
    "reporter": "person",
    "watcher": "person",
    "label": "label",
    "system": "system",
    "environment": "environment",
    "track": "track",
}


def labels_from_required_evidence(required_evidence: list[str]) -> list[str]:
    """Best-effort mapping of free-text evidence requirements to node labels."""
    labels: list[str] = []
    for item in required_evidence:
        key = item.strip().lower()
        label = EVIDENCE_KEYWORD_TO_LABEL.get(key)
        if not label:
            for keyword, candidate_label in EVIDENCE_KEYWORD_TO_LABEL.items():
                if keyword in key:
                    label = candidate_label
                    break
        if label and label not in labels:
            labels.append(label)
    return labels


def intent_priority_labels(intent: str) -> set[str]:
    """Labels the given intent prioritizes, used for the rerank intent-match bonus."""
    profile = INTENT_PROFILES.get(intent, INTENT_PROFILES["GENERAL"])
    return set(profile.get("lexical_labels", [])) | set(profile.get("vector_labels", []))


# --- fusion / rerank tuning --------------------------------------------------------
# Reciprocal Rank Fusion is used to combine modality-specific rankings rather
# than raw scores, since lexical (Lucene) and vector (cosine/dot) scores live
# on incomparable scales. RRF_K is the standard damping constant; scaling by
# it keeps a rank-1 hit worth close to 1.0, decaying smoothly thereafter, so
# it's on a similar order of magnitude to the additive bonuses below.
RRF_K = 60

RERANK_WEIGHTS: dict[str, float] = {
    "lexical": 0.9,
    "vector": 1.0,
    "graph": 1.1,
    "intent_label_match": 0.6,
    "required_evidence_match": 0.9,
    "entity_match": 0.8,
    "multi_source_bonus": 0.25,  # additive, per extra modality that agrees
}

MAX_ADDITIONAL_RETRIEVAL_ROUNDS = 1
DEFAULT_TOP_K = 12
PER_LABEL_MIN_SLOTS = 2  # reserve at least this many slots per required-evidence label
