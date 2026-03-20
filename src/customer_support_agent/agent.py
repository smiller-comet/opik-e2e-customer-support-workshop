"""
Customer support agent with SQL and RAG capabilities.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import litellm
import pandas as pd
from opik import track, opik_context
from opik.integrations.litellm import track_completion

from customer_support_agent.utils.config import get_config
from customer_support_agent.prompts import (
    get_router_prompt,
    get_database_schema,
    CHAT_SYSTEM_PROMPT,
    SQL_SYSTEM_PROMPT,
    SQL_TOOL_DESCRIPTION,
    RAG_SYSTEM_PROMPT,
    RAG_TOOL_DESCRIPTION,
)

# --- COLAB/LINUX FIX ---
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# Load model config from config.yml at import time (no API key validation)
_config = get_config()

# Database schema (static, no dependencies)
database_schema = get_database_schema()

# --- Lazily initialized resources ---
_model_name: str | None = None
_completion = None  # litellm.completion wrapped with Opik tracking
_conn: sqlite3.Connection | None = None
_collection = None


def init_agent(
    api_key: str,
    provider: str,
    model_name: str,
    db_path: Path,
    chroma_path: Path,
    opik_project_name: str = "Ohm Sweet Ohm Support Agent",
) -> None:
    """Initialize agent resources.

    Args:
        api_key: API key for the chosen provider (OpenAI or Anthropic).
        provider: "openai" or "anthropic".
        model_name: Model identifier, e.g. "gpt-4o" or "claude-sonnet-4-6".
        db_path: Path to the SQLite database file.
        chroma_path: Path to the ChromaDB directory.
        opik_project_name: Opik project name where traces will appear.

    Raises:
        FileNotFoundError: If either database has not been created yet.
    """
    global _model_name, _completion, _conn, _collection

    # Set provider API key for LiteLLM
    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key

    # Set Opik project name and force a fresh Opik client so @track decorators
    # pick up the new value. The client is lru_cache'd, so we must clear it
    # before the next trace is created.
    os.environ["OPIK_PROJECT_NAME"] = opik_project_name
    from opik.api_objects.opik_client import get_client_cached

    get_client_cached.cache_clear()

    # Allow LiteLLM to drop/adjust unsupported params per provider (e.g. Anthropic tool_choice rules)
    litellm.modify_params = True

    # Wrap litellm.completion with Opik tracking
    _completion = track_completion(project_name=opik_project_name)(litellm.completion)

    _model_name = model_name

    # SQLite
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found at: {db_path}\n" "Run `make create-db` to generate it.")
    _conn = sqlite3.connect(f"file:{db_path}?mode=rw", uri=True, check_same_thread=False)

    # ChromaDB with local embedding model (no API key required)
    if not chroma_path.exists():
        raise FileNotFoundError(f"ChromaDB not found at: {chroma_path}\n" "Run `make build-vector-db` to generate it.")
    chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    _collection = chroma_client.get_collection(
        name="ohm_policies",
        embedding_function=DefaultEmbeddingFunction(),
    )


def is_initialized() -> bool:
    """Return True if init_agent() has been called successfully."""
    return _model_name is not None and _completion is not None and _conn is not None and _collection is not None


def _msg_to_dict(msg) -> dict:
    """Convert a completion message object to a plain dict for the messages list.

    Works with both OpenAI and LiteLLM response message objects.
    """
    if isinstance(msg, dict):
        return msg
    d: dict = {"role": msg.role, "content": msg.content}
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


# 1. TOOLS


@track(type="tool")
def run_sql_query(query: str) -> str:
    """Run a SQL query against the database."""
    if _conn is None:
        raise RuntimeError("Agent not initialized. Call init_agent() first.")
    try:
        if "DROP" in query.upper() or "DELETE" in query.upper():
            return "Error: Read-only access."
        df = pd.read_sql_query(query, _conn)
        if df.empty:
            return "Query returned no results."
        try:
            return df.to_markdown(index=False)
        except ImportError:
            return df.to_string(index=False)
    except Exception as e:
        return f"SQL Error: {str(e)}"


@track(type="tool")
def look_up_policy(query: str) -> str:
    """Look up policy information from the RAG knowledge base."""
    if _collection is None:
        raise RuntimeError("Agent not initialized. Call init_agent() first.")
    results = _collection.query(query_texts=[query], n_results=3)
    docs = results["documents"][0]
    if not docs:
        return "No relevant policies found."
    return "\n\n---\n\n".join(docs)


# 2. ROUTER


@track()
def route_user_request(user_question: str, history: list) -> str:
    """Route user question to appropriate workflow.

    History is included so the router can correctly classify short follow-up
    messages (e.g. an order ID typed in response to being asked for one).
    """
    routing_prompt = get_router_prompt(user_question)
    # Include up to the last 4 messages (2 turns) so the router has context
    messages = [m for m in history[-4:] if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": routing_prompt})
    response = _completion(
        model=_model_name,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content.strip().upper()


# 3. WORKFLOWS


@track
def run_chat_workflow(question: str, history: list) -> str:
    """Handle general chat questions."""
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = _completion(
        model=_model_name,
        messages=messages,
        temperature=_config.model.temperature,
        max_tokens=_config.model.max_tokens,
    )
    return response.choices[0].message.content


@track
def run_sql_workflow(question: str, history: list) -> str:  # noqa: C901
    """Handle SQL database queries."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_sql_query",
                "description": SQL_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": f"SQL Query. Schema:\n{database_schema}"}},
                    "required": ["query"],
                },
            },
        }
    ]

    messages = [{"role": "system", "content": SQL_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    @track(name="SQL_Generation_Step")
    def _generate_sql_plan(msgs, tools_def):
        return _completion(
            model=_model_name,
            messages=msgs,
            tools=tools_def,
            temperature=_config.model.temperature,
            max_tokens=_config.model.max_tokens,
        )

    response = _generate_sql_plan(messages, tools)
    msg = response.choices[0].message

    if msg.tool_calls:
        messages.append(_msg_to_dict(msg))

        for tool_call in msg.tool_calls:
            sql_query = json.loads(tool_call.function.arguments)["query"]
            result = run_sql_query(sql_query)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

        def _get_content(m):
            return m.get("content", "") if isinstance(m, dict) else str(getattr(m, "content", ""))

        def _get_role(m):
            return m.get("role", "") if isinstance(m, dict) else str(getattr(m, "role", ""))

        has_empty_results = any("Query returned no results" in _get_content(m) for m in messages if _get_role(m) == "tool")

        if has_empty_results:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The previous query returned no results. Call run_sql_query again with "
                        "alternative or similar product terms. For example, if 'headphones' found "
                        "nothing, try 'earbuds' or 'earphones'."
                    ),
                }
            )

            @track(name="SQL_Alternative_Search")
            def _try_alternatives(msgs, tools_def):
                return _completion(
                    model=_model_name,
                    messages=msgs,
                    tools=tools_def,
                    tool_choice="auto",
                    temperature=_config.model.temperature,
                    max_tokens=_config.model.max_tokens,
                )

            alt_response = _try_alternatives(messages, tools)
            alt_msg = alt_response.choices[0].message

            if alt_msg.tool_calls:
                messages.append(_msg_to_dict(alt_msg))
                for tool_call in alt_msg.tool_calls:
                    sql_query = json.loads(tool_call.function.arguments)["query"]
                    result = run_sql_query(sql_query)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
            # If the model chose not to make a tool call, don't append anything —
            # messages already end with the user instruction, which is a valid
            # ending for all providers including Anthropic.

        @track(name="SQL_Final_Answer_Step")
        def _generate_final_answer(msgs):
            return _completion(
                model=_model_name,
                messages=msgs,
                temperature=_config.model.temperature,
                max_tokens=_config.model.max_tokens,
            )

        final = _generate_final_answer(messages)
        return final.choices[0].message.content

    return msg.content if msg.content else "I couldn't process that request."


@track
def run_rag_workflow(question: str, history: list) -> str:
    """Handle RAG policy queries."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "look_up_policy",
                "description": RAG_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query."}},
                    "required": ["query"],
                },
            },
        }
    ]

    messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    @track(name="RAG_Query_Generation")
    def _generate_rag_query(msgs, tools_def):
        return _completion(
            model=_model_name,
            messages=msgs,
            tools=tools_def,
            temperature=_config.model.temperature,
            max_tokens=_config.model.max_tokens,
        )

    response = _generate_rag_query(messages, tools)
    msg = response.choices[0].message

    if msg.tool_calls:
        messages.append(_msg_to_dict(msg))

        for tool_call in msg.tool_calls:
            query = json.loads(tool_call.function.arguments)["query"]
            context = look_up_policy(query)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": context,
                }
            )

        @track(name="RAG_Final_Answer_Step")
        def _generate_rag_answer(msgs):
            return _completion(
                model=_model_name,
                messages=msgs,
                temperature=_config.model.temperature,
                max_tokens=_config.model.max_tokens,
            )

        final = _generate_rag_answer(messages)
        return final.choices[0].message.content

    return msg.content if msg.content else "I couldn't process that request."


# 4. MAIN ENTRY POINT


@track(name="OhmSweetOhm_Agent")
def run_agent(user_question: str, chat_history: list, session_id: str) -> str:
    """Main agent entry point. Routes question to the appropriate workflow."""
    opik_context.update_current_trace(
        input={"question": user_question},
        thread_id=session_id,
        metadata={
            "session_id": session_id,
            "chat_history": json.dumps(chat_history),
            "_opik_graph_definition": {
                "format": "mermaid",
                "data": """
                graph TD;
                    Start(User Input) --> Router{Router};
                    Router -->|DATABASE| SQL[SQL Workflow];
                    Router -->|POLICY| RAG[Policy Workflow];
                    Router -->|CHAT| Chat[General Chat];
                    SQL --> SQLTool[DB Query];
                    RAG --> RAGTool[Vector Search];
                    Chat --> End(Response);
                """,
            },
        },
    )

    category = route_user_request(user_question, chat_history)

    if "DATABASE" in category:
        return run_sql_workflow(user_question, chat_history)
    elif "POLICY" in category:
        return run_rag_workflow(user_question, chat_history)
    else:
        if "CHAT" not in category:
            print(f"[Router] Unexpected category '{category}', defaulting to CHAT.")
        return run_chat_workflow(user_question, chat_history)
