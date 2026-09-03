from openai import OpenAI
client = OpenAI()

def embed(query):
    response = client.embeddings.create(
            model="text-embedding-3-large",
            input=query
        )
    return response.data[0].embedding

