from pathlib import Path
import json
from document_creator import create_ticket_document, create_comment_document, \
                             create_investigation_report_document, create_repo_objects_document, \
                             create_full_issue_document

def convert_to_document(infile, outfile):
    infile = Path(infile)
    outfile = Path(outfile)
    outdir = outfile.parent
    outdir.mkdir(parents=True, exist_ok=True)

    with open(infile, "r", encoding="utf-8") as ifile:
        inc_list = json.load(ifile)

    doc_list = []

    for inc in inc_list:
        doc_entity = {}

        issue_key = inc["identity"]["issue_key"]
        doc_entity["issue_key"] = issue_key

        identity = create_ticket_document(inc)
        doc_entity["ticket_document"] = identity

        if inc.get("investigation_report", False):
            investigation_report = create_investigation_report_document(inc)
            doc_entity["investigation_report"] = investigation_report

        if inc.get("repo_objects", False):
            repo_objects = create_repo_objects_document(inc)
            doc_entity["repo_objects"] = repo_objects

        if inc.get("comments", False):
            comments = inc["comments"]
            c_list = []
            for c in comments:
                c_dict = {   
                    "timestamp": c["timestamp"],
                    "comment": create_comment_document(c, issue_key)
                }
                c_list.append(c_dict)
            doc_entity["comments"] = c_list

        doc_list.append(doc_entity)

    with open(outfile, "w", encoding="utf-8") as ofile:
        json.dump(doc_list, ofile, ensure_ascii=False, indent=4)


def convert_to_one_document(infile, outfile):
    infile = Path(infile)
    outfile = Path(outfile)
    outdir = outfile.parent
    outdir.mkdir(parents=True, exist_ok=True)

    with open(infile, "r", encoding="utf-8") as ifile:
        inc_list = json.load(ifile)
    
    doc_list = []

    for inc in inc_list:
        doc_entity = {}
        doc_entity["issue_key"] = inc["identity"]["issue_key"]
        doc_entity["document"] = create_full_issue_document(inc)
        doc_list.append(doc_entity)

    with open(outfile, "w", encoding="utf-8") as ofile:
        json.dump(doc_list, ofile, ensure_ascii=False, indent=4)

    


