MERGE_TICKET = """
MERGE (t:ticket {issue_key: $issue_key})

SET
    t.issue_id                     = $issue_id,

    t.summary_original             = $summary_original,
    t.summary_en                   = $summary_en,

    t.description_original         = $description_original,
    t.description_en               = $description_en,

    t.status                       = $status,
    t.status_category              = $status_category,
    t.resolution                   = $resolution,
    t.priority                     = $priority,
    t.severity                     = $severity,

    t.created_on                   = datetime($created_on),
    t.updated_on                   = datetime($updated_on),
    t.resolved_on                  = CASE WHEN $resolved_on IS NULL THEN NULL ELSE datetime($resolved_on) END,
    t.closed_on                    = CASE WHEN $closed_on IS NULL THEN NULL ELSE datetime($closed_on) END,
    t.due_on                       = CASE WHEN $due_on IS NULL THEN NULL ELSE datetime($due_on) END,
    t.ended_on                     = CASE WHEN $ended_on IS NULL THEN NULL ELSE datetime($ended_on) END,
    t.first_response_on            = CASE WHEN $first_response_on IS NULL THEN NULL ELSE datetime($first_response_on) END,
    t.status_category_changed_on   = CASE WHEN $status_category_changed_on IS NULL THEN NULL ELSE datetime($status_category_changed_on) END,

    t.time_in_status               = $time_in_status,

    t.bug_category                 = $bug_category,
    t.bug_type                     = $bug_type,
    t.rca_category                 = $rca_category,
    t.sub_category                 = $sub_category,

    t.business_area                = $business_area,
    t.issue_raised_fdp             = $issue_raised_fdp,
    t.department                   = $department,

    t.sprint                       = $sprint,
    t.epic_name                    = $epic_name,
    t.epic_status                  = $epic_status,
    t.parent_key                   = $parent_key
"""

MERGE_COMMENT = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $comments as c

MERGE (com:comment {
    issue_key: $issue_key,
    timestamp: c.timestamp
})   

SET
    com.timestamp                    = c.timestamp,
    com.author                       = c.author,
    com.comment_original             = c.text,
    com.comment_english              = c.text_enu
    
MERGE (t)-[:HAS_COMMENT]->(com)
"""

MERGE_REPORTER_AND_WATCHERS = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $reporters as reporter
MERGE (r:person {id: reporter.id})
SET r.name = reporter.name
MERGE (r)-[:REPORTS]->(t) 


UNWIND $watchers as watcher
MERGE (w:person {id: watcher.id})
SET w.name = watcher.name
MERGE (w)-[:WATCHES]->(t)
"""

MERGE_ENVIRONMENT = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $environments as env
MERGE (e:environment {name: env})
MERGE (t)-[:IMPACTS]->(e)
"""

MERGE_ISSUE_TYPE = """
MATCH (t:ticket {issue_key: $issue_key})

MERGE (i:issueType {name: $issue_type})
MERGE (t)-[:IS_OF_TYPE]->(i)
"""

MERGE_TRACK = """
MATCH (t:ticket {issue_key: $issue_key})

WITH t, $track AS track
WHERE track IS NOT NULL
  AND trim(track) <> ''

MERGE (tr:track {name: $track})
MERGE (t)-[:BELONGS_TO_TRACK]->(tr)
"""

MERGE_SYSTEM = """
MATCH (t:ticket {issue_key: $issue_key})

WITH t, $system AS system
WHERE system IS NOT NULL
  AND trim(system) <> ''

MERGE (sys:system {name: $system})
MERGE (t)-[:AFFECTS_SYSTEM]->(sys)
"""

MERGE_LABELS = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $labels as lbl
MERGE (l:label {name: lbl})
MERGE (t)-[:HAS_LABEL]->(l)
"""

MERGE_INVESTIGATION_REPORT = """
MATCH (t:ticket {issue_key: $issue_key})

WITH t, $investigation_summary AS investigation_summary
WHERE investigation_summary IS NOT NULL
 AND TRIM(investigation_summary) <> ''

MERGE (ir:investigationReport {issue_key: $issue_key})
SET
    ir.investigation_summary = $investigation_summary,
    ir.important_findings = $important_findings,
    ir.root_cause = $root_cause,
    ir.resolution = $resolution,
    ir.technical_entities = $technical_entities

MERGE (t)-[:HAS_INVESTIGATION]->(ir)    
"""

MERGE_REPOSITORY_OBJECTS = """
MATCH (t:ticket {issue_key: $issue_key})

WITH t, $track as track
WHERE track IS NOT NULL
    AND TRIM(track) <> ''

MERGE (ro:repositoryObjects {issue_key: $issue_key})
SET
    ro.track = $track,
    ro.owner = $owner,
    ro.objects = $objects,
    ro.object_type = $object_type,
    ro.repo_changes = $repo_changes

MERGE (t)-[:HAS_REPOSITORY_OBJECTS]->(ro) 
"""

RELATE_ISSUE_BLOCKERS = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $inward_blockers as inward_blocker
MATCH (in_blocker:ticket {issue_key: inward_blockers})
MERGE (in_blocker)-[:BLOCKS]->(t)

UNWIND $outward_blockers as outward_blocker
MATCH (out_blocker:ticket {issue_key: outward_blocker})
MERGE (t)-[:BLOCKS]->(out_blocker)

"""

ESTABLISH_RELATIONS = """
MATCH (t:ticket {issue_key: $issue_key})

CALL {
    WITH t
    UNWIND $inward_blockers as inward_blocker
    MATCH (in_blocker:ticket {issue_key: inward_blocker})
    MERGE (in_blocker)-[:BLOCKS]->(t)
}

CALL {
    WITH t
    UNWIND $outward_blockers as outward_blocker
    MATCH (out_blocker:ticket {issue_key: outward_blocker})
    MERGE (t)-[:BLOCKS]->(out_blocker)
}

CALL {
    WITH t
    UNWIND $inward_cloners as inward_cloner
    MATCH (in_cloner:ticket {issue_key: inward_cloner})
    MERGE (in_cloner)-[:CLONES]->(t)
}

CALL {
    WITH t
    UNWIND $outward_cloners as outward_cloner
    MATCH (out_cloner:ticket {issue_key: outward_cloner})
    MERGE (t)-[:CLONES]->(out_cloner)
}

CALL {
    WITH t   
    UNWIND $inward_duplicates as inward_duplicate
    MATCH (in_duplicate:ticket {issue_key: inward_duplicate})
    MERGE (in_duplicate)-[:DUPLICATES]->(t)
}

CALL {
    WITH t
    UNWIND $outward_duplicates as outward_duplicate
    MATCH (out_duplicate:ticket {issue_key: outward_duplicate})
    MERGE (t)-[:DUPLICATES]->(out_duplicate)
}

CALL {
    WITH t
    UNWIND $inward_defects as inward_defect
    MATCH (in_defect:ticket {issue_key: inward_defect})
    MERGE (in_defect)-[:DEFECTS]->(t)
}

CALL {
    WITH t
    UNWIND $outward_defects as outward_defect
    MATCH (out_defect:ticket {issue_key: outward_defect})
    MERGE (t)-[:DEFECTS]->(out_defect)
}

CALL {
    WITH t
    UNWIND $inward_gantts as inward_gantt
    MATCH (in_gantt:ticket {issue_key: inward_gantt})
    MERGE (in_gantt)-[:CONTAINS_WBS_GANTT]->(t)
}

CALL {
    WITH t
    UNWIND $outward_gantts as outward_gantt
    MATCH (out_gantt:ticket {issue_key: outward_gantt})
    MERGE (t)-[:CONTAINS_WBS_GANTT]->(out_gantt)
}

CALL {
    WITH t
    UNWIND $inward_discs as inward_disc
    MATCH (in_disc:ticket {issue_key: inward_disc})
    MERGE (in_disc)-[:DISCOVERY_CONNECTED]->(t)
}

CALL {
    WITH t
    UNWIND $outward_discs as outward_disc
    MATCH (out_disc:ticket {issue_key: outward_disc})
    MERGE (t)-[:DISCOVERY_CONNECTED]->(out_disc)
}
"""

RELATE_ISSUE_CLONERS = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $inward_cloners as inward_cloner
MATCH (in_cloner:ticket {issue_key: inward_cloner})
MERGE (in_cloner)-[:CLONES]->(t)

UNWIND $outward_cloners as outward_cloner
MATCH (out_cloner:ticket {issue_key: outward_cloner})
MERGE (t)-[:CLONES]->(out_cloner)
"""

RELATE_ISSUE_DUPLICATES = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $inward_duplicates as inward_duplicate
MATCH (in_duplicate:ticket {issue_key: inward_duplicate})
MERGE (in_duplicate)-[:DUPLICATES]->(t)

UNWIND $outward_duplicates as outward_duplicate
MATCH (out_duplicate:ticket {issue_key: outward_duplicate})
MERGE (t)-[:DUPLICATES]->(out_duplicate)
"""

RELATE_ISSUE_DEFECTS = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $inward_defects as inward_defect
MATCH (in_defect:ticket {issue_key: inward_defect})
MERGE (in_defect)-[:DEFECTS]->(t)

UNWIND $outward_defects as outward_defect
MATCH (out_defect:ticket {issue_key: outward_defect})
MERGE (t)-[:DEFECTS]->(out_defect)
"""

RELATE_ISSUE_CONTAINING_WBS_GANTT = """
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $inward_gantts as inward_gantt
MATCH (in_gantt:ticket {issue_key: inward_gantt})
MERGE (in_gantt)-[:DUPLICATES]->(t)

UNWIND $outward_duplicates as outward_duplicate
MATCH (out_duplicate:ticket {issue_key: outward_duplicate})
MERGE (t)-[:DUPLICATES]->(out_duplicate)
"""

RELATE_ISSUE_DISCOVERY_CONNECTED = """"
MATCH (t:ticket {issue_key: $issue_key})

UNWIND $inward_discs as inward_disc
MATCH (in_disc:ticket {issue_key: inward_disc})
MERGE (in_disc)-[:DUPLICATES]->(t)

UNWIND $outward_discs as outward_disc
MATCH (out_disc:ticket {issue_key: outward_disc})
MERGE (t)-[:DUPLICATES]->(out_disc)
"""

MERGE_TICKET_EMBEDDINGS = """
MERGE (t:ticket {issue_key: $issue_key})
SET
    t.vector_embedding = $embedding
"""

MERGE_INVESTIGATION_REPORT_EMBEDDINGS = """
MERGE (ir:investigationReport {issue_key: $issue_key})
SET
    ir.vector_embedding = $embedding
"""

MERGE_REPO_OBJECTS_EMBEDDINGS = """
MERGE (ro:repositoryObjects {issue_key: $issue_key})
SET
    ro.vector_embedding = $embedding
"""

MERGE_COMMENT_EMBEDDINGS = """
UNWIND $comments as c

MERGE (com:comment {
    issue_key: $issue_key,
    timestamp: c.timestamp
})
SET
    com.vector_embedding = c.comment_embedding
"""

MERGE_FULL_DOC_EMBEDDINGS = """
MERGE (t:ticket {issue_key: $issue_key})
SET
    t.full_vector_embedding = $embedding
"""