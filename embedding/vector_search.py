def perform_search(session, query_embedding, index_name, limit=5):

    query = f"""
    MATCH (n)
    SEARCH n IN (
        VECTOR INDEX {index_name}
        FOR $query_embedding
        LIMIT $limit
    )
    SCORE AS score

    RETURN n, score
    ORDER BY score DESC
    """

    result = session.run(
        query,
        query_embedding=query_embedding,
        limit=limit
    )

    return [
        {
            "node": record["n"],
            "score": record["score"]
        }
        for record in result
    ]