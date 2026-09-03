def add_value(field_name, actual, lines, default=None):
    value = default if actual is None else actual
    if value is not None:
        lines.append(f"{field_name}: {value}")

def create_ticket_document(incident): 
    parts = []
    add_value("Ticket key",incident["identity"]["issue_key"], parts)
    add_value("Ticket type", incident["identity"]["issue_type"], parts)
    add_value("Ticket Summary", incident["content"]["summary"].get("english"), parts, incident["content"]["summary"].get("original"))
    add_value("Ticket Description", incident["content"]["description"].get("english"), parts, incident["content"]["description"].get("original"))
    add_value("Status", incident["lifecycle"]["status"], parts)
    add_value("Status Category", incident["lifecycle"]["status_category"], parts)
    add_value("Resolution", incident["lifecycle"]["resolution"], parts)
    add_value("Priority", incident["lifecycle"]["priority"], parts)
    add_value("Severity", incident["lifecycle"]["severity"], parts)
    add_value("Created on", incident["timeline"]["created_on"], parts)
    add_value("Updated on", incident["timeline"]["updated_on"], parts)
    add_value("Resolved on", incident["timeline"]["resolved_on"], parts)
    add_value("Closed on", incident["timeline"]["closed_on"], parts)
    add_value("Due on", incident["timeline"]["due_on"], parts)
    add_value("Incident on", incident["timeline"]["incident_on"], parts)
    add_value("Ended on", incident["timeline"]["ended_on"], parts)
    add_value("First response on", incident["timeline"]["first_response_on"], parts)
    add_value("Status category changed on", incident["timeline"]["status_category_changed_on"], parts)
    add_value("Reported by", incident["people"]["reporter"][0]["name"], parts)
    add_value("Created by", incident["people"]["creator"][0]["name"], parts)
    add_value("Watched by", ", ".join(w["name"] for w in incident["people"]["watchers"]), parts)
    add_value("Labelled as ", ", ".join(l for l in incident["classification"]["labels"]), parts)
    add_value("Bug Category", incident["classification"]["bug_category"], parts)
    add_value("Bug Type", incident["classification"]["bug_type"], parts)
    add_value("RCA Category", incident["classification"]["rca_category"], parts)
    add_value("Sub Category", incident["classification"]["sub_category"], parts)
    add_value("Business Area", incident["classification"]["business_area"], parts)
    add_value("Track", incident["classification"]["track"], parts)
    add_value("CR Phase", incident["classification"]["cr_phase"], parts)
    add_value("Affected System", incident["system_context"]["force_system"], parts)
    add_value("Issue raised in environment", incident["system_context"]["issue_raised_fdp"], parts)
    add_value("Impacted Environments ", ", ".join(e for e in incident["system_context"]["impacted_environments"]), parts)
    add_value("Sprint", incident["planning"]["sprint"], parts)
    add_value("Epic Name", incident["planning"]["epic"]["name"], parts)
    add_value("Epic Status", incident["planning"]["epic"]["status"], parts)
    add_value("Parent Issue", incident["planning"]["parent"]["key"], parts)

    doc = "\n".join(parts)
    return doc


def create_comment_document(comment, issue_key):
    parts = []

    add_value("Issue Key", issue_key, parts)
    add_value("Timestamp", comment["timestamp"], parts)
    add_value("Author", comment.get("author"), parts)
    add_value("Comment", comment.get("text_enu"), parts, comment.get("text"))

    doc = "\n".join(parts)
    return doc

def create_investigation_report_document(incident):
    parts = []

    add_value("Issue Key", incident["identity"]["issue_key"], parts)
    add_value("Investigation Summary", incident["investigation_report"]["investigation_summary"], parts)
    add_value("Important Findings", incident["investigation_report"]["important_findings"], parts)
    add_value("Root Cause", incident["investigation_report"]["root_cause"], parts)
    add_value("Resolution", incident["investigation_report"]["resolution"], parts)
    add_value("Technical Entities", incident["investigation_report"]["technical_entities"], parts)

    doc = "\n".join(parts)
    return doc

def create_repo_objects_document(incident):
    parts = []

    add_value("Issue Key", incident["identity"]["issue_key"], parts)
    add_value("Track", incident["repo_objects"]["track"], parts)
    add_value("Owner", incident["repo_objects"]["owner"], parts)
    add_value("Objects", incident["repo_objects"]["objects"], parts)
    add_value("Object Type", incident["repo_objects"]["object_type"], parts)
    add_value("Repository Changes", incident["repo_objects"]["repo_changes"], parts)
    add_value("Non Repository Changes", incident["repo_objects"]["non_repo_changes"], parts)

    doc = "\n".join(parts)
    return doc

def create_full_issue_document(incident):

    parts = []
    add_value("Ticket key",incident["identity"]["issue_key"], parts)

    parts.append("Ticket Identity")

    add_value("Ticket type", incident["identity"]["issue_type"], parts)
    add_value("Ticket Summary", incident["content"]["summary"].get("english"), parts, incident["content"]["summary"].get("original"))
    add_value("Ticket Description", incident["content"]["description"].get("english"), parts, incident["content"]["description"].get("original"))
    add_value("Status", incident["lifecycle"]["status"], parts)
    add_value("Status Category", incident["lifecycle"]["status_category"], parts)
    add_value("Resolution", incident["lifecycle"]["resolution"], parts)
    add_value("Priority", incident["lifecycle"]["priority"], parts)
    add_value("Severity", incident["lifecycle"]["severity"], parts)
    add_value("Created on", incident["timeline"]["created_on"], parts)
    add_value("Updated on", incident["timeline"]["updated_on"], parts)
    add_value("Resolved on", incident["timeline"]["resolved_on"], parts)
    add_value("Closed on", incident["timeline"]["closed_on"], parts)
    add_value("Due on", incident["timeline"]["due_on"], parts)
    add_value("Incident on", incident["timeline"]["incident_on"], parts)
    add_value("Ended on", incident["timeline"]["ended_on"], parts)
    add_value("First response on", incident["timeline"]["first_response_on"], parts)
    add_value("Status category changed on", incident["timeline"]["status_category_changed_on"], parts)
    add_value("Reported by", incident["people"]["reporter"][0]["name"], parts)
    add_value("Created by", incident["people"]["creator"][0]["name"], parts)
    add_value("Watched by", ", ".join(w["name"] for w in incident["people"]["watchers"]), parts)
    add_value("Labelled as ", ", ".join(l for l in incident["classification"]["labels"]), parts)
    add_value("Bug Category", incident["classification"]["bug_category"], parts)
    add_value("Bug Type", incident["classification"]["bug_type"], parts)
    add_value("RCA Category", incident["classification"]["rca_category"], parts)
    add_value("Sub Category", incident["classification"]["sub_category"], parts)
    add_value("Business Area", incident["classification"]["business_area"], parts)
    add_value("Track", incident["classification"]["track"], parts)
    add_value("CR Phase", incident["classification"]["cr_phase"], parts)
    add_value("Affected System", incident["system_context"]["force_system"], parts)
    add_value("Issue raised in environment", incident["system_context"]["issue_raised_fdp"], parts)
    add_value("Impacted Environments ", ", ".join(e for e in incident["system_context"]["impacted_environments"]), parts)
    add_value("Sprint", incident["planning"]["sprint"], parts)
    add_value("Epic Name", incident["planning"]["epic"]["name"], parts)
    add_value("Epic Status", incident["planning"]["epic"]["status"], parts)
    add_value("Parent Issue", incident["planning"]["parent"]["key"], parts)

    if incident.get("investigation_report", None):
        parts.append("Investigation Report")
        add_value("Investigation Summary", incident["investigation_report"]["investigation_summary"], parts)
        add_value("Important Findings", incident["investigation_report"]["important_findings"], parts)
        add_value("Root Cause", incident["investigation_report"]["root_cause"], parts)
        add_value("Resolution", incident["investigation_report"]["resolution"], parts)
        add_value("Technical Entities", incident["investigation_report"]["technical_entities"], parts)

    if incident.get("repo_objects", None):
        parts.append("Repository Objects")
        add_value("Track", incident["repo_objects"]["track"], parts)
        add_value("Owner", incident["repo_objects"]["owner"], parts)
        add_value("Objects", incident["repo_objects"]["objects"], parts)
        add_value("Object Type", incident["repo_objects"]["object_type"], parts)
        add_value("Repository Changes", incident["repo_objects"]["repo_changes"], parts)
        add_value("Non Repository Changes", incident["repo_objects"]["non_repo_changes"], parts)

    # if incident.get("comments", None) and len(incident["comments"])>0:
    #     parts.append("Comments")
    #     for c in incident["comments"]:
    #         add_value("Timestamp", c["timestamp"], parts)
    #         add_value("Author", c.get("author"), parts)
    #         add_value("Comment", c.get("text_enu"), parts, c.get("text"))

    doc = "\n".join(parts)
    return doc
    




