CREATE_TICKET_TEXT_INDEX = """
CREATE FULLTEXT INDEX ticket_full_text_index IF NOT EXISTS
FOR (t:ticket)
ON EACH [
    t.issue_id,
    t.summary_original,
    t.summary_en,
    t.description_original,
    t.description_en,
    t.status,
    t.status_category,
    t.resolution,
    t.priority,
    t.severity,
    t.created_on,
    t.updated_on,
    t.resolved_on,
    t.closed_on,
    t.due_on,
    t.ended_on,
    t.first_response_on,
    t.status_category_changed_on,
    t.time_in_status,
    t.bug_category,
    t.bug_type,
    t.rca_category,
    t.sub_category,
    t.business_area,
    t.issue_raised_fdp,
    t.department,
    t.sprint,
    t.epic_name,
    t.epic_status,
    t.parent_key
]
"""

CREATE_INVESTIGATION_REPORT_TEXT_INDEX="""
CREATE FULLTEXT INDEX investigation_report_full_text_index
FOR (ir:investigationReport)
ON EACH [
    ir.investigation_summary,
    ir.important_findings,
    ir.root_cause,
    ir.resolution,
    ir.technical_entities
]
"""

CREATE_REPOSITORY_OBJECTS_TEXT_INDEX="""
CREATE FULLTEXT INDEX repository_objects_full_text_index
FOR (ro:repositoryObjects)
ON EACH [
    ro.track,
    ro.owner,
    ro.objects,
    ro.object_type,
    ro.repo_changes
]
"""

CREATE_COMMENT_TEXT_INDEX = """
CREATE FULLTEXT INDEX comment_full_text_index IF NOT EXISTS
FOR (c:comment)
ON EACH [
    c.timestamp,
    c.author,
    c.comment_original,
    c.comment_english
]
"""

CREATE_PERSON_TEXT_INDEX="""
CREATE FULLTEXT INDEX person_full_text_index
FOR (p:person)
ON EACH [
    p.name
]
"""

CREATE_LABEL_TEXT_INDEX="""
CREATE FULLTEXT INDEX label_full_text_index
FOR (l:label)
ON EACH [
    l.name
]
"""

CREATE_SYSTEM_TEXT_INDEX="""
CREATE FULLTEXT INDEX system_full_text_index
FOR (s:system)
ON EACH [
    s.name
] 
"""

CREATE_ENVIRONMENT_TEXT_INDEX="""
CREATE FULLTEXT INDEX environment_full_text_index
FOR (e:environment)
ON EACH [
    e.name
]
"""

CREATE_TRACK_TEXT_INDEX="""
CREATE FULLTEXT INDEX track_full_text_index
FOR (t:track)
ON EACH [
    t.name
]
"""