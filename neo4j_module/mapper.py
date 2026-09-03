import json

def clean_datetime(value):

    if value in [None, "", "NaT"]:
        return None

    return value

def build_ticket_params(incident):

    timeline = incident["timeline"]
    lifecycle = incident["lifecycle"]
    content = incident["content"]
    classification = incident["classification"]
    planning = incident["planning"]

    return {

        "issue_key": incident["identity"]["issue_key"],
        "issue_id": incident["identity"]["issue_id"],

        "summary_original": content["summary"]["original"],
        "summary_en": content["summary"]["english"],

        "description_original": content["description"]["original"],
        "description_en": content["description"]["english"],

        "status": lifecycle["status"],
        "status_category": lifecycle["status_category"],
        "resolution": lifecycle["resolution"],
        "priority": lifecycle["priority"],
        "severity": lifecycle["severity"],

        "created_on": clean_datetime(timeline["created_on"]),
        "updated_on": clean_datetime(timeline["updated_on"]),
        "resolved_on": clean_datetime(timeline["resolved_on"]),
        "closed_on": clean_datetime(timeline["closed_on"]),
        "due_on": clean_datetime(timeline["due_on"]),
        "ended_on": clean_datetime(timeline["ended_on"]),
        "first_response_on": clean_datetime(timeline["first_response_on"]),
        "status_category_changed_on":
            clean_datetime(timeline["status_category_changed_on"]),

        "time_in_status": json.dumps(incident["workflow_metrics"]["time_in_status"],ensure_ascii=False),
        "bug_category": classification["bug_category"],
        "bug_type": classification["bug_type"],
        "rca_category": classification["rca_category"],
        "sub_category": classification["sub_category"],

        "business_area": classification["business_area"],

        "issue_raised_fdp":
            incident["system_context"]["issue_raised_fdp"],

        "department":
            incident["organizational_context"]["department"],

        "sprint":
            planning["sprint"],

        "epic_name":
            planning["epic"]["name"],

        "epic_status":
            planning["epic"]["status"],

        "parent_key":
            planning["parent"]["key"]
    }

def build_comment_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "comments": incident["comments"]
    }

def build_person_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "watchers": incident["people"]["watchers"],
        "reporters": incident["people"]["reporter"]
    }

def build_environment_params(incident):

    return{
        "issue_key": incident["identity"]["issue_key"],
        "environments": incident["system_context"]["impacted_environments"]
    }

def build_label_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "labels": incident["classification"]["labels"]
    }

def build_system_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "system": incident["system_context"]["force_system"]
    }   

def build_issue_type_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "issue_type": incident["identity"]["issue_type"]
    }

def build_track_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "track": incident["classification"]["track"]
    }


def build_investigation_report_params(incident):
    
    report = incident.get("investigation_report")

    return {
        "issue_key": incident["identity"]["issue_key"],
        "investigation_summary": report.get("investigation_summary") if report else None,
        "important_findings": report.get("important_findings") if report else None,
        "root_cause": report.get("root_cause") if report else None,
        "resolution": report.get("resolution") if report else None,
        "technical_entities": report.get("technical_entities") if report else None
    }

def build_repository_objects_params(incident):

    repo_objects = incident.get("repo_objects")

    return {
        "issue_key": incident["identity"]["issue_key"],
        "track": repo_objects.get("track") if repo_objects else None,
        "owner": repo_objects.get("owner") if repo_objects else None,
        "objects": repo_objects.get("objects") if repo_objects else None,
        "object_type": repo_objects.get("object_type") if repo_objects else None,
        "repo_changes": repo_objects.get("repo_changes") if repo_objects else None,
        "non_repo_changes": repo_objects.get("non_repo_changes") if repo_objects else None
    }

def build_relation_params(incident):

    return {
        "issue_key": incident["identity"]["issue_key"],
        "inward_blockers": incident["relationships"]["blocks"]["inward"],
        "outward_blockers": incident["relationships"]["blocks"]["outward"],
        "inward_cloners": incident["relationships"]["cloners"]["inward"],
        "outward_cloners": incident["relationships"]["cloners"]["outward"],
        "inward_duplicates": incident["relationships"]["duplicates"]["inward"],
        "outward_duplicates": incident["relationships"]["duplicates"]["outward"],
        "inward_gantts": incident["relationships"]["contains_wbs_gantt"]["inward"],
        "outward_gantts": incident["relationships"]["contains_wbs_gantt"]["outward"],
        "inward_defects": incident["relationships"]["defects"]["inward"],
        "outward_defects": incident["relationships"]["defects"]["outward"],
        "inward_discs": incident["relationships"]["discovery_connected"]["inward"],
        "outward_discs": incident["relationships"]["discovery_connected"]["outward"]
    }

def build_ticket_embedding_params(embeddings):

    return {
        "issue_key": embeddings["issue_key"],
        "embedding": embeddings["ticket_document_embedding"]
    }

def build_investigation_report_embedding_params(embeddings):

    return {
        "issue_key": embeddings["issue_key"],
        "embedding": embeddings["investigation_report_embedding"]
    }

def build_repo_objects_embedding_params(embeddings):

    return {
        "issue_key": embeddings["issue_key"],
        "embedding": embeddings["repo_objects_embedding"]
    }

def build_comment_embedding_params(embeddings):

    return {
        "issue_key": embeddings["issue_key"],
        "comments": embeddings["comments"]
    }

def build_full_doc_embedding_params(embeddings):

    return {
        "issue_key": embeddings["issue_key"],
        "embedding": [float(val) for val in embeddings["vector"]]
    }