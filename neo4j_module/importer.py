from queries import MERGE_TICKET, MERGE_COMMENT, MERGE_REPORTER_AND_WATCHERS, \
                    MERGE_ENVIRONMENT, MERGE_ISSUE_TYPE, MERGE_TRACK, MERGE_SYSTEM, \
                    MERGE_LABELS, MERGE_INVESTIGATION_REPORT, MERGE_REPOSITORY_OBJECTS, \
                    ESTABLISH_RELATIONS, MERGE_TICKET_EMBEDDINGS, MERGE_INVESTIGATION_REPORT_EMBEDDINGS, \
                    MERGE_REPO_OBJECTS_EMBEDDINGS, MERGE_COMMENT_EMBEDDINGS, MERGE_FULL_DOC_EMBEDDINGS
from mapper import build_ticket_params, build_comment_params, build_environment_params, \
                   build_investigation_report_params, build_issue_type_params, \
                   build_label_params, build_person_params, build_track_params, \
                   build_repository_objects_params, build_system_params, build_relation_params, \
                   build_ticket_embedding_params, build_investigation_report_embedding_params, \
                   build_repo_objects_embedding_params, build_comment_embedding_params, \
                   build_full_doc_embedding_params

def import_ticket(tx, incident):

    tx.run(
        MERGE_TICKET,
        build_ticket_params(incident)    
    )

def import_comments(tx, incident):

    tx.run(
        MERGE_COMMENT,
        build_comment_params(incident)
    )

def import_labels(tx, incident):

    tx.run(
        MERGE_LABELS,
        build_label_params(incident)
    )
    

def import_persons(tx, incident):

    tx.run(
        MERGE_REPORTER_AND_WATCHERS,
        build_person_params(incident)
    )   


def import_environments(tx, incident):

    tx.run(
        MERGE_ENVIRONMENT,
        build_environment_params(incident)
    )

def import_issue_type(tx, incident):

    tx.run(
        MERGE_ISSUE_TYPE,
        build_issue_type_params(incident)
    )

def import_system(tx, incident):

    tx.run(
        MERGE_SYSTEM,
        build_system_params(incident)
    )


def import_track(tx, incident):

    tx.run(
        MERGE_TRACK,
        build_track_params(incident)
    )

def import_investigation_report(tx, incident):

    tx.run(
        MERGE_INVESTIGATION_REPORT,
        build_investigation_report_params(incident)
    )
    

def import_repository_objects(tx, incident):

    tx.run(
        MERGE_REPOSITORY_OBJECTS,
        build_repository_objects_params(incident)
    )

def drop_constraint(tx, con_name):
    tx.run(f"""DROP CONSTRAINT {con_name} IF EXISTS""")

def create_constraint(tx, con_name, node, con_field):

    tx.run(
        f"""CREATE CONSTRAINT {con_name} IF NOT EXISTS
            FOR (n:{node})
            REQUIRE n.{con_field} IS UNIQUE
        """
    )

def create_relationships(tx, incident):

    tx.run(
        ESTABLISH_RELATIONS,
        build_relation_params(incident)
    )

def import_ticket_embeddings(tx, embeddings):

    tx.run(
        MERGE_TICKET_EMBEDDINGS,
        build_ticket_embedding_params(embeddings)
    )

def import_investigation_report_embeddings(tx, embeddings):

    tx.run(
        MERGE_INVESTIGATION_REPORT_EMBEDDINGS,
        build_investigation_report_embedding_params(embeddings)
    )

def import_repo_objects_embeddings(tx, embeddings):

    tx.run(
        MERGE_REPO_OBJECTS_EMBEDDINGS,
        build_repo_objects_embedding_params(embeddings)
    )

def import_comment_embeddings(tx, embeddings):

    tx.run(
        MERGE_COMMENT_EMBEDDINGS,
        build_comment_embedding_params(embeddings)
    )

def import_full_doc_embeddings(tx, embeddings):

    tx.run(
        MERGE_FULL_DOC_EMBEDDINGS,
        build_full_doc_embedding_params(embeddings)
    )

# issue_key = incident["identity"]["issue_key"],
# issue_id = incident["identity"]["issue_id"],

# summary_original = incident["content"]["summary"]["original"],
# summary_en = incident["content"]["summary"]["english"],

# description_original = incident["content"]["description"]["original"],
# description_en = incident["content"]["description"]["english"],

# status = incident["lifecycle"]["status"],
# status_category = incident["lifecycle"]["status_category"],
# resolution = incident["lifecycle"]["resolution"],
# priority = incident["lifecycle"]["priority"],
# severity = incident["lifecycle"]["severity"],

# created_on = incident["timeline"]["created_on"],
# updated_on = incident["timeline"]["updated_on"],
# resolved_on = None if incident["timeline"]["resolved_on"] == "NaT" else incident["timeline"]["resolved_on"],
# closed_on = None if incident["timeline"]["closed_on"] == "NaT" else incident["timeline"]["closed_on"],
# due_on = None if incident["timeline"]["due_on"] == "NaT" else incident["timeline"]["due_on"],
# ended_on = None if incident["timeline"]["ended_on"] == "NaT" else incident["timeline"]["ended_on"],
# first_response_on = incident["timeline"]["first_response_on"],
# status_category_changed_on = incident["timeline"]["status_category_changed_on"],

# time_in_status = incident["workflow_metrics"]["time_in_status"],

# bug_category = incident["classification"]["bug_category"],
# bug_type = incident["classification"]["bug_type"],
# rca_category = incident["classification"]["rca_category"],
# sub_category = incident["classification"]["sub_category"],

# business_area = incident["classification"]["business_area"],
# issue_raised_fdp = incident["system_context"]["issue_raised_fdp"],
# department = incident["organizational_context"]["department"],

# sprint = incident["planning"]["sprint"],
# epic_name = incident["planning"]["epic"]["name"],
# epic_status = incident["planning"]["epic"]["status"],
# parent_key = incident["planning"]["parent"]["key"],