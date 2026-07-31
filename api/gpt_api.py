from config import config
import os
from openai import OpenAI

class GPTClient:
    def __init__(self):
        self.client = OpenAI()

    def generate(self, prompt):
        response = self.client.responses.create(
            model="gpt-5",
            input=prompt
        )
        return response.output_text
        


    

        
        