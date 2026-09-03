import asyncio
import atexit
import threading

import streamlit as st

from llama_index_module.retrieval_agent import create_agent
from llama_index_module.reasoning_agent import analyze_query_intent_tool
from llama_index.core.workflow import Context
from llama_index.core.memory import Memory
from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult

st.set_page_config(
    page_title="JIRA Retrieval Assistant",
    page_icon="🤖",
    layout="wide",
)

class AgentRuntime:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        future = asyncio.run_coroutine_threadsafe(self._build_agent(), self.loop)
        self.agent, self.driver = future.result()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _build_agent(self):
        return create_agent()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def close(self):
        async def _close():
            await self.driver.close()

        try:
            self.run(_close())
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)


@st.cache_resource
def get_runtime() -> AgentRuntime:
    runtime = AgentRuntime()
    atexit.register(runtime.close)  # close the driver when the process exits
    return runtime

runtime = get_runtime()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tool_logs" not in st.session_state:
    st.session_state.tool_logs = []


async def _build_context():
        return Context(runtime.agent)

memory = Memory.from_defaults(session_id="jira_chat", token_limit=8000)
retrieval_context = runtime.run(_build_context())


async def process_query(query: str):
    intent = analyze_query_intent_tool(query)

    agent_input = f"""
    USER QUERY:
    {query}

    ANALYZED INTENT:
    {intent}

    Use the analyzed intent to choose the appropriate retrieval
    strategy and answer the user's question.
    """

    handler = runtime.agent.run(
        user_msg=agent_input,
        ctx=retrieval_context,
        memory=memory,
    )

    assistant_response = ""
    tool_logs = []

    async for event in handler.stream_events():
        if isinstance(event, AgentStream):
            assistant_response += event.delta
        elif isinstance(event, ToolCall):
            tool_logs.append(
                {
                    "type": "call",
                    "tool_name": event.tool_name,
                    "args": event.tool_kwargs,
                }
            )
        elif isinstance(event, ToolCallResult):
            tool_logs.append(
                {
                    "type": "result",
                    "tool_name": event.tool_name,
                }
            )

    response = await handler

    if not assistant_response:
        assistant_response = str(response)

    return assistant_response, tool_logs


st.title("🤖 JIRA Retrieval Assistant")
st.caption("Hybrid retrieval + reasoning agent")

chat_col, tool_col = st.columns(2, gap="large")

with chat_col:
    st.subheader("💬 Conversation")
    chat_container = st.container(height=650)

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

with tool_col:
    st.subheader("🔧 Agent Activity")
    tool_container = st.container(height=650)

    with tool_container:
        if not st.session_state.tool_logs:
            st.info("Tool calls and retrieval activity will appear here.")
        else:
            for i, log in enumerate(st.session_state.tool_logs):
                if log["type"] == "call":
                    with st.expander(
                        f"🔹 Tool Call: {log['tool_name']}",
                        expanded=False,
                    ):
                        st.json(log["args"])
                elif log["type"] == "result":
                    st.success(f"✓ Tool completed: {log['tool_name']}")

query = st.chat_input("Ask something about your JIRA incidents...")

if query:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    with chat_col:
        chat_container = st.container(height=650)
        with chat_container:
            for message in st.session_state.messages[:-1]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            with st.chat_message("user"):
                st.markdown(query)

    with st.spinner("Thinking..."):
        assistant_response, tool_logs = runtime.run(process_query(query))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_response,
        }
    )
    st.session_state.tool_logs.extend(tool_logs)
    st.rerun()