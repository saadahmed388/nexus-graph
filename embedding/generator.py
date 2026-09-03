import json
from pathlib import Path
from openai import OpenAI
import time

class GPTEmbeddingClient:
    def __init__(self):
        self.client = OpenAI()

    def generate(self, prompt):
        response = self.client.embeddings.create(
            model="text-embedding-3-large",
            input=prompt
        )
        return response.data[0].embedding

    def main_pipeline(self, doc):
        # self.create_ticket_embedding(doc)
        # self.create_investigation_report_embedding(doc)
        # self.create_repo_objects_embedding(doc)
        # self.create_comments_embedding(doc)
        self.create_full_doc_embedding(doc)
    
    def read_json(self, filepath):
        filepath = Path(filepath)
        if filepath.is_file():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def write_json(self, filepath, rec_list):
        filepath = Path(filepath)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rec_list, f, ensure_ascii=False)

    def create_ticket_embedding(self, doc):
        text = doc["ticket_document"]
        embedding = self.generate(text)
        doc["ticket_document_embedding"] = embedding

    def create_investigation_report_embedding(self, doc):
        text = doc.get("investigation_report", None)
        if text:
            embedding = self.generate(text)
            doc["investigation_report_embedding"] = embedding
            
    def create_repo_objects_embedding(self, doc):
        text = doc.get("repo_objects", None)
        if text:
            embedding = self.generate(text)
            doc["repo_objects_embedding"] = embedding

    def create_comments_embedding(self, doc):
        comments = doc.get("comments", None)
        if comments:
            for c in comments:
                text = c["comment"]
                embedding = self.generate(text)
                c["comment_embedding"] = embedding
            doc["comments"] = comments
    
    def create_full_doc_embedding(self, doc):
        full_doc = doc.get("document", None)
        doc["vector"] = self.generate(full_doc)


    
        
            

