"""
Streamlit app for Customer Support Agent.
"""

import os
import sys
import uuid
from pathlib import Path

# Add src/ to path so the package is importable on Streamlit Cloud
sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

# --- 1. CONFIGURATION (Must be first) ---
st.set_page_config(page_title="Ohm Sweet Ohm | Support", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- 2. SESSION STATE MANAGEMENT ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = False

# If the module was reloaded (e.g. hot-reload during dev), module-level state is lost.
# Detect the mismatch and reset so the user is prompted to reconnect.
if st.session_state.agent_initialized:
    from customer_support_agent.agent import is_initialized

    if not is_initialized():
        st.session_state.agent_initialized = False

# --- 3. CUSTOM STYLING ---
st.markdown(
    """
    <style>
    h1 {
        background: -webkit-linear-gradient(45deg, #00ADB5, #EEEEEE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -1px;
    }
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    div.stButton > button {
        background-color: #00ADB5;
        color: white;
        border: none;
        box-shadow: 0 4px 14px 0 rgba(0, 173, 181, 0.39);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #00FFF5;
        box-shadow: 0 6px 20px rgba(0, 173, 181, 0.23);
        transform: scale(1.02);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 4. SIDEBAR ---
base_dir = Path(__file__).parent
DB_PATH = base_dir / "data" / "ohm_sweet_ohm.db"
CHROMA_PATH = base_dir / "data" / "chroma_db"

with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/electronics.png", width=120)
    st.title("Ohm Sweet Ohm")
    st.markdown("---")

    if not st.session_state.agent_initialized:
        st.markdown("### 🔑 Connect to Agent")
        st.caption("Enter your API keys to get started. Keys are only stored for this session.")

        # Provider selection
        provider = st.radio(
            "LLM Provider",
            options=["OpenAI", "Anthropic"],
            horizontal=True,
        )
        provider_key = provider.lower()  # "openai" or "anthropic"

        # Dynamic key label and placeholder based on provider
        key_label = "OpenAI API Key" if provider == "OpenAI" else "Anthropic API Key"
        key_placeholder = "sk-..." if provider == "OpenAI" else "sk-ant-..."
        env_var = "OPENAI_API_KEY" if provider == "OpenAI" else "ANTHROPIC_API_KEY"

        api_key = st.text_input(
            key_label,
            value=os.environ.get(env_var, ""),
            type="password",
            placeholder=key_placeholder,
        )
        opik_key = st.text_input(
            "Opik API Key",
            value=os.environ.get("OPIK_API_KEY", ""),
            type="password",
            placeholder="Your Opik API key",
        )
        opik_workspace = st.text_input(
            "Opik Workspace",
            value=os.environ.get("OPIK_WORKSPACE", ""),
            placeholder="your-workspace-name",
        )
        opik_project = st.text_input(
            "Opik Project Name",
            value="Ohm Sweet Ohm Support Agent",
            placeholder="Ohm Sweet Ohm Support Agent",
        )

        if st.button("Connect", type="primary", use_container_width=True):
            if not api_key:
                st.error(f"{key_label} is required.")
            elif not opik_key:
                st.error("Opik API Key is required.")
            elif not opik_workspace:
                st.error("Opik Workspace is required.")
            else:
                with st.spinner("Initializing agent..."):
                    try:
                        # Set project name before configure so Opik picks it up
                        os.environ["OPIK_PROJECT_NAME"] = opik_project

                        from opik import configure

                        configure(api_key=opik_key, workspace=opik_workspace)

                        from customer_support_agent.utils.config import get_config

                        config = get_config()
                        model_name = config.models[provider_key]

                        from customer_support_agent.agent import init_agent

                        init_agent(
                            api_key=api_key,
                            provider=provider_key,
                            model_name=model_name,
                            db_path=DB_PATH,
                            chroma_path=CHROMA_PATH,
                            opik_project_name=opik_project,
                        )

                        st.session_state.agent_initialized = True
                        st.session_state.provider = provider
                        st.session_state.model_name = model_name
                        st.session_state.opik_project = opik_project
                        st.rerun()
                    except FileNotFoundError as e:
                        st.error(f"Database setup required:\n\n{e}")
                    except Exception as e:
                        st.error(f"Failed to connect: {e}")
    else:
        st.success("Connected")
        st.caption(f"Provider: **{st.session_state.get('provider', '')}** — `{st.session_state.get('model_name', '')}`")
        st.caption(f"Session: `{st.session_state.session_id[:8]}...`")
        st.caption(f"Opik project: `{st.session_state.get('opik_project', '')}`")

        st.markdown("---")

        if st.button("➕ Start New Conversation", type="primary", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        st.markdown("### 🛠️ Lab Tools")
        st.info("This agent is instrumented with **Opik**. Check your dashboard to see the traces!")

        if st.checkbox("Show Debug Info"):
            st.write(f"**DB exists:** `{DB_PATH.exists()}`")
            st.write(f"**ChromaDB exists:** `{CHROMA_PATH.exists()}`")

# --- 5. MAIN AREA ---
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("# ⚡")
with col2:
    st.title("Customer Support")
    st.markdown(
        "**How can we help you power up today?** Ask about products, order statuses, returns, inventory, promotions, policies, and more."
    )

st.divider()

if not st.session_state.agent_initialized:
    st.info(
        "**Welcome to the Ohm Sweet Ohm workshop!**\n\n"
        "Enter your API keys in the sidebar to connect the agent and start chatting.\n\n"
        "You'll need:\n"
        "- An **OpenAI** or **Anthropic** API key (for the LLM)\n"
        "- An **Opik API key**, **workspace**, and **project name** — sign up free at comet.com/opik"
    )
else:
    from customer_support_agent.agent import run_agent

    # Display chat history
    for message in st.session_state.messages:
        role_icon = "👤" if message["role"] == "user" else "⚡"
        with st.chat_message(message["role"], avatar=role_icon):
            st.markdown(message["content"])

    # Handle new input
    if prompt := st.chat_input("Ex: Do you have wireless headphones in stock?"):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        history_for_agent = st.session_state.messages.copy()
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant", avatar="⚡"):
            message_placeholder = st.empty()
            with st.spinner("Connecting to knowledge base..."):
                try:
                    response = run_agent(prompt, history_for_agent, st.session_state.session_id)
                    message_placeholder.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    message_placeholder.error(f"🔌 Circuit Break! Error: {e}")
