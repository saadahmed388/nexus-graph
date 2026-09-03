import json
from pathlib import Path
from connection import Neo4jConnection
import ijson
from constraints import create_constraints
from importer import import_ticket, import_persons, import_track, import_issue_type, \
                     import_labels, import_environments, import_investigation_report, \
                     import_system, import_comments, import_repository_objects, \
                     drop_constraint, create_relationships, import_comment_embeddings, \
                     import_investigation_report_embeddings, import_repo_objects_embeddings, \
                     import_ticket_embeddings, import_full_doc_embeddings

from vector_indexes import CREATE_TICKET_INDEX, CREATE_COMMENT_INDEX, \
                           CREATE_INVESTIGATION_REPORT_INDEX, CREATE_REPOSITORY_OBJECTS_INDEX, \
                           CREATE_SEMANITC_SEARCH_INDEX

from full_text_indexes import CREATE_COMMENT_TEXT_INDEX, CREATE_INVESTIGATION_REPORT_TEXT_INDEX, \
                              CREATE_REPOSITORY_OBJECTS_TEXT_INDEX, CREATE_TICKET_TEXT_INDEX
                     

def read_json(filepath):
    filepath = Path(filepath)
    if filepath.is_file():
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def run_tickets_import(driver, incidents):

    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_ticket,
                incident
            )

    print("Tickets Imported")

def run_persons_import(driver, incidents):
    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_persons,
                incident
            )

    print("Persons Imported")

def run_labels_import(driver, incidents):
    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_labels,
                incident
            )
    
    print("Labels Imported")

def run_tracks_import(driver, incidents):
    with driver.session() as session:
            for incident in incidents:
                session.execute_write(
                    import_track,
                    incident
                )
    
    print("Tracks Imported")

def run_environments_import(driver, incidents):
    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_environments,
                incident
            )
    
    print("Environments Imported")

def run_comments_import(driver, incidents):
    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_comments,
                incident
            )
     
    print("Comments Imported")

def run_systems_import(driver, incidents):
    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_system,
                incident
            )
    
    print("Systems Imported")
    
def run_issue_types_import(driver, incidents):

    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_issue_type,
                incident
            )
    
    print("Issue Types Imported")
    
def run_investigation_reports_import(driver, incidents):

    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_investigation_report,
                incident
            )
    
    print("Investigation Reports Imported")

def run_repository_reports_import(driver, incidents):

    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                import_repository_objects,
                incident
            )

    print("Repository Objects Imported")

def run_drop_constraint(driver, con_name):
    with driver.session() as session:
        session.execute_write(
            drop_constraint,
            con_name
        )

    print(f"Constraint {con_name} dropped")
    
def run_create_constraint(driver, con_name, node, con_field):
    with driver.session() as session:
        session.execute_write(
            create_constraint,
            con_name,
            node,
            con_field
        )

    print(f"Constraint {con_name} created on node: {node} for field: {con_field}")

def run_create_relationships(driver, incidents):
    with driver.session() as session:
        for incident in incidents:
            session.execute_write(
                create_relationships,
                incident
            )

    print("Relationships successfully established")

def run_ticket_embeddings_import(driver, embedding):
    with driver.session() as session:
        session.execute_write(
            import_ticket_embeddings,
            embedding
        )

def run_investigation_report_embeddings_import(driver, embedding):
    with driver.session() as session:
        session.execute_write(
            import_investigation_report_embeddings,
            embedding
        )
                
def run_repo_object_embeddings_import(driver, embedding):
    with driver.session() as session:
        session.execute_write(
            import_repo_objects_embeddings,
            embedding
        )

def run_comment_embeddings_import(driver, embedding):
    with driver.session() as session:
        session.execute_write(
            import_comment_embeddings,
            embedding
        )

def run_full_doc_embeddings_import(driver, embedding):
    with driver.session() as session:
        session.execute_write(
            import_full_doc_embeddings,
            embedding
        )

def run_embeddings_import(driver, embedding):
    ticket_embedding = embedding.get("ticket_document_embedding", None)
    investigation_report_embedding = embedding.get("investigation_report_embedding", None)
    repo_objects_embedding = embedding.get("repo_objects_embedding", None)
    comments = embedding.get("comments", None)

    if ticket_embedding:
        embedding["ticket_document_embedding"] = [float(val) for val in embedding["ticket_document_embedding"]]
        run_ticket_embeddings_import(driver, embedding)

    if investigation_report_embedding:
        embedding["investigation_report_embedding"] = [float(val) for val in embedding["investigation_report_embedding"]]
        run_investigation_report_embeddings_import(driver, embedding)

    if repo_objects_embedding:
        embedding["repo_objects_embedding"] = [float(val) for val in embedding["repo_objects_embedding"]]
        run_repo_object_embeddings_import(driver, embedding)

    if comments: 
        for c in embedding["comments"]:
            c["comment_embedding"] = [float(val) for val in c["comment_embedding"]]
        run_comment_embeddings_import(driver, embedding)


def run_index_creation(driver, query):
    with driver.session() as session:
        session.run(
            query
        )
    print(f"Index created")

def main():
    neo4j_con = Neo4jConnection()
    driver = neo4j_con.get_driver()

    # filepath = r"C:/Python Projects/knowledge-graph/data/json-exports/schema_v6.json"
    # incidents = read_json(filepath) 

    # filepath = r"C:/Python Projects/knowledge-graph/embedding/doc-file/vector_doc_full_embedded_v1.json"
    
    # with open(filepath, "rb") as f:
    #     records = ijson.items(f, "item")
    #     #print(next(records).keys())
    #     for rec in records:
    #         run_full_doc_embeddings_import(driver, rec)
    #         print(f"{rec['issue_key']} imported")
    #         # print(f"{rec['issue_key']} {rec.keys()}")
    
    # run_tickets_import(driver, incidents)
    # run_create_constraint(driver, "person_id", "person", "id")
    # run_persons_import(driver, incidents)
    # run_labels_import(driver, incidents)
    # run_tracks_import(driver, incidents)
    # run_issue_types_import(driver, incidents)
    # run_environments_import(driver, incidents)
    # run_investigation_reports_import(driver, incidents)
    # run_systems_import(driver, incidents)
    # run_repository_reports_import(driver, incidents)
    # run_comments_import(driver, incidents)
    # run_create_relationships(driver, incidents)

    # run_index_creation(driver, CREATE_TICKET_INDEX)
    # run_index_creation(driver, CREATE_INVESTIGATION_REPORT_INDEX)
    # run_index_creation(driver, CREATE_REPOSITORY_OBJECTS_INDEX)
    # run_index_creation(driver, CREATE_COMMENT_INDEX)
    # run_index_creation(driver, CREATE_SEMANITC_SEARCH_INDEX)

    run_index_creation(driver, CREATE_TICKET_TEXT_INDEX)
    run_index_creation(driver, CREATE_INVESTIGATION_REPORT_TEXT_INDEX)
    run_index_creation(driver, CREATE_REPOSITORY_OBJECTS_TEXT_INDEX)
    run_index_creation(driver, CREATE_COMMENT_TEXT_INDEX)
    
main()

