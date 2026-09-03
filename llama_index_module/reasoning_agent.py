from llama_index.llms.openai import OpenAIResponses
from llama_index.core import PromptTemplate
from pydantic import BaseModel
from typing import Literal
from llama_index_module.schema_and_prompts.system_prompts import intent_resolution_prompt
from llama_index_module.schema_and_prompts.db_schema import GRAPH_DB_SCHEMA_JSON
from typing import Literal
from pydantic import BaseModel, Field
import json

from llama_index_module.retrieval_agent import function_tools

llm = OpenAIResponses(
    model="gpt-5.6-terra", 
    temperature=0.0, 
    strict=True, 
    reasoning_options={
        "effort": "xhigh",
        "summary": "auto",
    }
)

INDEX_MAP = {
    "ticket": "ticket_full_text_index",
    "person": "person_full_text_index",
    "environment":"environment_full_text_index",
    "system": "system_full_text_index",
    "label": "label_full_text_index",
    "track": "track_full_text_index",
    "investigationReport": "investigation_report_full_text_index",
    "repositoryObject": "repository_objects_full_text_index",
    "comment": "comment_full_text_index",
}

class QueryIntentResult(BaseModel):
    intent: Literal["METADATA", "ANALYSIS", "ROOT_CAUSE", "RESOLUTION", "COMMENTS", "CODE_CHANGES", \
                    "RELATED_TICKETS", "SEMANTIC_SEARCH", "EXACT_SEARCH", "AGGREGATION", "GENERAL"]
    sub_intent: str
    required_evidence: list[str]
    retrieval_strategy: list[str]

class EntityCandidateSelection(BaseModel):
    resolved: bool
    selected_element_id: str | None
    selected_name: str | None
    entity_type: str | None
    confidence: Literal["high", "medium", "low", "unresolved"]
    reason: str

class EntitySelectionResult(BaseModel):
    status: str
    entities: list[EntityCandidateSelection]

class ResolvedEntity(BaseModel):
    user_reference: str
    entity_type: str
    confidence: Literal["high", "medium", "low", "unresolved"]

class EntityResolutionResult(BaseModel):
    status: Literal["success", "partial", "unresolved"]
    entities: list[ResolvedEntity]

class QueryContext(BaseModel):
    user_query: str
    query_intent: QueryIntentResult

def get_index(type: str) -> str:
    return INDEX_MAP(type)

def analyze_query_intent_tool(query: str) -> str:

    prompt = PromptTemplate("""
    User Query : {query}
    {intent_resolution_prompt}
    """)

    result = llm.structured_predict(
        QueryIntentResult, 
        prompt=prompt, 
        query=query, 
        intent_resolution_prompt = intent_resolution_prompt
    )
    
    return result.model_dump_json()

async def resolve_query_entities_tool(user_query: str, intent_result: str) -> str:

    prompt = PromptTemplate("""
    Extract the entities required to satisfy the user's request.
    Read the intent and the user query and make the DB Schema as your factual basis.
    The entities should only be resolved as per the graph schema provided, as the graph is the factual
    truth.

    USER QUERY:
    {user_query}

    INTENT ANALYSIS:
    {intent_result}

    Use the intent and required evidence to determine which entities
    must be resolved.

    For each entity, return:
    - user_reference: the exact phrase used by the user
    - entity_type: the most likely graph entity type
    - confidence: valid values are 'high', 'medium', 'low' or 'unresolved'

    ### STRICT GRAPH ENTITY RESOLUTION

    Use the schema as the sole authority for entity typing.

    - `entity_type` MUST exactly match a valid Neo4j node label.
    - Use the user's query, intent, and context to select the most specific valid label.
    - Use relationships only to validate the choice, never to invent a type.
    - Never use natural-language categories or unsupported labels.
    - If no valid label can be determined, return `unknown`.
    - Preserve the user's exact wording in `user_reference`.
    - Do not resolve canonical names or `elementId` at this stage.

    Graph entity types:
    ticket, person, investigationReport, repositoryObjects, comment,
    system, environment, track, issueType, label

    ticket
    --HAS_INVESTIGATION--> investigationReport
    --HAS_REPOSITORY_OBJECTS--> repositoryObjects
    --HAS_COMMENT--> comment
    --HAS_LABEL--> label
    --AFFECTS_SYSTEM--> system
    --IMPACTS--> environment
    --BELONGS_TO_TRACK--> track
    --IS_OF_TYPE--> issueType
    <--REPORTS-- person
    <--WATCHES-- person
    --DEFECTS--> ticket
    --DUPLICATES--> ticket
    --CLONES--> ticket
    --CONTAINS_WBS_GANTT--> ticket

    person --REPORTS--> ticket
    person --WATCHES--> ticket

    Rules:
    - Extract only entities relevant to the identified intent.
    - Preserve the exact user reference.
    - Assign the most appropriate graph entity type making the graph schema as reasoning basis.
    - Do not invent canonical names or element IDs.
    - Do not perform retrieval or resolution yourself.
    - Return only the EntityResolutionResult.
    """)

    extracted = llm.structured_predict(
        EntityResolutionResult, 
        prompt = prompt, 
        user_query = user_query,
        intent_result = intent_result
    )

    resolved_entities = []
    unresolved_entities = []


    for entity in extracted.entities:      

        index_name = INDEX_MAP.get(entity.entity_type)
        print(entity.entity_type)
        print(index_name)

        if not index_name:
            unresolved_entities.append(entity)
            continue

        matches = await function_tools.full_text_keyword_tool(
            keyword=entity.user_reference,
            index_name=index_name
        )       

        matches = json.loads(matches)
        matches = matches['results']

        candidate_result = await select_entity_candidate(
            entity=entity,
            candidates=matches
        )
        
        resolved_entities.append(candidate_result)

    result = EntitySelectionResult(
        status="success",
        entities=resolved_entities
    )

    return result.model_dump_json()


async def select_entity_candidate(entity: dict, candidates: list[dict]) -> EntityCandidateSelection:

    entity_reference = entity.user_reference
    expected_type = entity.entity_type

    normalized_candidates   = []

    for candidate in candidates:
        if not candidate.get("element_id"):
            continue

        normalized_candidates.append({
            "element_id": candidate.get("element_id"),
            "labels": candidate.get("labels", []),
            "properties": candidate.get("properties", {}),
            "score": candidate.get("score", 0.0),
        })

    if not normalized_candidates:
        return EntityCandidateSelection(
            resolved=False,
            selected_element_id=None,
            selected_name=None,
            entity_type=expected_type,
            confidence="unresolved",
            reason="No valid graph candidates were returned by lexical search."
        )

    selection_prompt = PromptTemplate(f"""
    You are an enterprise graph entity-resolution specialist.

    Your job is to select the graph entity that best matches the user's
    entity reference from the supplied candidate list.

    USER ENTITY REFERENCE:
    {entity_reference}

    EXPECTED ENTITY TYPE:
    {expected_type or "unknown"}

    CANDIDATES:
    {normalized_candidates}

    RULES:

    1. Select ONLY from the supplied candidates.
    2. NEVER invent, alter, truncate, or reconstruct an element_id.
    3. The selected_element_id must exactly equal an element_id present in
    the candidate list.
    4. Prefer candidates whose graph labels match the expected entity type.
    5. Prefer exact or strong near-exact name matches.
    6. Consider aliases, honorifics, abbreviations, and partial names when
    supported by the candidate properties.
    7. Use lexical relevance scores as supporting evidence.
    8. Do not select a candidate merely because it has the highest score if
    another candidate is clearly a better semantic/entity-type match.
    9. If the evidence is ambiguous, return resolved=false.
    10. Do not fabricate missing information.

    Return a structured resolution decision.
    """)

    result = llm.structured_predict(
        EntityCandidateSelection,
        prompt=selection_prompt,
        entity_reference=entity_reference,
        expected_type=expected_type,
        normalized_candidates=normalized_candidates
    )

    valid_ids = {
        candidate["element_id"]
        for candidate in normalized_candidates
    }

    if result.resolved:
        if result.selected_element_id not in valid_ids:

            return EntityCandidateSelection(
                resolved=False,
                selected_element_id=None,
                selected_name=None,
                confidence="unresolved",
                reason=(
                    "The model selected an element ID that was not present "
                    "in the supplied candidate set."
                )
            )            

        selected_candidate = next(
            candidate
            for candidate in normalized_candidates
            if candidate["element_id"] == result.selected_element_id
        )

        properties = selected_candidate.get("properties", {})

        canonical_name = (
            properties.get("name")
            or properties.get("display_name")
            or properties.get("full_name")
            or result.selected_name
        )

        labels = selected_candidate.get("labels", [])

        return EntityCandidateSelection(
            resolved=True,
            selected_element_id=result.selected_element_id,
            selected_name=canonical_name,
            entity_type=labels[0] if labels else expected_type,
            confidence=result.confidence,
            reason=result.reason
        )

    return result

    
