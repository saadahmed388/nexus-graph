import json
from typing import Any, Dict, List, Optional
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core import PromptTemplate
from llama_index_module.schema_and_prompts.db_schema import GRAPH_DB_SCHEMA_JSON
from llama_index_module.schema_and_prompts.lexical_index_scopes import LEXICAL_SCOPE_MAP
from llama_index_module.schema_and_prompts.vector_index_scopes import VECTOR_SCOPE_MAP
import regex as re
from pydantic import BaseModel, Field
import asyncio

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

class CypherModel(BaseModel):
    cypher: str = Field(description="Read-only Cypher query.")
    parameters: str = Field(description="Parameters referenced by the Cypher query using $parameter_name.")

class Neo4jVectorRetriever(BaseRetriever):
    """
    LlamaIndex-compatible retriever backed directly by a Neo4j vector index.
    """

    def __init__(self, driver, embedding_model, index_name: str, top_k: int = 20):
        super().__init__()
        self.driver = driver
        self.embedding_model = embedding_model
        self.index_name = index_name
        self.top_k = top_k

    @staticmethod
    def _clean_properties(props: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in props.items() if k not in {"vector_embedding", "full_vector_embedding"}}

    @classmethod
    def _neo4j_record_to_node(cls, row) -> NodeWithScore:
        element_id = str(row["element_id"])
        labels = row["labels"] or []
        clean_props = cls._clean_properties(row["props"] or {})
        properties_json = json.dumps(clean_props, default=str, sort_keys=True, ensure_ascii=False)
        text = properties_json
        
        node = TextNode(
            id_=element_id,
            text=text,
            metadata={
                "element_id": element_id,
                "labels": ",".join(labels),
                "properties_json": properties_json,
            },
        )

        return NodeWithScore(
            node=node,
            score=float(row["score"] or 0.0),
        )

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:

        query_text = query_bundle.query_str
        query_vector = await asyncio.to_thread(
            self.embedding_model.get_query_embedding,
            query_text,
        )

        cypher_query = """
        CALL db.index.vector.queryNodes($index_name, $top_k, $vector)
        YIELD node, score
        RETURN
            elementId(node) AS element_id,
            properties(node) AS props,
            labels(node) AS labels,
            score
        """

        nodes: List[NodeWithScore] = []

        async with self.driver.session() as session:
            result = await session.run(
                cypher_query,
                index_name=self.index_name,
                top_k=self.top_k,
                vector=query_vector,
            )

            async for row in result:
                nodes.append(
                    self._neo4j_record_to_node(row)
                )
        print(f"======== Vector Nodes Count ===={len(nodes)}===============")

        return nodes

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            raise RuntimeError(
                "Neo4jVectorRetriever is async-only. "
                "Use QueryFusionRetriever with use_async=True."
            )

        return asyncio.run(self._aretrieve(query_bundle))


class Neo4jFullTextRetriever(BaseRetriever):
    """
    LlamaIndex-compatible retriever backed directly by one
    Neo4j Lucene full-text index.
    """

    def __init__(self, driver, index_name: str, top_k: int = 20):
        super().__init__()
        self.driver = driver
        self.index_name = index_name
        self.top_k = top_k

    @staticmethod
    def _clean_properties(props: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in props.items()
            if k not in {"vector_embedding", "full_vector_embedding"}
        }

    @classmethod
    def _neo4j_record_to_node(cls, row) -> NodeWithScore:
        element_id = str(row["element_id"])
        labels = row["labels"] or []
        clean_props = cls._clean_properties(row["props"] or {})
        properties_json = json.dumps(clean_props, default=str, sort_keys=True, ensure_ascii=False)

        node = TextNode(
            id_=element_id,
            text=properties_json,
            metadata={
                "element_id": element_id,
                "labels": ",".join(labels),
                "properties_json": properties_json,
            },
        )
        
        return NodeWithScore(
            node=node,
            score=float(row["score"] or 0.0),
        )

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:

        keyword = query_bundle.query_str

        cypher_query = """
        CALL db.index.fulltext.queryNodes($index_name, $keyword)
        YIELD node, score

        RETURN
            elementId(node) AS element_id,
            properties(node) AS props,
            labels(node) AS labels,
            score

        LIMIT $top_k
        """

        nodes: List[NodeWithScore] = []

        async with self.driver.session() as session:
            result = await session.run(
                cypher_query,
                index_name=self.index_name,
                keyword=keyword,
                top_k=self.top_k,
            )

            async for row in result:
                nodes.append(
                    self._neo4j_record_to_node(row)
                )

        print(f"======== Full Text Nodes Count ===={len(nodes)}===============")

        return nodes

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            raise RuntimeError(
                "Neo4jFullTextRetriever is async-only. "
                "Use QueryFusionRetriever with use_async=True."
            )

        return asyncio.run(self._aretrieve(query_bundle))

class FunctionTools:
    def __init__(self, driver, embedding_model, llm_model):
        self.driver = driver
        self.embedding_model = embedding_model
        self.llm_model = llm_model

    async def vector_search_tool(self, query_text: str, index_name: str) -> str:
        """
        Performs high-accuracy semantic vector search using dense embeddings across specified graph indexes.
        
        Use this tool when a user query contains a conversational, broad, or conceptual issue description 
        (e.g., an active server incident, a complex error description, or a bug description) and you need 
        to locate relevant historical elements based on meaning rather than exact keywords.
        
        Args:
            query_text (str): The raw natural language text, incident description, or conceptual query to search for.
            index_name (str, optional): The target vector index to query. You MUST choose the most specific index 
                based on the user's intent from these valid options:
                - 'ticket_embedding_index': Specifically searches across core ticket fields (summaries, titles, descriptions).
                - 'investigation_report_embedding_index': Specifically searches engineering root cause analyses and fix actions.
                - 'repository_objects_embedding_index': Specifically searches files, pull requests, and objects changed in code.
                - 'comment_embedding_index': Specifically searches user and engineer discussion text streams.
                - 'semantic_search_index': A global fallback index that searches across all blended text chunks.
                Defaults to "semantic_search_index".
                
        Returns:
            str: A multi-line string containing a list of the top matching entity keys, titles, and similarity scores.
                Example format: 'Ticket: PROJ-101 (Score: 0.92) - Title: "Fix memory leak in auth validator"'
        """

        try:

            query_vector = self.embedding_model.get_query_embedding(query_text)
            
            cypher_query = f"""
            CALL db.index.vector.queryNodes($index_name, 10, $vector) 
            YIELD node, score
            RETURN 
                elementId(node) AS element_id,
                properties(node) AS props, 
                labels(node) AS labels,
                score
            """
            async with self.driver.session() as session:
                result = await session.run(cypher_query, index_name=index_name, vector=query_vector)
                records = []
                async for row in result:

                    clean_props = {
                        k: v for k, v in row['props'].items() 
                        if k not in {'vector_embedding', 'full_vector_embedding'}
                    }

                    records.append({
                        "element_id": row['element_id'],
                        "labels": row['labels'] or [],
                        "properties": clean_props,
                        "score": row['score']
                    })

                    json_str_output = json.dumps({
                        "status": "success",
                        "search_type": "vector",
                        "query": query_text,
                        "index": index_name,
                        "count": len(records),
                        "results": records
                    }, default=str)
                
            return json_str_output

        except:
            import traceback
            print("=== Vector search tool FAILED ===", flush=True)
            traceback.print_exc()


    async def full_text_keyword_tool(self, keyword: str, index_name: str, node_type: str) -> str:
        """
        Performs an exact keyword and text token search across indexed fields using Lucene full-text indexes.
        
        Use this tool ONLY when the user's query contains explicit tokens, unique string signatures, 
        or exact phrases that must match exactly. This includes:
        - Specific system error messages or stack traces (e.g., 'NullPointerException', 'TimeoutException').
        - Distinct error codes, hex values, or log codes (e.g., 'ERR_502', '0x7FFF').
        - Exact filenames, function names, database keys, or explicit system tags.
        Do not use this for broad, conceptual, or conversational descriptions (use vector_search_tool for those).


        
        Args:
            keyword_query (str): The explicit keyword, exact phrase, error token, or log signature to locate.
                
        Returns:
            str: A multi-line string listing the top matching ticket keys, titles, and relevancy metrics.
                Example format: 'Matched Ticket: PROJ-404 (Relevancy: 4.8) - Title: "Fix ERR_502 in auth layer"'
        """

        try:

            if node_type not in INDEX_MAP.keys():
                return json.dumps({
                    "status": "error",
                    "search_type": "lexical",
                    "keyword": keyword,
                    "index": "Non existent",
                    "count": 0,
                    "results": []
                }, default=str)

            index_name = INDEX_MAP(node_type)

            cypher_query = f"""
            CALL db.index.fulltext.queryNodes($index_name, $keyword) 
            YIELD node, score
            RETURN 
                elementId(node) AS element_id,
                properties(node) AS props, 
                labels(node) AS labels,
                score
            """

            async with self.driver.session() as session:
                result = await session.run(cypher_query, index_name=index_name, keyword=keyword)
                records = []
                async for row in result:
                    clean_props = {
                        k: v for k, v in row['props'].items() 
                        if k not in {'vector_embedding', 'full_vector_embedding'}
                    }

                    records.append({
                        "element_id": row['element_id'],
                        "labels": row['labels'] or [],
                        "properties": clean_props,
                        "score": row['score']
                    })
                
            json_str_output = json.dumps({
                        "status": "success",
                        "search_type": "lexical",
                        "keyword": keyword,
                        "index": index_name,
                        "count": len(records),
                        "results": records
                    }, default=str)
                
            return json_str_output

        except:
            import traceback
            print("=== Keyword search tool FAILED ===", flush=True)
            traceback.print_exc()


    async def get_ticket_relations_tool(self, ticket_id: str, relation_type: str) -> str:
        """
        Discover direct relationships from a ticket.

        This tool performs relationship discovery only.
        It does NOT retrieve the complete properties/content of connected nodes.

        Each discovered target includes its exact Neo4j element ID.
        When deeper content is required, use that element ID with
        get_node_details_tool.

        Supported relationship types:
            IS_OF_TYPE
            BELONGS_TO_TRACK
            HAS_LABEL
            IMPACTS
            AFFECTS_SYSTEM
            HAS_REPOSITORY_OBJECTS
            HAS_INVESTIGATION
            HAS_COMMENT
        """
        try:
            VALID_RELATIONS = {
                "IS_OF_TYPE",
                "BELONGS_TO_TRACK",
                "HAS_LABEL",
                "IMPACTS",
                "AFFECTS_SYSTEM",
                "HAS_REPOSITORY_OBJECTS",
                "HAS_INVESTIGATION",
                "HAS_COMMENT",
            }

            if relation_type is not None and relation_type not in VALID_RELATIONS:
                return json.dumps({
                    "status": "error",
                    "error": f"Invalid relationship type: {relation_type}",
                    "valid_relationship_types": sorted(VALID_RELATIONS)
                })

            match_rel = f"[r:{relation_type}]" if relation_type else "[r]"

            cypher_query = f"""
            MATCH (t:ticket)
            WHERE t.issue_key = $ticket_id

            MATCH (t)-{match_rel}-(connected)

            RETURN
                t.issue_key AS source_ticket,
                type(r) AS relationship,
                labels(connected) AS target_labels,
                elementId(connected) AS target_element_id,
                (startNode(r) = t) AS is_outgoing

            LIMIT 200
            """

            async with self.driver.session() as session:
                result = await session.run(cypher_query, ticket_id=ticket_id)

                relationships = []

                async for row in result:
                    relationships.append({
                        "source_ticket": row["source_ticket"],
                        "relationship": row["relationship"],
                        "direction": (
                            "outgoing"
                            if row["is_outgoing"]
                            else "incoming"
                        ),
                        "target": {
                            "labels": row["target_labels"] or [],
                            "element_id": row["target_element_id"],
                        }
                    })

            if not relationships:
                return json.dumps({
                    "status": "success",
                    "source_ticket": ticket_id,
                    "relationship_type": relation_type,
                    "relationship_count": 0,
                    "relationships": [],
                    "message": "No relationships found."
                })

            return json.dumps({
                "status": "success",
                "source_ticket": ticket_id,
                "relationship_type": relation_type,
                "relationship_count": len(relationships),
                "relationships": relationships
            }, default=str)
        
        except:
            import traceback
            print("=== Vector search tool FAILED ===", flush=True)
            traceback.print_exc()


    async def traverse_ticket_network_tool(self, ticket_id: str, relation_types: list[str], max_hops: int) -> str:
        """
        Traces deep multi-hop ticket-to-ticket dependency networks, blocker chains, and duplicates.
        
        Use this tool ONLY when you need to follow chains of related tickets across multiple steps 
        (e.g., finding upstream blocker roots, identifying downstream impact cascades, or mapping 
        cloned/duplicated ticket clusters). Do not use this for checking non-ticket entities like 
        comments or system components.
        
        Args:
            ticket_id (str): The unique Jira issue key (e.g., 'PROJ-123') or database ID of the anchor ticket.
            max_hops (int, optional): How deep to trace the graph network. Defaults to 3. 
                Keep between 1 and 5 to prevent token overflow.
            relation_types (list[str], optional): Explicit list of relationship edge types to traverse. 
                Defaults to monitoring: ['BLOCKS', 'DUPLICATES', 'CLONES', 'DEFECTS', 'CONTAINS_WBS_GANTT', 'DISCOVERY_CONNECTED'].
                
        Returns:
            str: A multi-line string mapping out sequential paths showing explicit directionality arrows.
                Example format: 'Chain: PROJ-101 <--[BLOCKS]-- PROJ-99 --[DUPLICATES]--> PROJ-88'
        """

        try:

            DEFAULT_RELATIONS = ["BLOCKS", "DUPLICATES", "CLONES", "DEFECTS", "CONTAINS_WBS_GANTT", "DISCOVERY_CONNECTED"]
            active_relations = relation_types if relation_types else DEFAULT_RELATIONS
            rel_pattern = "|".join(active_relations)

            # We match globally without arrowheads to traverse both incoming and outgoing edges,
            # but we return the raw path to inspect true edge directions in Python.
            cypher_query = f"""
            MATCH (start:ticket)
            WHERE start.issue_key = $ticket_id OR elementId(start) = $ticket_id

            MATCH path = (start)-[:{rel_pattern}*1..{max_hops}]-(related:ticket)
            RETURN path
            LIMIT 50
            """

            async with self.driver.session() as session:
                result = await session.run(cypher_query, ticket_id=ticket_id)
                records = []

                async for row in result:
                    path = row['path']

                    nodes = path.nodes
                    relationships = path.relationships

                    path_list = []

                    for i, rel in enumerate(relationships):

                        path_unit = {
                            "source_element_id": "",
                            "target_element_id": "",
                            "source_key": "",
                            "target_key": "",
                            "relationship": ""
                        }
                        current_node_id = nodes[i].element_id
                        current_node_key = nodes[i].get('issue_key') or "Unknown"

                        next_node_id = nodes[i+1].element_id
                        next_node_key = nodes[i+1].get('issue_key') or "Unknown"
                        
                        if rel.start_node_id == current_node_id:
                            # arrow = f" --[{rel.type}]--> "

                            path_unit["source_element_id"] = current_node_id
                            path_unit["target_element_id"] = next_node_id
                            path_unit["source_key"] = current_node_key
                            path_unit["target_key"] = next_node_key
                            path_unit["relationship"] = rel.type

                            
                        else:
                            # arrow = f" <--[{rel.type}]-- "
                            path_unit["source_element_id"] = next_node_id
                            path_unit["target_element_id"] = current_node_id
                            path_unit["source_key"] = next_node_key
                            path_unit["target_key"] = current_node_key
                            path_unit["relationship"] = rel.type

                        path_list.append(path_unit)
                        
                    # records.append(f"Chain: {chain_str}")
                    records.append(path_list)

            return records or "No ticket networks or dependency chains found."

        except:
            import traceback
            print("=== traverse ticket network tool FAILED ===", flush=True)
            traceback.print_exc()

    async def get_node_details_tool(self, node_identifier: str) -> str:

        """
        Retrieve the complete properties and content of one exact Neo4j node.

        IMPORTANT:
        element_id must be the Neo4j elementId returned by another graph tool.

        Use this tool immediately after a relationship-discovery tool returns
        a target element ID and the user's request requires the contents of
        that target node.
        """

        try: 
            cypher_query = """
            MATCH (n) 
            WHERE elementId(n) = $node_identifier 
            RETURN labels(n) AS node_labels, properties(n) AS props
            LIMIT 1
            """

            async with self.driver.session() as session:
                result = await session.run(cypher_query, node_identifier=node_identifier)
                single_row = await result.single()
                
                if not single_row:
                    return f"Error: No node found in the database with identifier '{node_identifier}'."
                    
                labels_list = single_row['node_labels']
                node_type = ", ".join(labels_list) if labels_list else "Unknown"
                props = single_row['props']
                
                clean_props = {
                    k: v for k, v in props.items() 
                    if k not in {'vector_embedding', 'full_vector_embedding'}
                }

                final_output = {
                    "header": f"=== Details for Node [{node_type}]: {node_identifier} ===",
                    "data": clean_props
                }
                return final_output
        except:
            import traceback
            print("=== Get node details tool FAILED ===", flush=True)
            traceback.print_exc()

    async def get_all_connected_nodes_content_tool(self, ticket_id: str, relation_type: str) -> str:
        """
        Retrieve the complete content and properties of all nodes directly connected
        to the specified ticket through a given relationship type.

        Use this tool when the user needs to inspect, read, audit, summarize, or
        analyze the full collection of related entities, rather than a single node.

        Typical use cases include:
        - All comments or discussion history → HAS_COMMENT
        - All repository/code artifacts → HAS_REPOSITORY_OBJECTS
        - All investigations → HAS_INVESTIGATION
        - Any other supported relationship where the complete set of connected
        nodes is required

        The tool performs bulk content retrieval. It returns each connected node's:
        - Neo4j element ID
        - Node labels/type
        - Relationship type
        - Direction of the relationship (Incoming or Outgoing)
        - Node properties/content

        Use get_ticket_relations_tool when you only need to discover relationships
        or identify connected node IDs.

        Use get_node_details_tool when you need to inspect one specific connected
        node in depth.

        Do not use this tool for simple relationship discovery or when only a
        single known node needs to be retrieved.
        """
        try:
            cypher_query = f"""
            MATCH (t:ticket) WHERE t.issue_key = $ticket_id OR elementId(t) = $ticket_id
            MATCH (t)-[r:{relation_type}]-(connected)
            RETURN 
                labels(connected) AS node_labels, 
                type(r) AS relation,
                properties(connected) AS props,
                elementId(connected) AS node_id,
                CASE 
                    WHEN startNode(r) = t THEN "OUTGOING"
                    ELSE "INCOMING"
                END AS direction                
            """
            
            async with self.driver.session() as session:
                result = await session.run(cypher_query, ticket_id=ticket_id)
                records = {}
                
                async for row in result:
                    props = row.get('props', {})
                    labels = row.get('node_labels', [])
                    relation = row.get('relation', "No Relationships Present")
                    node_id = row.get('node_id', "Node Id Missing")
                    direction = row.get('direction', "Unknown")
                    clean_props = {k: v for k, v in props.items() if k not in {'vector_embedding', 'full_vector_embedding'}}

                    label = labels[0]
                    if label and label not in records:
                        records[label] = []

                    records[label].append({
                        "node_id": node_id,
                        "relation": relation,
                        "direction": direction,
                        "properties": clean_props
                    })
                    
            if not records:
                return f"No items found for relationship '{relation_type}' on ticket '{ticket_id}'."

            output = {
                "header": f"--- Complete list of data for the requested relation types---",
                "data": records
            }
            return output
        
        except:
            import traceback
            print("=== Get all connected nodes content tool FAILED ===", flush=True)
            traceback.print_exc()

    async def count_tickets_by_metadata_tool(self, metadata_value: str, relation_type: str) -> str:
        """
        Counts the total number of unique tickets in the entire graph connected to a specific 
        metadata value, label, track name, or person (e.g., 'SV', 'Tsunoda San').
        
        Use this tool ONLY when the user asks for aggregation, statistics, totals, or counts of tickets 
        associated with a specific track, system, label, user, or reporter category.
        
        Args:
            metadata_value (str): The value of the track, label, or system node to search for (e.g., 'SV').
            relation_type (str, optional): Restricts the count to a specific relationship type. 
                Must be one of: 'BELONGS_TO_TRACK', 'HAS_LABEL', 'IMPACTS', 'AFFECTS_SYSTEM', 'REPORTS', 'WATCHES'.
                If None, counts tickets connected via ANY of these metadata relationships.
                
        Returns:
            str: A summary text breaking down the exact counts found in the database.
        """

        try:
            # Define the group of relationships that link tickets to categories/metadata
            if relation_type:
                rel_clause = f"[r:{relation_type}]"
            else:
                rel_clause = "[r:BELONGS_TO_TRACK|HAS_LABEL|IMPACTS|AFFECTS_SYSTEM|REPORTS|WATCHES]"

            # Cypher query matching inward toward the metadata anchor node
            cypher_query = f"""
            MATCH (connected) 
            WHERE elementId(connected) = $metadata_value 
            OR connected.name = $metadata_value 
            OR connected.issue_key = $metadata_value
            
            MATCH (t:ticket)-{rel_clause}->(connected)
            RETURN type(r) AS rel_type, count(DISTINCT t) AS ticket_count
            """
            
            async with self.driver.session() as session:
                result = await session.run(cypher_query, metadata_value=metadata_value)
                
                breakdown = []
                total_unique_tickets = 0
                
                async for row in result:
                    rel_type = row['rel_type']
                    count = row['ticket_count']
                    breakdown.append(f"- Connected via '{rel_type}': {count} tickets")

                    
                union_query = f"""
                MATCH (connected) 
                WHERE elementId(connected) = $metadata_value OR connected.name = $metadata_value
                MATCH (t:ticket)-{rel_clause}->(connected)
                RETURN count(DISTINCT t) AS total
                """
                union_result = await session.run(union_query, metadata_value=metadata_value)
                single_row = await union_result.single()
                if single_row:
                    total_unique_tickets = single_row['total']

            if total_unique_tickets == 0:
                return f"No tickets found associated with the metadata value '{metadata_value}'."

            output = [
                f"=== Metadata Count Summary for '{metadata_value}' ===",
                f"Total Unique Tickets: {total_unique_tickets}",
                "\nBreakdown by Relationship Type:"
            ]
            output.extend(breakdown)
            final_output = "\n".join(output)
            return final_output

        except:
            import traceback
            print("=== Count tickets tool FAILED ===", flush=True)
            traceback.print_exc()

    async def hybrid_retrieval_tool(self, query_text: str, lexical_scopes: List[str], vector_scopes: List[str], candidate_top_k: int, final_top_k: int) -> str:
        """
        Perform hybrid semantic + lexical retrieval using LlamaIndex
        QueryFusionRetriever with Reciprocal Rank Fusion (RRF).

        The semantic retriever searches the selected Neo4j vector indexes.
        Each selected vector index becomes its own vector retriever, allowing
        RRF to reward entities that rank highly across multiple semantic indexes.

        The lexical side searches the selected Neo4j full-text indexes.
        Each selected full-text index becomes its own lexical retriever, allowing
        RRF to reward entities that rank highly across multiple lexical fields/indexes.

        Index selection MUST be based on both the analyzed intent and the user query.

        IMPORTANT:
        - Choose lexical scopes ONLY from the allowed lexical scopes below.
        - Choose vector scopes ONLY from the allowed vector scopes below.
        - Do NOT invent, modify, or return any other scope or index name.
        - Multiple scopes MAY and SHOULD be selected when broader relevant recall
        is needed.
        - Do NOT select irrelevant scopes merely to increase coverage.
        - The application resolves scopes to the actual Neo4j index names.

        Allowed lexical scopes:
            ticket
            person
            environment
            system
            label
            track
            investigationReport
            repositoryObject
            comment

        Compound lexical scopes:
            person_activity
                Search person, comment, ticket, and investigation-report evidence
                for broad activity/discovery involving a person.

            incident_context
                Search ticket, comment, investigation-report, system, and
                environment evidence for broad incident discovery.

            investigation_context
                Search ticket, comment, and investigation-report evidence for
                investigation, diagnosis, root-cause, and remediation discovery.

            code_investigation
                Search ticket, repository-object, investigation-report, and
                comment evidence for code/repository-related investigation.

            global
                Search across all configured lexical indexes for genuinely
                broad cross-domain discovery when narrower scopes may miss
                relevant evidence.

        Use a compound lexical scope when its broader evidence coverage matches
        the query better than selecting individual scopes.

        Allowed vector scopes:
            ticket
            investigationReport
            repositoryObject
            comment
            global

        Lexical scope selection:
            Select one or more scopes where the user's exact terms, names,
            identifiers, or requested evidence are likely to occur.

            Multiple lexical scopes are encouraged when the query spans multiple
            evidence types. Compound scopes may be preferred when the query is
            naturally cross-domain.

        Vector scope selection:
            Select one or more scopes whose content is semantically relevant to
            the query.

            Prefer specific vector scopes over global when appropriate.
            Use global when the query is genuinely broad or cross-domain and no
            specialized vector scope provides adequate semantic coverage.

        For discovery-oriented queries, hybrid retrieval should normally be the
        FIRST retrieval step.

        Favor high recall during candidate discovery, but keep scope selection
        relevant to the actual query and analyzed intent.

        Examples:

            "Tell me about Saad Ahmed"
                lexical: person_activity
                vector: comment, ticket

            "Find incidents related to database timeout errors"
                lexical: incident_context
                vector: ticket, investigationReport, comment

            "What was the root cause and fix?"
                lexical: investigation_context
                vector: investigationReport

            "Find code changes related to this incident"
                lexical: code_investigation
                vector: repositoryObject, ticket

        Args:
            query_text:
                User's retrieval query. Ideally this should be the actual user
                query, optionally enriched with useful intent information.

            lexical_scopes:
                List of selected lexical scopes. Every value MUST be one of the
                allowed lexical or compound lexical scopes above.

            vector_scopes:
                List of selected vector scopes. Every value MUST be one of the
                allowed vector scopes above.

            candidate_top_k:
                Default: 20
                Number of candidates retrieved from EACH underlying retriever
                before fusion.

            final_top_k:
                Default: 10
                Number of final fused candidates returned.

        Returns:
            JSON string containing the best fused Neo4j candidates.
        """
        try:

            if not query_text or not query_text.strip():
                return json.dumps({
                    "status": "error",
                    "error": "query_text cannot be empty."
                })

            # if not vector_scopes:
            #     return json.dumps({
            #         "status": "error",
            #         "error": "At least one vector full-text index must be supplied."
            #     })

            # if not lexical_scopes:
            #     return json.dumps({
            #         "status": "error",
            #         "error": "At least one lexical full-text index must be supplied."
            #     })

            if candidate_top_k <= 0:
                return json.dumps({
                    "status": "error",
                    "error": "candidate_top_k must be greater than 0."
                })

            if final_top_k <= 0:
                return json.dumps({
                    "status": "error",
                    "error": "final_top_k must be greater than 0."
                })

            lexical_index_names = []

            for scope in lexical_scopes:
                lexical_index_names.extend(
                    LEXICAL_SCOPE_MAP.get(scope, [])
                )

            # Deduplicate while preserving order
            lexical_index_names = list(dict.fromkeys(lexical_index_names))


            vector_index_names = []

            for scope in vector_scopes:
                vector_index_names.extend(
                    VECTOR_SCOPE_MAP.get(scope, [])
                )

            vector_index_names = list(dict.fromkeys(vector_index_names))


            vector_retrievers = [
                Neo4jVectorRetriever(
                    driver=self.driver,
                    embedding_model=self.embedding_model,
                    index_name=index_name,
                    top_k=candidate_top_k,
                )
                for index_name in vector_index_names
            ]
            

            lexical_retrievers = [
                Neo4jFullTextRetriever(
                    driver=self.driver,
                    index_name=index_name,
                    top_k=candidate_top_k,
                )
                for index_name in lexical_index_names
            ]

            retrievers = []

            if lexical_retrievers:
                retrievers.extend(lexical_retrievers)

            if vector_retrievers:
                retrievers.extend(vector_retrievers)

            if not retrievers:
                return json.dumps({
                    "status": "error",
                    "error_type": "NO_RETRIEVERS",
                    "message": (
                        "No valid retrievers were created from the selected lexical "
                        "and vector scopes."
                    ),
                    "lexical_scopes": lexical_scopes,
                    "vector_scopes": vector_scopes,
                })

            fusion_retriever = QueryFusionRetriever(
                retrievers=retrievers,
                num_queries=1,
                similarity_top_k=final_top_k,
                mode="reciprocal_rerank",
                use_async=True,
                verbose=False,
            )

            fused_nodes = await fusion_retriever.aretrieve(
                QueryBundle(query_text)
            )

            candidates = []

            for rank, node_with_score in enumerate(fused_nodes, start=1):

                node = node_with_score.node
                metadata = node.metadata or {}

                element_id = metadata.get("element_id", node.node_id)
                labels_raw = metadata.get("labels", "")
                properties_json = metadata.get("properties_json", "{}")

                try:
                    properties = json.loads(properties_json)
                except Exception:
                    properties = {}

                candidates.append({
                    "rank": rank,
                    "element_id": element_id,
                    "labels": (
                        labels_raw.split(",")
                        if isinstance(labels_raw, str) and labels_raw
                        else []
                    ),
                    "properties": properties,
                    "rrf_score": node_with_score.score,
                })

            return json.dumps(
                {
                    "status": "success",
                    "search_type": "hybrid_rrf",
                    "query": query_text,
                    "vector_indexes": vector_index_names,
                    "lexical_indexes": lexical_index_names,
                    "candidate_top_k": candidate_top_k,
                    "final_top_k": final_top_k,
                    "count": len(candidates),
                    "results": candidates,
                },
                default=str,
                ensure_ascii=False,
            )
        except:
            import traceback
            print("=== Hybrid Retrieval tool FAILED ===", flush=True)
            traceback.print_exc()

    async def execute_dynamic_cypher_queries(self, user_query: str, requirement: str) -> str:
        """
        Generate and execute a constrained, read-only Cypher query to retrieve
        ADDITIONAL graph evidence required to answer the user's query.

        IMPORTANT:
        This is an escalation / investigation tool, NOT the primary retrieval
        mechanism.

        For discovery, search, lookup, or "find anything related to X" queries,
        the agent should first use hybrid_retrieval_tool to identify relevant
        candidate entities/documents.

        Use this tool only when the results already obtained from the retrieval
        tools are insufficient, or when the task requires capabilities that
        standard retrieval does not provide, such as:

        - custom aggregations
        - cross-entity filtering
        - multi-condition graph queries
        - relationship-based filtering
        - node/key/property discovery
        - distinct-value inspection
        - additional supporting evidence

        Do not use this tool as a replacement for hybrid retrieval when the
        task is primarily entity/document discovery.

        The generated query must use only labels, relationships, and properties
        defined in the supplied graph schema and must be strictly read-only.

        User-provided values must be passed through Cypher parameters rather than
        embedded directly into the query.

        Returns a structured JSON result containing the executed query, row count,
        returned columns, and arbitrary Neo4j result rows.
        """
        # """
        # Generate and execute a constrained, read-only Cypher query to retrieve
        # additional graph evidence required to answer the user's query.

        # Use this tool when the existing retrieval tools cannot directly obtain
        # a required piece of information, especially for custom aggregations,
        # cross-entity filtering, multi-condition queries, node/key discovery,
        # distinct-value inspection, or additional supporting evidence.

        # The generated query must use only labels, relationships, and properties
        # defined in the supplied graph schema and must be strictly read-only.

        # User-provided values must be passed through Cypher parameters rather than
        # embedded directly into the query.

        # Returns a structured JSON result containing the executed query, row count,
        # returned columns, and arbitrary Neo4j result rows.
        # """

        cypher_query_prompt = PromptTemplate("""
        You are an expert Neo4j Cypher query generator operating inside a
        production GraphRAG retrieval system.

        Your task is to generate ONE precise, efficient, READ-ONLY Cypher query
        that retrieves exactly the information required by the requirement.

        USER QUERY:
        {user_query}

        RETRIEVAL REQUIREMENT:
        {requirement}

        GRAPH SCHEMA:
        {graph_schema}

        RULES:
        1. Treat the supplied graph schema as the sole source of truth.
        2. Use ONLY node labels, relationship types, properties, and directions
        explicitly present in the schema.
        3. NEVER invent, guess, rename, or assume graph structure.
        4. The query must be strictly read-only.
        5. Only use retrieval/query constructs such as:
        MATCH, OPTIONAL MATCH, WHERE, WITH, UNWIND, RETURN,
        DISTINCT, aggregation, ORDER BY, LIMIT, CASE, COALESCE.
        6. Never use CREATE, MERGE, SET, DELETE, DETACH DELETE, DROP, REMOVE,
        LOAD CSV, or arbitrary write/procedural operations.
        7. User-provided values MUST be represented as parameters using $parameter_name.
        8. Return only information relevant to the requirement.
        9. Prefer the simplest efficient query that satisfies the requirement.
        10. Avoid unnecessary traversals, cartesian products, or large result sets.
        11. Use DISTINCT when required to avoid duplicate entities or counts.
        12. If an exact elementId is supplied, use elementId(node) for exact node
            identification.
        13. If the requirement asks for a count, return the count directly.
        14. If the requirement asks for properties or nodes, return only the
            necessary properties.
        15. Do not provide explanations. Return only the structured CypherModel.

        PROPERTY TYPE SAFETY

        Do not assume all Neo4j properties are scalar values.

        Some properties may contain:
        - LIST<FLOAT>
        - numeric arrays
        - embedding vectors
        - other list/array types

        Embedding/vector properties are internal retrieval artifacts and should
        normally NOT be returned in evidence.

        Never apply toString() to:
        - LIST properties
        - ARRAY properties
        - embedding/vector properties

        When returning arbitrary node properties for evidence, exclude embedding/vector
        properties unless the user explicitly requests them.

        Prefer returning only the specific scalar properties needed to answer the
        requirement.

        For example, prefer:

        RETURN
            n.name AS name,
            n.id AS id,
            n.summary AS summary

        rather than:

        RETURN properties(n)

        or:

        RETURN toString(n.some_property)

        Generate the query and its parameters.
        """)

        try:
            response = self.llm_model.structured_predict(
                CypherModel,
                cypher_query_prompt,
                user_query=user_query,
                requirement=requirement,
                graph_schema=GRAPH_DB_SCHEMA_JSON,
            )
        
            cypher_query = response.cypher.strip()
            parameters = json.loads(response.parameters)

            forbidden = re.compile(
                r"\b(CREATE|MERGE|SET|DELETE|DETACH|DROP|REMOVE|LOAD\s+CSV)\b",
                re.IGNORECASE,
            )

            if forbidden.search(cypher_query):
                return json.dumps({
                    "status": "error",
                    "error": "Generated Cypher contains a forbidden write operation."
                })

            
            async with self.driver.session() as session:

                # Validate query before execution
                explain_result = await session.run(
                    f"EXPLAIN {cypher_query}",
                    **parameters
                )
                await explain_result.consume()

                # Execute
                result = await session.run(
                    cypher_query,
                    **parameters
                )

                rows = await result.data()


            return json.dumps({
                "status": "success",
                "query": cypher_query,
                "parameters": parameters,
                "row_count": len(rows),
                "results": rows,
            }, default=str)

        except Exception as e:
            import traceback
            print("=== execute_dynamic_cypher_queries FAILED ===", flush=True)
            traceback.print_exc()
            return json.dumps({"status": "error", "stage": "unknown", "error": str(e)})