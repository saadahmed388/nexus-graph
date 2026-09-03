import json
from pathlib import Path
import time
from openai import OpenAI

class GPTClient:
    def __init__(self):
        self.client = OpenAI()
        self.comment_list = self.read_json()

    def generate(self, prompt):
        response = self.client.responses.create(
            model="gpt-5.6-terra",
            input=prompt,
            reasoning={"effort": "high"} 
        )
        return response.output_text

    def main_pipeline(self):
        issue_list = ['MFTBCFFR-5855', 'MFTBCFFR-4763', 'MFTBCFFR-4754', 'MFTBCFFR-4750', 'MFTBCFFR-4731', 'MFTBCFFR-4724', 'MFTBCFFR-4674', 'MFTBCFFR-4668', 'MFTBCFFR-4648', 'MFTBCFFR-4634', 'MFTBCFFR-4625', 'MFTBCFFR-4621', 'MFTBCFFR-4619', 'MFTBCFFR-4611', 'MFTBCFFR-4608', 'MFTBCFFR-4587', 'MFTBCFFR-4583', 'MFTBCFFR-4570', 'MFTBCFFR-4565', 'MFTBCFFR-4557', 'MFTBCFFR-3592', 'MFTBCFFR-3002', 'MFTBCFFR-2767', 'MFTBCFFR-2764', 'MFTBCFFR-2763', 'MFTBCFFR-2753', 'MFTBCFFR-2749', 'MFTBCFFR-2745', 'MFTBCFFR-2729', 'MFTBCFFR-2728', 'MFTBCFFR-2726', 'MFTBCFFR-2723', 'MFTBCFFR-2722', 'MFTBCFFR-2721', 'MFTBCFFR-2718', 'MFTBCFFR-2704', 'MFTBCFFR-2699', 'MFTBCFFR-2696', 'MFTBCFFR-2680', 'MFTBCFFR-2665', 'MFTBCFFR-2655', 'MFTBCFFR-2654', 'MFTBCFFR-2653', 'MFTBCFFR-2651', 'MFTBCFFR-2650', 'MFTBCFFR-2649', 'MFTBCFFR-2637', 'MFTBCFFR-2625', 'MFTBCFFR-2620', 'MFTBCFFR-2591', 'MFTBCFFR-2586', 'MFTBCFFR-2583', 'MFTBCFFR-2582', 'MFTBCFFR-2579', 'MFTBCFFR-2571', 'MFTBCFFR-2570', 'MFTBCFFR-2554', 'MFTBCFFR-2546', 'MFTBCFFR-2527', 'MFTBCFFR-2516', 'MFTBCFFR-2515', 'MFTBCFFR-2512', 'MFTBCFFR-2507', 'MFTBCFFR-2503', 'MFTBCFFR-2500', 'MFTBCFFR-2499', 'MFTBCFFR-2498', 'MFTBCFFR-2491', 'MFTBCFFR-2490', 'MFTBCFFR-2747', 'MFTBCFFR-2396', 'MFTBCFFR-1103']
        self.call_api_specific(issue_list)
    
    def read_json(self, filepath = "C:/Python Projects/knowledge-graph/json-exports/bug_comments_v1_1.json"):
        filepath = Path(filepath)
        if filepath.is_file():
            try:
                with open(filepath, "r", encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def write_json(self, obj, filepath = None):
        filepath = Path(filepath)
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(obj, f, indent = 4)

    def call_api(self, start, filepath = "C:/Python Projects/knowledge-graph/json-exports/comments_analyzed_v1.json"):

        end = len(self.comment_list)
        analyzed_comm_list = self.read_json(filepath)
        start_time = time.time()

        for i in range(start, end):
            print("Processing Index: ", i)
            comment = self.comment_list[i]
            prompt = self.get_prompt(comment)
            response = self.generate(prompt)
            actual_dict = json.loads(response)
            analyzed_comm_list.append(actual_dict)
            if i%20 == 0:
                self.write_json(analyzed_comm_list, filepath)
                print("Time Taken: ", time.time() - start_time)
        print("Time Taken: ", time.time()-start_time)

    def call_api_specific(self, issue_list, filepath = "C:/Python Projects/knowledge-graph/json-exports/comments_analyzed_v1_1.json"):
    
            analyzed_comm_list = self.read_json(filepath)
            start_time = time.time()
            print(analyzed_comm_list)

            for comm in self.comment_list:
                if comm["issue_key"] in issue_list:
                    print("Processing issue: ", comm["issue_key"])
                    prompt = self.get_prompt(comm["comments"])
                    response = self.generate(prompt)
                    actual_dict = json.loads(response)
                    analyzed_comm_list.append(actual_dict)
                    issue_list.remove(comm["issue_key"])
            
            self.write_json(analyzed_comm_list, filepath)
            print("Time Taken: ", time.time()-start_time)

    def get_prompt(self, comment):
        return f'''
        You are a Senior Enterprise Support Engineer responsible for converting Jira incident discussions into reusable organizational knowledge
        Your task is to analyze the complete chronological comment timeline of a single Jira incident and generate a concise, factual incident analysis.
        The comments represent the complete engineering discussion for the incident. Earlier comments may contain acknowledgements, intermediate investigations, incorrect assumptions or failed hypotheses, while later comments often contain the actual findings and final resolution.
        If both the original and English translation of a comment are available, always use the English translation. Otherwise, use the original comment.
        Your goal is NOT to summarize every comment.
        Your goal is to extract only the engineering knowledge that will help future engineers understand similar incidents.
 
        Instructions:

        - Read every comment in chronological order.
        - Ignore greetings, acknowledgements, signatures, polite language and repetitive information.
        - Do not invent or infer facts that are not supported by the comments.
        - If the root cause or resolution cannot be confidently determined, return null.
        - Preserve exact product names, table names, workflows, environments, systems, error messages and business objects whenever they appear.
        - Keep every field concise and factual.
        - Return ONLY valid JSON.
        - Do not include markdown.
        - Do not include explanations.

        Return the following JSON schema exactly:

        {{
            "issue_key": "",
            "investigation_summary": "",
            "important_findings": [
                "",
                "",
                ""
            ],
            "root_cause": "",
            "resolution": "",
            "technical_entities": [
                ""
            ]
        }}

        Field Guidelines

        issue_key
        - Copy directly from the input.

        investigation_summary
        - 2–4 sentences.
        - Explain the incident, investigation outcome and overall resolution.
        - Do not include greetings or unnecessary chronology.

        important_findings
        - 3–6 concise technical findings.
        - Each finding should represent an important engineering observation.
        - Remove duplicates.
        - Preserve chronological logic where appropriate.

        root_cause
        - The primary technical cause of the incident.
        - Return null if the comments do not clearly establish one.

        resolution
        - The final corrective action that resolved the incident.
        - Return null if unresolved.

        technical_entities
        - Extract every important technical entity explicitly mentioned.
        - Include products, systems, environments, tables, workflows, databases, interfaces, APIs, business objects, modules, technologies and error identifiers.
        - Do not infer entities that are not explicitly present.
        - Return an empty array if none are found.

        Input:

        {comment}
        '''

