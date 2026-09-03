VECTOR_SCOPE_MAP = {

    # Incident / ticket semantic similarity.
    "ticket": [
        "ticket_embedding_index",
    ],

    # Root cause, diagnosis, fix, remediation, investigation findings.
    "investigation_report": [
        "investigation_report_embedding_index",
    ],

    # Code, files, PRs, repository objects.
    "repository_object": [
        "repository_objects_embedding_index",
    ],

    # Discussions and conversational evidence.
    "comment": [
        "comment_embedding_index",
    ],

    # Broad cross-domain semantic search.
    "global": [
        "semantic_search_index",
    ],
}