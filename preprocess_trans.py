from pathlib import Path
import pandas as pd
import regex as re
from api.gpt_api import GPTClient
from deep_translator import GoogleTranslator
from tqdm import tqdm
from datetime import datetime, timezone
import math
import ast
import warnings

warnings.filterwarnings("ignore")

gpt_client = GPTClient()
deep_translator = GoogleTranslator(source='ja', target='en')

class PreProcessorTrans:
    def __init__(self, filepath = './preprocessed-exports/preprocessed_data.csv'):
        self.filepath = Path(filepath)
        self.df = pd.read_csv(self.filepath)

    def translate_in_batches_recur(self, start, end, col, batch_size=200, filepath = './preprocessed-exports/preprocessed_data_for_trans.csv'):
        temp_df = pd.read_csv(filepath)
        num_rows = temp_df.shape[0]

        for i in range(start, end):
            print(f"Processing Index {i}")
            if i == num_rows:
                return
            x = str(temp_df.loc[i,col]).strip()
            jp_regex = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
            try:
                if bool(re.search(jp_regex, str(x))):
                    temp_df.loc[i,f"{col}_enu"] = deep_translator.translate(str(x)) if pd.notna(x) and str(x).strip() else ""
            except Exception:
                return

        temp_df.to_csv(filepath, index=False)

        self.translate_in_batches(start+batch_size, end+batch_size, col)

    def translate_in_batches_no_recur(self, start, col, filepath = './preprocessed-exports/preprocessed_data_for_trans.csv'):
            temp_df = pd.read_csv(filepath)
            num_rows = temp_df.shape[0]
    
            for i in range(start, num_rows):
                print(f"Processing Index {i}")
                x = str(temp_df.loc[i,col]).strip()
                jp_regex = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
                try:
                    if bool(re.search(jp_regex, str(x))):
                        temp_df.loc[i,f"{col}_enu"] = deep_translator.translate(str(x)) if pd.notna(x) and str(x).strip() else ""
                except Exception:
                    return
                if i%200 == 0:
                    temp_df.to_csv(filepath, index=False)

    def translate_in_batches_comments(self, start, filepath = './preprocessed-exports/preprocessed_data_for_trans_com.csv'):
        temp_df = pd.read_csv(filepath)
        num_rows = temp_df.shape[0]

        def get_comment_traslation(x):
            new_list = []
            comment_list = ast.literal_eval(x)
            for c in comment_list:
                text = c["text"]
                jp_regex = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
                try:
                    if bool(re.search(jp_regex, str(text))):
                        text_enu = deep_translator.translate(str(text)) if pd.notna(text) and str(text).strip() else ""
                        c["text_enu"] = text_enu
                    new_list.append(c)
                except Exception:
                    return
            return str(new_list)

        for i in range(start, num_rows):
            print(f"Processing Index {i}")

            temp_df.loc[i,"Comments_enu"] = get_comment_traslation(temp_df.loc[i,"Comments"])
            
            if i%200 == 0:
                temp_df.to_csv(filepath, index=False)


    def clean_data(self, filepath = './preprocessed-exports/preprocessed_data_for_trans.csv'):
        temp_df = pd.read_csv(filepath)
        num_rows = temp_df.shape[0]
        col_list = [col for col in temp_df.columns if col.startswith('Unnamed')]
        temp_df = temp_df.drop(columns=col_list)
        temp_df.to_csv(filepath, index=False)
        print(col_list)
        print(num_rows)
        print(temp_df.head())


translate_engine = PreProcessorTrans()
translate_engine.translate_in_batches_comments(0)



        