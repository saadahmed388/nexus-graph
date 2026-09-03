"""
Reference copy of the existing FunctionTools implementation, exactly as
provided — this file is NOT part of the graphrag_retrieval package and
nothing in that package redesigns or reimplements what's in here (per the
"do not redesign the existing retrieval tools" requirement). It lives here
purely so example_usage.py has something concrete to import and wrap in a
ToolRegistry.

A few things worth knowing before wiring this up for real (none of these
have been changed here — flagging them so they don't surprise you at
runtime; happy to patch any of these if useful):

  1. vector_search_tool: `json_str_output` is only assigned inside the
     `for row in result:` loop, so a query with zero hits raises
     UnboundLocalError instead of returning an empty result. It also
     iterates `result` with a plain `for`, not `async for` — with the
     async Neo4j driver, session.run() returns an AsyncResult, and
     iterating it synchronously will raise a TypeError.
  2. get_ticket_relations_tool, get_all_connected_nodes_content_tool, and
     the first loop in count_tickets_by_metadata_tool all use
     `for row in result:` as well — same async-iteration issue.
  3. get_all_connected_nodes_content_tool's Cypher has a trailing comma
     right before `LIMIT 200` (after `END AS direction,`), which is
     invalid Cypher syntax. It also references `elementId(n)` in the WHERE
     clause where `n` is never bound (looks like it should be `t`).
  4. count_tickets_by_metadata_tool calls `session.run(union_query, ...)`
     and `.single()` without `await` — both return coroutines rather than
     results with the async driver.
  5. traverse_ticket_network_tool is typed to return `str` but actually
     returns a raw `list` on success (not JSON-serialized) or a plain
     string when nothing is found; its Cypher loop also uses `for row in
     result:` rather than `async for`.

None of this blocks wiring the retrieval engine — graphrag_retrieval's
graph.py already tolerates whichever shape comes back (JSON string, dict,
list, or plain text) via `tools.parse_tool_output`. But #1-#4 will raise at
call time against a real async Neo4j session until fixed, so worth patching
before this goes anywhere near production traffic.
"""
import json

class FunctionTools:
    def __init__(self, driver, embedding_model):
        self.driver = driver
        self.embedding_model = embedding_model

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
            for row in result:

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

    async def full_text_keyword_tool(self, keyword: str, index_name: str) -> str:
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

            for row in result:
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

        DEFAULT_RELATIONS = ["BLOCKS", "DUPLICATES", "CLONES", "DEFECTS", "CONTAINS_WBS_GANTT", "DISCOVERY_CONNECTED"]
        active_relations = relation_types if relation_types else DEFAULT_RELATIONS
        rel_pattern = "|".join(active_relations)

        # We match globally without arrowheads to traverse both incoming and outgoing edges,
        # but we return the raw path to inspect true edge directions in Python.
        cypher_query = f"""
        MATCH (start:ticket)
        WHERE start.issue_key = $ticket_id OR start.id = $ticket_id

        MATCH path = (start)-[:{rel_pattern}*1..{max_hops}]-(related:ticket)
        RETURN path
        LIMIT 50
        """

        async with self.driver.session() as session:
            result = await session.run(cypher_query, ticket_id=ticket_id)
            records = []

            for row in result:
                path = row['path']

                nodes = path.nodes
                relationships = path.relationships
                
                #first_node = nodes[0]
                #chain_str = first_node.get('issue_key') or first_node.get('id') or "Unknown"

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

    async def get_node_details_tool(self, node_identifier: str) -> str:

        """
        Retrieve the complete properties and content of one exact Neo4j node.

        IMPORTANT:
        element_id must be the Neo4j elementId returned by another graph tool.

        Use this tool immediately after a relationship-discovery tool returns
        a target element ID and the user's request requires the contents of
        that target node.
        """

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

        cypher_query = f"""
        MATCH (t:ticket) WHERE t.issue_key = $ticket_id OR elementId(n) = $ticket_id
        MATCH (t)-[r:{relation_type}]-(connected)
        RETURN 
            labels(connected) AS node_labels, 
            type(r) AS relation,
            properties(connected) AS props,
            elementId(connected) AS node_id,
            CASE 
                WHEN startNode(r) = t THEN "OUTGOING"
                ELSE "INCOMING"
            END AS direction,
        LIMIT 200 
        """
        
        async with self.driver.session() as session:
            result = await session.run(cypher_query, ticket_id=ticket_id)
            records = {}
            
            for i, row in enumerate(result, 1):
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
        # Define the group of relationships that link tickets to categories/metadata
        if relation_type:
            rel_clause = f"[r:{relation_type}]"
        else:
            rel_clause = "[r:BELONGS_TO_TRACK|HAS_LABEL|IMPACTS|AFFECTS_SYSTEM|REPORTS|WATCHES]"

        # Cypher query matching inward toward the metadata anchor node
        cypher_query = f"""
        MATCH (connected) 
        WHERE connected.id = $metadata_value 
        OR connected.name = $metadata_value 
        OR connected.issue_key = $metadata_value
        
        MATCH (t:ticket)-{rel_clause}->(connected)
        RETURN type(r) AS rel_type, count(DISTINCT t) AS ticket_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(cypher_query, metadata_value=metadata_value)
            
            breakdown = []
            total_unique_tickets = 0
            
            # Track unique tickets across categories using a quick subquery count or map aggregation
            for row in result:
                rel_type = row['rel_type']
                count = row['ticket_count']
                breakdown.append(f"- Connected via '{rel_type}': {count} tickets")
                
            # Get the absolute unique union count to handle the "OR" logic correctly
            union_query = f"""
            MATCH (connected) 
            WHERE connected.id = $metadata_value OR connected.name = $metadata_value
            MATCH (t:ticket)-{rel_clause}->(connected)
            RETURN count(DISTINCT t) AS total
            """
            union_result = session.run(union_query, metadata_value=metadata_value)
            single_row = union_result.single()
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
