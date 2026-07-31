from pathlib import Path
import pandas as pd
import regex as re
from api.gpt_api import GPTClient
from deep_translator import GoogleTranslator
from tqdm import tqdm
from datetime import datetime, timezone
import math
import warnings

warnings.filterwarnings("ignore")

gpt_client = GPTClient()
deep_translator = GoogleTranslator(source='ja', target='en')

class PreProcessor:
    def __init__(self, filepath='./exported-jira-data/Jira.csv'):
        self.filepath = Path(filepath)
        self.df = pd.read_csv(self.filepath, low_memory=False)
        self.df = self.df.dropna(axis=1, how='all')
        self.df_cols_intial = self.df.columns

    def get_df(self):
        return self.df

    def main_pipeline(self):
        self.filter_columns()

        name_cols = [col for col in self.df.columns if col.startswith('Watchers')]
        name_col_list = ['Reporter','Creator']
        name_cols.extend(name_col_list)
        self.clean_names(name_cols)  

        text_cols = ['Summary','Description']      
        self.clean_texts(text_cols)

        fillna_columns = ['Resolution']
        self.column_fillna(fillna_columns)

        date_columns = ['Created', 'Updated', 'Resolved', 'Due date', 'Custom field ([CHART] Date of First Response)', 'Custom field (Incident Date)', 'Custom field (Closed Date)', 'Custom field (End Date)', 'Custom field (Closed Date)', 'Status Category Changed']
        self.convert_to_datetime(date_columns)

        self.normalize_status_in_time()

        label_cols = [col for col in self.df.columns if col.startswith('Labels')]
        watcher_cols = [col for col in self.df.columns if col.startswith('Watchers')]
        impacted_fdp_cols = [col for col in self.df.columns if col.startswith('Custom field (MFTBCFFR Impacted FDPs)')]
        inward_issue_link_blocks_cols = [col for col in self.df.columns if col.startswith('Inward issue link (Blocks)')]
        outward_issue_link_blocks_cols = [col for col in self.df.columns if col.startswith('Outward issue link (Blocks)')]
        inward_issue_link_cloners_cols = [col for col in self.df.columns if col.startswith('Inward issue link (Cloners)')]
        outward_issue_link_cloners_cols = [col for col in self.df.columns if col.startswith('Outward issue link (Cloners)')]
        inward_issue_link_wbsgantt_cols = [col for col in self.df.columns if col.startswith('Inward issue link (Contains(WBSGantt))')]
        outward_issue_link_wbsgantt_cols = [col for col in self.df.columns if col.startswith('Outward issue link (Contains(WBSGantt))')]
        inward_issue_link_defect_cols = [col for col in self.df.columns if col.startswith('Inward issue link (Defect)')]
        outward_issue_link_defect_cols = [col for col in self.df.columns if col.startswith('Outward issue link (Defect)')]
        inward_issue_link_discovery_conn_cols = [col for col in self.df.columns if col.startswith('Inward issue link (Discovery - Connected)')]
        outward_issue_link_discovery_conn_cols = [col for col in self.df.columns if col.startswith('Outward issue link (Discovery - Connected)')]
        inward_issue_link_duplicate_cols = [col for col in self.df.columns if col.startswith('Inward issue link (Duplicate)')]
        outward_issue_link_duplicate_cols = [col for col in self.df.columns if col.startswith('Outward issue link (Duplicate)')]

        self.combine_columns(label_cols, 'Labels')
        self.combine_columns(watcher_cols, 'Watchers')
        self.combine_columns(impacted_fdp_cols, 'Impacted Environments')
        self.combine_columns(inward_issue_link_blocks_cols, 'Inward issue link (Blocks)')
        self.combine_columns(outward_issue_link_blocks_cols, 'Outward issue link (Blocks)')
        self.combine_columns(inward_issue_link_cloners_cols, 'Inward issue link (Cloners)')
        self.combine_columns(outward_issue_link_cloners_cols, 'Outward issue link (Cloners)')
        self.combine_columns(inward_issue_link_wbsgantt_cols, 'Inward issue link (Contains(WBSGantt))')
        self.combine_columns(outward_issue_link_wbsgantt_cols, 'Outward issue link (Contains(WBSGantt))')
        self.combine_columns(inward_issue_link_defect_cols, 'Inward issue link (Defect)')
        self.combine_columns(outward_issue_link_defect_cols, 'Outward issue link (Defect)')
        self.combine_columns(inward_issue_link_discovery_conn_cols, 'Inward issue link (Discovery - Connected)')
        self.combine_columns(outward_issue_link_discovery_conn_cols, 'Outward issue link (Discovery - Connected)')
        self.combine_columns(inward_issue_link_duplicate_cols, 'Inward issue link (Duplicate)')
        self.combine_columns(outward_issue_link_duplicate_cols, 'Outward issue link (Duplicate)')

        comment_cols = [col for col in self.df.columns if col.startswith('Comment')]
        self.process_comments(comment_cols)
        self.combine_columns(comment_cols, 'Comments')
        #self.translate_to_enu('Summary')
        self.export_as_csv()

        return self.df

    def filter_columns(self):
        columns_to_drop = ['Project key', 'Project name', 'Project type', 'Project lead', 'Project lead id', 'Assignee', 'Assignee Id', 'Reporter Id', 'Creator Id', 'Last Viewed', 'Environment', 'Votes', 'Custom field (Approvals)', 'Custom field (Begin Date)', 'Custom field (End Date (migrated 2))', 'Custom field (Epic Color)', 'Custom field (Issue color)', 'Custom field (MFTBCDLS Request Type)', 'Custom field (Start Date (migrated 2))', 'Custom field (TRKD Region)', 'Custom field (Rank)']
        attachment_columns_to_drop = [col for col in self.df_cols_intial if col.startswith('Attachment')]
        watchers_id_columns_to_drop = [col for col in self.df_cols_intial if col.startswith('Watchers Id')]
        self.df = self.df.drop(columns=columns_to_drop, errors='ignore')
        self.df = self.df.drop(columns=attachment_columns_to_drop, errors='ignore')
        self.df = self.df.drop(columns=watchers_id_columns_to_drop, errors='ignore')

    def column_fillna(self, col_list):
        for col in col_list:
            match col:
                case 'Resolution':
                    self.df[col] = self.df[col].fillna('Unresolved')

                case 'Custom field (Epic Name)':
                    self.df[col] = self.df[col].fillna('Not Applicable (Not an EPIC)')

                case 'Custom field (Epic Status)':
                    self.df[col] = self.df[col].fillna('Not Applicable (Not an EPIC)')

    def clean_names(self, col_list):

        def clean_name(x):
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

        for col in col_list:
            self.df[col] = self.df[col].apply(clean_name)

    def clean_texts(self, col_list):
    
        def clean_text(text):
            text = str(text)
            pattern_img = r"(?i)(?:!image)?.*?!"
            pattern_sq_bracket = r"\[[^\]]*\]"
            text = re.sub(pattern_img, "", text)
            text = re.sub(pattern_sq_bracket, "", text)
            text = text.replace("\r\n", "\n")
            text = text.replace("\r", "\n")
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{2,}", "\n", text)
            text = text.strip()
            return text

        for col in col_list:
            self.df[col] = self.df[col].apply(clean_text)

    def convert_to_datetime(self, col_list):

        def to_isoformat(x):
            return x.isoformat()

        for col in col_list:
            self.df[col] = pd.to_datetime(self.df[col])
            self.df[col] = self.df[col].apply(to_isoformat)

    def normalize_status_in_time(self):

        status_id_map = {
            "3" : "In Progress",
            "4" : "Reopened",
            "6" : "Closed",
            "10035" : "To Do",
            "10036" : "Done",
            "10037" : "Active",
            "10038" : "InActive",
            "10039" : "On Hold",
            "10040" : "Under Review",
            "10041" : "In Testing",
            "10053" : "Reject Accepted",
            "10054" : "Rejected",
            "10055" : "Fixed",
            "10056" : "Validated",
            "10057" : "Specification Change"
        }
        #3_*:*_1_*:*_497400097_*|*_10035_*:*_1_*:*_1141757_*|*_10036_*:*_1_*:*_0
        def convert_to_json(x):
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return None
            stat_list = []
            time_blocks = str(x).split('_*|*_')
            for block in time_blocks:
                stats = block.split('_*:*_')
                s = {}
                s['status'] = status_id_map[str(stats[0])]
                s['duration_in_hrs'] = round(float(stats[2]) / 1000 / 3600, 2)
                s['duration_in_days'] = round(float(stats[2]) / 1000 / 3600 / 24, 2)
                stat_list.append(s)
            return stat_list

        self.df['Custom field ([CHART] Time in Status)'] = self.df['Custom field ([CHART] Time in Status)'].apply(convert_to_json)

    def combine_columns(self, col_list, new_col_name):

        def build_list(row):
            return [row[col] for col in col_list if not pd.isna(row[col])]
            
        self.df[new_col_name] = self.df.apply(build_list, axis=1)
        col_list = [col for col in col_list if col != new_col_name]
        self.df = self.df.drop(columns = col_list, errors='coerce')     

    def process_comments(self, col_list):

        def find_author(x):
            if pd.isna(x) or not isinstance(x, str):
                return None

            pattern = r"(?i)(?:(?:best\s+)?regards?|thanks?)\s*,\s*(.*)$"
            match = re.search(pattern, x, re.DOTALL)
            author = None
            if match:
                author = match.group(1)
                author = author.replace('\r',' ').replace('\n',' ')
                author = author.strip()
                return author

        def clean_comments(x):

            pattern = r"(?i)(?:dear|hi)?\s*\[[^\]]*\]\s*(?:san)?\s*,?\s*"
            pattern_img = r"(?i)(?:!image)?.*?!"
            pattern_sq_bracket = r"\[[^\]]*\]"
            text = re.sub(pattern, "", x, count=1)
            text = re.sub(pattern_img, "", text)
            text = re.sub(pattern_sq_bracket, "", text)
            text = text.replace("\r\n", "\n")
            text = text.replace("\r", "\n")
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{2,}", "\n", text)
            text = text.strip()
            return text

        def convert_to_json(x):
            if x is None or (isinstance(x,float) and math.isnan(x)):
                return None
            data_list = str(x).split(";")
            timestamp = pd.to_datetime(data_list[0]).isoformat()
            author = find_author(data_list[2])
            text = clean_comments(data_list[2])
            return {
                "timestamp" : timestamp,
                "author" : author,
                "text" : text
            }

        for col in col_list:
            self.df[col] = self.df[col].apply(convert_to_json)

    def translate_to_enu(self, col):

        def translate(x):
            x = str(x).strip()
            jp_regex = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
            if bool(re.search(jp_regex, str(x))):
                return deep_translator.translate(str(x)) if pd.notna(x) and str(x).strip() else ""
            return x
    
        new_col_name = f"{col}_enu"
        self.df[new_col_name] = self.df[col].apply(translate)

    def export_as_csv(self, filepath = './preprocessed-exports', filename = 'preprocessed_data.csv'):
        filepath = Path(filepath)
        filepath.mkdir(exist_ok=True)
        self.df.to_csv(filepath/filename, index=False)
        self.df.to_csv(filepath/'preprocessed_data_for_trans.csv', index=False)


preprocessor = PreProcessor('./preprocessed-exports/preprocessed_data_for_json.csv')
preprocessor.convert_to_datetime(['Status Category Changed'])
df = preprocessor.get_df()
df = df.drop(columns=['Unnamed: 0'])
df.to_csv('./preprocessed-exports/preprocessed_data_for_json.csv', index=False)

print(df.shape, '\n')
print(df['Summary'], '\n')
#print(df['Resolution'].value_counts(), '\n')
#print(df['Watchers'].value_counts(), '\n')
#print(df['Labels'].value_counts(), '\n')
#print(df['Created'].value_counts(), '\n')
#print(df['Custom field (Epic Status)'].value_counts(), '\n')
#print(df['Custom field ([CHART] Time in Status)'].value_counts(), '\n')
#print(df['Created'].dtype, '\n')
#print(df['Labels'].value_counts(), '\n')
