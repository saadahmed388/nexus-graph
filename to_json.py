from pathlib import Path
import pandas as pd
import regex as re
import math
import ast
import time
import json
from deep_translator import GoogleTranslator

deep_translator = GoogleTranslator(source='ja', target='en')

class ToJSON:
    def __init__(self, filepath = './preprocessed-exports/preprocessed_data_for_json.csv', outfilefolder = './json-exports', schema_version = 1):
        self.filepath = Path(filepath)
        self.schema_version = schema_version
        Path(outfilefolder).mkdir(parents=True, exist_ok=True)
        self.outfilepath = Path(outfilefolder/Path(f'schema_v{self.schema_version}.json'))
        self.df = pd.read_csv(self.filepath)
        self.json_list = []

    def read_json(self):
        if self.outfilepath.is_file():
            with open(self.outfilepath, "r", encoding="utf-8") as f:
                content = json.loads(f.read())
                if content:
                    self.json_list = content

    def main(self):
        self.convert_to_json()
        self.read_json()
        self.correction_in_json('comments')
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
                    "inward": ast.literal_eval(row['Inward issue link (Duplicate)']),
                    "outward": ast.literal_eval(row['Outward issue link (Duplicate)'])
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

        with open(self.outfilepath, "w", encoding="utf-8") as outfile:
            json.dump(self.json_list, outfile, indent=4, ensure_ascii=False)

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
    
    def merge_analyzed_comments(self, \
                                original_file = './json-exports/bug_comments_v1.json', \
                                analyzed_file = './json-exports/comments_analyzed_v1.json', \
                                merged_file = './json-exports/bug_comments_merged_v1.json'):

        original_file = Path(original_file)
        analyzed_file = Path(analyzed_file)
        merged_file = Path(merged_file)

        with open(original_file, "r", encoding="utf-8") as o_file, \
             open(analyzed_file, "r", encoding="utf-8") as a_file, \
             open(merged_file, "w", encoding="utf-8") as m_file:

            original_comment_list = json.load(o_file)
            analyzed_comments = json.load(a_file)

            analyzed_dict = {}

            for c in analyzed_comments:
                if c["investigation_summary"]:
                    analyzed_dict[c["issue_key"]] = {
                        "investigation_summary": c["investigation_summary"],
                        "important_findings": c["important_findings"],
                        "root_cause": c["root_cause"],
                        "resolution": c["resolution"],
                        "technical_entities": c["technical_entities"]
                    }

            for c in original_comment_list:

                if c["issue_key"] in analyzed_dict.keys():
                    c["investigation_report"] = analyzed_dict[c["issue_key"]]
                else:
                    c["investigation_report"] = None

            json.dump(original_comment_list, m_file, indent=4)

    def merge_investigation_report(self, \
                                    schema_file = "./json-exports/schema_v1.json", \
                                    report_file = "./json-exports/bug_comments_merged_v1.json", \
                                    outfile = "./json-exports/schema_v2.json" ):

        schema_file = Path(schema_file)
        report_file = Path(report_file)
        outfile = Path(outfile)

        with open(schema_file, "r", encoding="utf-8") as schema_file, \
                open(report_file, "r", encoding="utf-8") as report_file, \
                open(outfile, "w", encoding="utf-8") as outfile:

            schema_file_list = json.load(schema_file)
            report_file_list = json.load(report_file)

            report_dict = {}

            for r in report_file_list:
                report_dict[r["issue_key"]] = r["investigation_report"]

            for s in schema_file_list:
                if s["identity"]["issue_key"] in report_dict.keys():
                    s["investigation_report"] = report_dict[s["identity"]["issue_key"]]

            json.dump(schema_file_list, outfile, indent=4)

    def convert_release_sheet(self, \
                              filepath = './release-sheet/release_sheet.xlsx', \
                              outfile = './json-exports/release_objects_v1.json'):
        filepath = Path(filepath)
        outfile = Path(outfile)

        release_sheet = pd.read_excel(filepath, sheet_name = None)
        df = pd.concat(release_sheet, ignore_index = True)
        df = df.dropna(axis=1, how='all')
        df = df.rename(columns = {df.columns[1] : "Issue key", df.columns[5] : "Object"})
        columns_to_keep = ["Issue key", 'Track', 'Owner', 'Object', 'Type', 'Changes', 'Non Repository Change']
        df = df[columns_to_keep]  

        obj_list = []

        for index, row in df.iterrows():
            obj = {
                "issue_key" : row["Issue key"] if not pd.isna(row["Issue key"]) else None,
                "track" : row["Track"] if not pd.isna(row["Track"]) else None,
                "owner" : row["Owner"] if not pd.isna(row["Owner"]) else None,
                "objects" : row["Object"] if not pd.isna(row["Object"]) else None,
                "object_type" : row["Type"] if not pd.isna(row["Type"]) else None,
                "repo_changes" : row["Changes"] if not pd.isna(row["Changes"]) else None,
                "non_repo_changes" : row["Non Repository Change"] if not pd.isna(row["Non Repository Change"]) else None,
            }

            obj_list.append(obj)

        with open(outfile, "w", encoding="utf-8") as o_file:
            json.dump(obj_list, o_file, indent = 4)
        
    def merge_release_objects(self, \
                                schema_file = "./json-exports/schema_v2.json", \
                                object_file = "./json-exports/release_objects_v1.json", \
                                outfile = "./json-exports/schema_v3.json" ):
                               
            schema_file = Path(schema_file)
            object_file = Path(object_file)
            outfile = Path(outfile)

            with open(schema_file, "r", encoding="utf-8") as schema_file, \
                 open(object_file, "r", encoding="utf-8") as object_file, \
                 open(outfile, "w", encoding="utf-8") as outfile:

                schema_file_list = json.load(schema_file)
                object_file_list = json.load(object_file)

                object_dict = {}

                for r in object_file_list:
                    object_dict[r["issue_key"]] = {
                        "track": r["track"],
                        "owner": r["owner"],
                        "objects": r["objects"],
                        "object_type": r["object_type"],
                        "repo_changes": r["repo_changes"],
                        "non_repo_changes": r["non_repo_changes"]
                    }

                for s in schema_file_list:
                    if s["identity"]["issue_key"] in object_dict.keys():
                        s["repo_objects"] = object_dict[s["identity"]["issue_key"]]

                json.dump(schema_file_list, outfile, indent=4)

    def find_null_comment_incidents(self, filepath = './json-exports/bug_comments_v1.json'):

        filepath = Path(filepath)
        comments = ''
        with open(filepath, "r") as f:
            comments = json.load(f)
        comm_list = []
        for c in comments:
            if c["comments"] is None:
                comm_list.append(c["issue_key"])
                print(c["issue_key"])
        print(len(comm_list))

    
    def clean_name(self, x):
        match = re.search("[a-zA-Z,\s]+(?=\s*\()", str(x))
        if match is None:
            return x
        x = match.group()
        x_l = x.split(',')
        for l in x_l:
            l = str(l).strip()
        x_l[0], x_l[1] = x_l[1], x_l[0]
        x = "".join(x_l)
        x = x.strip()
        return x

    def clean_text(self, text):
        text = str(text)
        pattern_img = r"(?i)(?:!image)?.*?!"
        pattern_sq_bracket = r"\[[^\]]*\]"
        pattern_xml = r"<.*>"
        text = re.sub(pattern_img, "", text)
        text = re.sub(pattern_sq_bracket, "", text)
        text = re.sub(pattern_xml, "", text)
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        text = text.strip()
        return text
    
    def to_isoformat(self, x):
        return pd.to_datetime(x).isoformat()

    def get_comment_list(self, filepath, issue_key):

        df = pd.read_excel(filepath)
        df = df.drop('Type', axis=1)
        df['Author'] = df['Author'].apply(self.clean_name)
        df['Date'] = df['Date'].apply(self.to_isoformat)
        df['Details'] = df['Details'].apply(self.clean_text)
        comment_list = []
        for index, row in df.iterrows():
            comment = {}
            comment['timestamp'] = row['Date']
            comment['author'] = row['Author']
            comment['text'] = row['Details']

            text = row['Details']
            jp_regex = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
            if bool(re.search(jp_regex, str(text))):
                print(f"Translating for: {issue_key}")
                text_enu = deep_translator.translate(str(text)) if pd.notna(text) and str(text).strip() else ""
                comment["text_enu"] = text_enu
                time.sleep(3)

            comment_list.append(comment)

        return comment_list


    def read_exported_buggy_comments(self, folderpath = './exported-jira-data/inci-no-comments'):
        folderpath = Path(folderpath)
        #first_item = next(folderpath.iterdir(), None)

        # list of bug issues with null comments
        # filepath = Path('./json-exports/bug_comments_v1.json')
        # with open(filepath, "r") as f:
        #     comment_list = json.load(f)
        # null_comment_list = []
        # for c in comment_list:
        #     if c["comments"] is None:
        #         null_comment_list.append(c["issue_key"])

        # Excel Dict for all the excel files to open dynamically
        
        excel_dict = {}
        for f in folderpath.iterdir():
            excel_dict[f.stem[:13]] = f

        schema_v1_1_filepath = Path('./json-exports/schema_v1_1.json')        
        with open(schema_v1_1_filepath, "r", encoding="utf-8") as sch_file:
            inc_list = json.load(sch_file)

        null_comment_list = []
        
        for inc in inc_list:
            issue_key = inc["identity"]["issue_key"]
            if issue_key in null_comment_list:
                filepath = excel_dict[issue_key]
                inc["comments"] = self.get_comment_list(filepath, issue_key)
                with open(schema_v1_1_filepath, "w", encoding="utf-8") as outfile:
                    json.dump(inc_list, outfile, indent=4, ensure_ascii=False)
                null_comment_list.remove(issue_key)
                print(len(null_comment_list))
        
        

        # print(comment_list)
        # for f in folderpath.iterdir():

    def merge_null_bug_comments(self, infile = './json-exports/schema_v1_1.json', \
                                outfile = './json-exports/bug_comments_v1_1.json', \
                                bug_com_file = './json-exports/bug_comments_v1.json'):
        infile = Path(infile)
        bug_com_file = Path(bug_com_file)
        outfile = Path(outfile)

        comment_list = ['MFTBCFFR-5855', 'MFTBCFFR-4763', 'MFTBCFFR-4754', 'MFTBCFFR-4750', 'MFTBCFFR-4731', 'MFTBCFFR-4724', 'MFTBCFFR-4674', 'MFTBCFFR-4668', 'MFTBCFFR-4648', 'MFTBCFFR-4634', 'MFTBCFFR-4625', 'MFTBCFFR-4621', 'MFTBCFFR-4619', 'MFTBCFFR-4611', 'MFTBCFFR-4608', 'MFTBCFFR-4587', 'MFTBCFFR-4583', 'MFTBCFFR-4570', 'MFTBCFFR-4565', 'MFTBCFFR-4557', 'MFTBCFFR-3592', 'MFTBCFFR-3002', 'MFTBCFFR-2767', 'MFTBCFFR-2764', 'MFTBCFFR-2763', 'MFTBCFFR-2753', 'MFTBCFFR-2749', 'MFTBCFFR-2745', 'MFTBCFFR-2729', 'MFTBCFFR-2728', 'MFTBCFFR-2726', 'MFTBCFFR-2723', 'MFTBCFFR-2722', 'MFTBCFFR-2721', 'MFTBCFFR-2718', 'MFTBCFFR-2704', 'MFTBCFFR-2699', 'MFTBCFFR-2696', 'MFTBCFFR-2680', 'MFTBCFFR-2665', 'MFTBCFFR-2655', 'MFTBCFFR-2654', 'MFTBCFFR-2653', 'MFTBCFFR-2651', 'MFTBCFFR-2650', 'MFTBCFFR-2649', 'MFTBCFFR-2637', 'MFTBCFFR-2625', 'MFTBCFFR-2620', 'MFTBCFFR-2591', 'MFTBCFFR-2586', 'MFTBCFFR-2583', 'MFTBCFFR-2582', 'MFTBCFFR-2579', 'MFTBCFFR-2571', 'MFTBCFFR-2570', 'MFTBCFFR-2554', 'MFTBCFFR-2546', 'MFTBCFFR-2527', 'MFTBCFFR-2516', 'MFTBCFFR-2515', 'MFTBCFFR-2512', 'MFTBCFFR-2507', 'MFTBCFFR-2503', 'MFTBCFFR-2500', 'MFTBCFFR-2499', 'MFTBCFFR-2498', 'MFTBCFFR-2491', 'MFTBCFFR-2490', 'MFTBCFFR-2747', 'MFTBCFFR-2396', 'MFTBCFFR-1103']

        with open(infile, "r", encoding="utf-8") as infile,\
             open(bug_com_file, "r", encoding="utf-8") as bug_com_file:
            inc_list = json.load(infile)
            bug_com_file_list = json.load(bug_com_file)

        comment_dict = {}

        for inc in inc_list:
            issue_key = inc["identity"]["issue_key"]
            if issue_key in comment_list:
                comment_dict[issue_key] = inc["comments"]

        for com in bug_com_file_list:
            if com["issue_key"] in comment_list:
                com["comments"] = comment_dict[com["issue_key"]]


        with open(outfile, "w",  encoding="utf-8") as outfile:
            json.dump(bug_com_file_list, outfile, indent=4, ensure_ascii=False)


            
to_json = ToJSON()
#to_json.merge_null_bug_comments()
#to_json.merge_investigation_report()
#to_json.convert_release_sheet()
#to_json.correction_in_json('comments')
# original_file = './json-exports/bug_comments_v1_1.json'
# analyzed_file = './json-exports/comments_analyzed_v1_1.json'
# merged_file = './json-exports/bug_comments_merged_v1_1.json'
# to_json.merge_analyzed_comments(original_file, analyzed_file, merged_file)
#to_json.merge_investigation_report()
#3592 bypassed