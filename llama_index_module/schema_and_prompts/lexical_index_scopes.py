LEXICAL_BASIC_SCOPE_MAP = {

    # ---------------------------------------------------------
    # Core incident / ticket evidence
    # ---------------------------------------------------------

    "ticket": [
        "ticket_full_text_index",
    ],

    # Use when the query is primarily about a person identity.
    "person": [
        "person_full_text_index",
    ],

    # Use for conversations, comments, discussions, authored remarks.
    "comment": [
        "comment_full_text_index",
    ],

    # Investigation-specific terminology, RCA, diagnosis, remediation.
    "investigation_report": [
        "investigation_report_full_text_index",
    ],

    # Code / repository / PR / file related terminology.
    "repository_object": [
        "repository_objects_full_text_index",
    ],

    # Infrastructure / deployment / runtime context.
    "system": [
        "system_full_text_index",
    ],

    "environment": [
        "environment_full_text_index",
    ],

    # Classification / categorization.
    "label": [
        "label_full_text_index",
    ],

    "track": [
        "track_full_text_index",
    ],
}

LEXICAL_COMPOUND_SCOPE_MAP = {

    # Broad person/activity discovery.
    "person_activity": [
        "person_full_text_index",
        "comment_full_text_index",
        "ticket_full_text_index",
        "investigation_report_full_text_index",
    ],

    # Broad incident discovery.
    "incident_context": [
        "ticket_full_text_index",
        "comment_full_text_index",
        "investigation_report_full_text_index",
        "system_full_text_index",
        "environment_full_text_index",
    ],

    # Investigation discovery.
    "investigation_context": [
        "ticket_full_text_index",
        "investigation_report_full_text_index",
        "comment_full_text_index",
    ],

    # Code / engineering investigation.
    "code_investigation": [
        "ticket_full_text_index",
        "repository_objects_full_text_index",
        "investigation_report_full_text_index",
        "comment_full_text_index",
    ],

    # Broad cross-domain discovery.
    "global": [
        "ticket_full_text_index",
        "person_full_text_index",
        "comment_full_text_index",
        "investigation_report_full_text_index",
        "repository_objects_full_text_index",
        "system_full_text_index",
        "environment_full_text_index",
        "label_full_text_index",
        "track_full_text_index",
    ],
}


LEXICAL_SCOPE_MAP = {
    **LEXICAL_BASIC_SCOPE_MAP,
    **LEXICAL_COMPOUND_SCOPE_MAP,
}