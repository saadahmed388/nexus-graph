import json
import asyncio
from llama_index.retrieval_agent import agent
from llama_index.reasoning_agent import analyze_query_intent_tool, resolve_query_entities_tool
from llama_index.schema_and_prompts.system_prompts import system_prompt_large
from llama_index.core.workflow import Context
from llama_index.core.memory import Memory
from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult

async def chat_loop():
    
    retrieval_ctx = Context(agent)

    memory = Memory.from_defaults(
        session_id="jira_chat",
        token_limit=8000,
    )

    while True:

        query = input("\nYou: ").strip()
        if query.lower() in {"exit", "quit"}: break
        
        intent = analyze_query_intent_tool(query)

        agent_input = f"""
        USER QUERY:
        {query}

        ANALYZED INTENT:
        {intent}

        Use the analyzed intent to choose the appropriate retrieval
        strategy and answer the user's question.
        """

        handler = agent.run(user_msg=agent_input, ctx=retrieval_ctx, memory=memory)

        print("\nAssistant: ", end="", flush=True)

        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                print(event.delta, end="", flush=True)

            elif isinstance(event, ToolCall):
                print(f"\n\n[TOOL CALL] {event.tool_name}")
                print(f"[ARGS] {event.tool_kwargs}")

            elif isinstance(event, ToolCallResult):
                print(f"\n[TOOL RESULT] {event.tool_name}")

        response = await handler
        print()