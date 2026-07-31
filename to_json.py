from pathlib import Path
import pandas as pd
import regex as re
import math
import ast
import json


class ToJSON:
    def __init__(self, filepath = './preprocessed-exports/preprocessed_data_for_json.csv', outfilefolder = './json-exports', schema_version = 1):
        self.filepath = Path(filepath)
        self.schema_version = schema_version
        Path(outfilefolder).mkdir(parents=True, exist_ok=True)
        self.outfilepath = Path(outfilefolder/Path(f'schema_v{self.schema_version}.json'))
        self.df = pd.read_csv(self.filepath)
        self.json_list = []

    def read_json(self):
        if self.outfilepath:
            with open(self.outfilepath, "r") as f:
                content = json.loads(f.read())
                if content:
                    self.json_list = content

    def main(self):
        self.read_json()
        self.correction_in_json('comments')
        self.convert_to_json()
        #self.print_cols()

    def print_cols(self):
        print(self.df.columns)

    def convert_to_json(self): 
        for index, row in self.df.iterrows():
            kn_block = {
                "identity": {
                    "issue_key": row['Issue key'],
                    "issue_id": row['Issue id'],
                    "issue_type": row['Issue Type']
                },

                "content": {
                    "summary": {
                    "original": row['Summary'] if not pd.isna(row['Summary']) else None,
                    "english": row['Summary_enu'] if not pd.isna(row['Summary_enu']) else None,
                    },
                    "description": {
                    "original": row['Description'] if not pd.isna(row['Description']) else None,
                    "english": row['Description_enu'] if not pd.isna(row['Description_enu']) else None
                    }
                },

                "lifecycle": {
                    "status": row['Status'] if not pd.isna(row['Status']) else None,
                    "status_category": row['Status Category'] if not pd.isna(row['Status Category']) else None,
                    "resolution": row['Resolution'] if not pd.isna(row['Resolution']) else None,
                    "priority": row['Priority'] if not pd.isna(row['Priority']) else None,
                    "severity": row['Custom field (Severity)'] if not pd.isna(row['Custom field (Severity)']) else None
                },

                "timeline": {
                    "created_on": row['Created'] if not pd.isna(row['Created']) else None,
                    "updated_on": row['Updated'] if not pd.isna(row['Updated']) else None,
                    "resolved_on": row['Resolved'] if not pd.isna(row['Resolved']) else None,
                    "closed_on": row['Custom field (Closed Date)'] if not pd.isna(row['Custom field (Closed Date)']) else None,
                    "due_on": row['Due date'] if not pd.isna(row['Due date']) else None,
                    "incident_on": row['Custom field (Incident Date)'] if not pd.isna(row['Custom field (Incident Date)']) else None,
                    "ended_on": row['Custom field (End Date)'] if not pd.isna(row['Custom field (End Date)']) else None,
                    "first_response_on": row['Custom field ([CHART] Date of First Response)'] if not pd.isna(row['Custom field ([CHART] Date of First Response)']) else None,
                    "status_category_changed_on": row['Status Category Changed'] if not pd.isna(row['Status Category Changed']) else None
                },

                "people": {
                    "reporter": row['Reporter'] if not pd.isna(row['Reporter']) else None,
                    "creator": row['Creator'] if not pd.isna(row['Creator']) else None,
                    "watchers": ast.literal_eval(row['Watchers'])
                },

                "classification": {
                    "labels": ast.literal_eval(row['Labels']),
                    "bug_category": row['Custom field (MFTBCFFR Bug Category)'] if not pd.isna(row['Custom field (MFTBCFFR Bug Category)']) else None,
                    "bug_type": row['Custom field (MFTBCFFR Bug Type)'] if not pd.isna(row['Custom field (MFTBCFFR Bug Type)']) else None,
                    "rca_category": row['Custom field (MFTBCFFR RCA Category)'] if not pd.isna(row['Custom field (MFTBCFFR RCA Category)']) else None,
                    "sub_category": row['Custom field (MFTBCFFR Sub Category)'] if not pd.isna(row['Custom field (MFTBCFFR Sub Category)']) else None,
                    "business_area": row['Custom field (MFTBCFFR Business Area)'] if not pd.isna(row['Custom field (MFTBCFFR Business Area)']) else None,
                    "track": row['Custom field (MFTBCFFR Track)'] if not pd.isna(row['Custom field (MFTBCFFR Track)']) else None,
                    "cr_phase": row['Custom field (MFTBCFFR CR Phase)'] if not pd.isna(row['Custom field (MFTBCFFR CR Phase)']) else None
                },

                "system_context": {
                    "force_system": row['Custom field (MFTBCFFR FORCE System)'] if not pd.isna(row['Custom field (MFTBCFFR FORCE System)']) else None,
                    "issue_raised_fdp": row['Custom field (MFTBCFFR Issue Raised FDP)'] if not pd.isna(row['Custom field (MFTBCFFR Issue Raised FDP)']) else None,
                    "impacted_environments": ast.literal_eval(row['Impacted Environments'])
                },

                "organizational_context": {
                    "department": row['Custom field (MFTBCFFR Department)'] if not pd.isna(row['Custom field (MFTBCFFR Department)']) else None,
                },

                "jira_knowledge": {
                    "root_cause_analysis": row['Custom field (FORCE Root Cause Analysis)'] if not pd.isna(row['Custom field (FORCE Root Cause Analysis)']) else None,
                    "action_taken": row['Custom field (MFTBCFFR Action Taken)'] if not pd.isna(row['Custom field (MFTBCFFR Action Taken)']) else None
                },

                "planning": {
                    "sprint": row['Sprint'] if not pd.isna(row['Sprint']) else None,

                    "epic": {
                        "name": row['Custom field (Epic Name)'] if not pd.isna(row['Custom field (Epic Name)']) else None,
                        "status": row['Custom field (Epic Status)'] if not pd.isna(row['Custom field (Epic Status)']) else None
                    },

                    "parent": {
                        "key": row['Parent key'] if not pd.isna(row['Parent key']) else None,
                        "summary": row['Parent summary'] if not pd.isna(row['Parent summary']) else None
                    }
                },

                "relationships": {
                    "blocks": {
                    "inward": ast.literal_eval(row['Inward issue link (Blocks)']),
                    "outward": ast.literal_eval(row['Outward issue link (Blocks)'])
                    },

                    "cloners": {
                    "inward": ast.literal_eval(row['Inward issue link (Cloners)']),
                    "outward": ast.literal_eval(row['Outward issue link (Cloners)'])
                    },

                    "contains_wbs_gantt": {
                    "inward": ast.literal_eval(row['Inward issue link (Contains(WBSGantt))']),
                    "outward": ast.literal_eval(row['Outward issue link (Contains(WBSGantt))'])
                    },

                    "defects": {
                    "inward": ast.literal_eval(row['Inward issue link (Defect)']),
                    "outward": ast.literal_eval(row['Outward issue link (Defect)'])
                    },

                    "discovery_connected": {
                    "inward": ast.literal_eval(row['Inward issue link (Discovery - Connected)']),
                    "outward": ast.literal_eval(row['Outward issue link (Discovery - Connected)'])
                    },

                    "duplicates": {
                    "inward": row['Inward issue link (Duplicate)'],
                    "outward": row['Outward issue link (Duplicate)']
                    }
                },

                "comments": ast.literal_eval(row['Comments_enu']) \
                    if not pd.isna(row['Comments_enu']) \
                    else None,

                "workflow_metrics": {
                    "time_in_status": ast.literal_eval(row['Custom field ([CHART] Time in Status)']) \
                        if not pd.isna(row['Custom field ([CHART] Time in Status)']) \
                        else None
                },

                "provenance": {
                    "source": "jira",
                    "schema_version": "1.0"
                }
            }

            self.json_list.append(kn_block)

        with open(self.outfilepath, "w") as outfile:
            json.dump(self.json_list, outfile, indent=4)

    def correction_in_json(self, entity):

        match entity:
            case 'comments':
                auth_set = set()
                for inc in self.json_list:
                    comment_list = inc["comments"]
                    if comment_list:
                        for c in comment_list:
                            if c["author"] is not None:
                                author = c["author"]
                                words_to_remove = {'and', 'regard', 'regards', 'thank', 'thanks', 'svc'}
                                pattern = r"\b(" + "|".join(words_to_remove) + r")\b\s*"
                                long_texts_to_remove = {
                                    "I'll check PBI on monday    Best ", "I've confirmed its benn changed    Best", \
                                    "PFA Sanity document for the same", "Prod Body Spec 1 Issuemp4", \
                                    "i varidated able to create new INT WO" 
                                }
                                pattern_long_text = r"(" + "|".join(long_texts_to_remove) + r")"
                                pattern_jpn = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
                                pattern_sq_bracket = r"\[[^\]]*\]"
                                pattern_img = r"(?i)(?:!image)?.*?!"
                                pattern_rand_chars = r"[\^\.,]"
                                patterns = r"(-.*)|(↓.*)|(\[.*)|(\*.*)|(\|.*)|(JPN.*)|({.*)|(々.*)|(image.*)|(Scre.*)|(scr.*)|(\xa0)"
                                author = re.sub(pattern_rand_chars, "", author)
                                author = re.sub(patterns, "", author)
                                author = re.sub(pattern_jpn, "", author)
                                author = re.sub(pattern_img, "", author)
                                author = re.sub(pattern_sq_bracket, "", author)
                                author = re.sub(pattern, "", author, flags=re.IGNORECASE)
                                author = re.sub(pattern_long_text, "", author, flags=re.IGNORECASE)
                                author = author.strip()
                                auth_set.add(author)
                                c["author"] = author
                # print(auth_set)
                # print(len(auth_set))


            
to_json = ToJSON()
to_json.main()
#to_json.correction_in_json('comments')