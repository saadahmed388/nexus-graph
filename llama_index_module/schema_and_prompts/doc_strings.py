select_entity_candidate_docstring ="""
    Select the best graph entity candidate for a user-referenced entity.

    This is a candidate-selection step, NOT an entity-search step.

    The candidates supplied to this function are authoritative. The selector
    MUST choose from those candidates only and MUST NEVER invent, modify, or
    synthesize a Neo4j element ID.

    Selection should consider:
    - User's original entity reference
    - Expected entity type
    - Candidate graph labels
    - Candidate canonical names and relevant properties
    - Lexical relevance score
    - Other contextual information present in the candidates

    Resolution rules:
    1. Prefer a candidate whose entity type matches the expected type.
    2. Prefer strong exact or near-exact name matches.
    3. Use aliases, honorifics, abbreviations, and partial-name matches when
       they are supported by candidate properties.
    4. Use the lexical score as supporting evidence, not as the only criterion.
    5. If one candidate is clearly superior, select it.
    6. If several candidates remain similarly plausible, do not guess.
       Return resolved=false and confidence="unresolved".
    7. If no candidate is relevant, return resolved=false.
    8. If resolved, selected_element_id MUST exactly match the element_id
       of one supplied candidate.

    Args:
        entity:
            Entity reference extracted from the user's query. Expected fields
            may include:
                {
                    "reference": "Tsunoda San",
                    "entity_type": "person"
                }

        candidates:
            Candidate graph entities returned by lexical search. Each
            candidate should contain an element_id, labels, properties,
            and relevance score.

    Returns:
        EntityCandidateSelection containing the selected canonical entity
        and exact Neo4j element ID, or an unresolved result.
    """


resolve_query_entity_tools_docstring= """
    Identify and resolve important entities mentioned in a user query.

    This tool resolves human-readable references, aliases, partial names,
    abbreviations, and explicit identifiers into exact graph entities.

    Use lexical/full-text retrieval for human-readable entity references
    when appropriate.

    For each resolved entity return:
    - The user's original reference
    - Entity type
    - Canonical name
    - Exact Neo4j element ID
    - Resolution confidence

    Do not invent entities or identifiers.

    If an entity cannot be uniquely resolved, mark it unresolved rather
    than guessing.
    """

analyze_intent_docstring =    """
    Analyze the user's request and determine the primary information need.

    This tool is a query-understanding and routing tool. It does not retrieve
    graph data and must not answer the user's question.

    Determine:
    - Primary intent
    - More specific sub-intent
    - Evidence required to answer the request
    - Recommended retrieval strategy

    Examples:
    "Analyze MFTBCFFR-4557"
        → ANALYSIS

    "What was fixed in MFTBCFFR-4557?"
        → RESOLUTION / CODE_CHANGES

    "How many tickets were raised by Tsunoda San?"
        → AGGREGATION

    "What did engineers discuss?"
        → COMMENTS

    "Find tickets similar to this issue."
        → SEMANTIC_SEARCH
    """