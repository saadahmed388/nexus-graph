CREATE_TICKET_INDEX="""
CREATE VECTOR INDEX ticket_embedding_index IF NOT EXISTS
FOR (t:ticket)
ON t.vector_embedding
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 3072,
        `vector.similarity_function`: 'cosine'
    }
}
"""

CREATE_INVESTIGATION_REPORT_INDEX="""
CREATE VECTOR INDEX investigation_report_embedding_index IF NOT EXISTS
FOR (ir:investigationReport)
ON ir.vector_embedding
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 3072,
        `vector.similarity_function`: 'cosine'
    }
}
"""

CREATE_REPOSITORY_OBJECTS_INDEX="""
CREATE VECTOR INDEX repository_objects_embedding_index IF NOT EXISTS
FOR (ro:repositoryObjects)
ON ro.vector_embedding
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 3072,
        `vector.similarity_function`: 'cosine'
    }
}
"""

CREATE_COMMENT_INDEX="""
CREATE VECTOR INDEX comment_embedding_index IF NOT EXISTS
FOR (com:comment)
ON com.vector_embedding
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 3072,
        `vector.similarity_function`: 'cosine'
    }
}
"""
CREATE_SEMANITC_SEARCH_INDEX="""
CREATE VECTOR INDEX semantic_search_index IF NOT EXISTS
FOR (n:ticket)
ON n.full_vector_embedding
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 3072,
        `vector.similarity_function`: 'cosine'
    }
}
"""
