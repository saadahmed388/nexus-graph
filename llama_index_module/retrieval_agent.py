import os
from typing import List
from llama_index.core import Settings
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAIResponses
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index_module.schema_and_prompts.system_prompts import system_prompt_large_v2
from llama_index_module.toolsets.function_tools import FunctionTools
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

env_path = r"C:/Python Projects/knowledge-graph/.env"
load_dotenv(dotenv_path=env_path)

NEO4J_URI = os.environ["NEO4J_LOCAL_URI"]
NEO4J_USER = os.environ["NEO4J_LOCAL_USER"]
NEO4J_PASSWORD = os.environ["NEO4J_LOCAL_PASS"]
driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large", dimensions=3072)

Settings.llm = llm = OpenAIResponses(
    model="gpt-5.6-terra", 
    temperature=0.0, 
    strict=True, 
    reasoning_options={
        "effort": "xhigh",
        "summary": "auto",
    }
)

embedding_model = Settings.embed_model
llm_model = Settings.llm
system_prompt = system_prompt_large_v2

driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

function_tools = FunctionTools(driver, embedding_model, llm_model)

tools = [
    FunctionTool.from_defaults(async_fn=function_tools.hybrid_retrieval_tool),
    FunctionTool.from_defaults(async_fn=function_tools.get_ticket_relations_tool),
    FunctionTool.from_defaults(async_fn=function_tools.traverse_ticket_network_tool),
    FunctionTool.from_defaults(async_fn=function_tools.get_node_details_tool),
    FunctionTool.from_defaults(async_fn=function_tools.get_all_connected_nodes_content_tool),
    FunctionTool.from_defaults(async_fn=function_tools.execute_dynamic_cypher_queries),
]

agent = FunctionAgent(
    tools=tools,
    llm=llm_model,
    verbose=True,
    system_prompt=system_prompt
)

def create_agent():
        
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    function_tools = FunctionTools(driver, embedding_model, llm_model)

    tools = [
        FunctionTool.from_defaults(async_fn=function_tools.hybrid_retrieval_tool),
        FunctionTool.from_defaults(async_fn=function_tools.get_ticket_relations_tool),
        FunctionTool.from_defaults(async_fn=function_tools.traverse_ticket_network_tool),
        FunctionTool.from_defaults(async_fn=function_tools.get_node_details_tool),
        FunctionTool.from_defaults(async_fn=function_tools.get_all_connected_nodes_content_tool),
        FunctionTool.from_defaults(async_fn=function_tools.execute_dynamic_cypher_queries),
    ]

    agent = FunctionAgent(
        tools=tools,
        llm=llm_model,
        verbose=True,
        system_prompt=system_prompt
    )

    return agent, driver

