"""
app/agent.py — SHUDHU EKTA ONGSHO BODLECHE
=========================================
Ki bodlalo ebong keno:

  Age: `_executor` ekta single global chhilo. Prothom bar je `streaming` flag
       diye build hoto, pore shobshomoy sheta ferot asto.
  Ekhon: streaming=True ar streaming=False er jonno ALADA cached executor.

  Keno dorkar holo? Flask e /chat (non-streaming) ar /chat/stream (streaming)
  duita endpoint eki process e chole. Age /chat age hit hole streaming executor
  ar toiri hoto na, fole /chat/stream e kono token asto na.

  Neeche "⬇️ EI ONGSHOTUKU BODLAN" comment er moddhe ja ache, shudhu shetutuku
  apnar existing agent.py te replace korlei hobe. Baki shob age jemon chhilo temoni.
"""

from typing import Any, Dict, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from app.config import settings
from app.memory import UserProfileStore, get_session_history
from app.prompts import build_agent_prompt
from app.tools import ALL_TOOLS


# --------------------------------------------------------------------------
# LLM  (ochopribortito)
# --------------------------------------------------------------------------
def build_llm(streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.MODEL_NAME,          # gpt-4o-mini
        temperature=settings.TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
        streaming=streaming,
        timeout=60,
        max_retries=2,
    )


# --------------------------------------------------------------------------
# Agent executor  (ochopribortito)
# --------------------------------------------------------------------------
def build_agent_executor(streaming: bool = False) -> AgentExecutor:
    llm = build_llm(streaming=streaming)
    prompt = build_agent_prompt()
    agent = create_tool_calling_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=settings.MAX_ITERATIONS,
        max_execution_time=60,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        early_stopping_method="force",
    )

# ==========================================================================
# ⬇️ EI ONGSHOTUKU BODLAN (purono `_executor = None` block er poriborte)
# ==========================================================================
_executors: Dict[bool, AgentExecutor] = {}

def get_executor(streaming: bool = False) -> AgentExecutor:
    if streaming not in _executors:
        _executors[streaming] = build_agent_executor(streaming=streaming)
    return _executors[streaming]


def build_conversational_agent(streaming: bool = False) -> RunnableWithMessageHistory:
    return RunnableWithMessageHistory(
        get_executor(streaming=streaming),
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="output",
    )


_conversational: Dict[bool, RunnableWithMessageHistory] = {}


def get_conversational_agent(streaming: bool = False) -> RunnableWithMessageHistory:
    if streaming not in _conversational:
        _conversational[streaming] = build_conversational_agent(streaming=streaming)
    return _conversational[streaming]
# ==========================================================================
# ⬆️ EI PORJONTO
# ==========================================================================


# --------------------------------------------------------------------------
# Public entry point  (ochopribortito)
# --------------------------------------------------------------------------
def chat(message: str, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    agent = get_conversational_agent(streaming=False)

    payload = {
        "input": message,
        "user_id": user_id or "guest",
        "user_profile": UserProfileStore.as_prompt_text(user_id) if user_id else "No saved preferences yet.",
    }

    result = agent.invoke(payload, config={"configurable": {"session_id": session_id}})

    tools_used = [
        {"tool": step[0].tool, "input": step[0].tool_input}
        for step in result.get("intermediate_steps", [])
    ]

    return {"answer": result["output"], "tools_used": tools_used, "session_id": session_id}


# --------------------------------------------------------------------------
# CLI test:  python -m app.agent   (ochopribortito)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import uuid

    sid = f"cli-{uuid.uuid4().hex[:8]}"
    uid = "U100"
    print(f"ShopMate CLI | session={sid} user={uid} | 'exit' likhe ber hon\n")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in {"exit", "quit"}:
            break
        if not msg:
            continue
        out = chat(msg, session_id=sid, user_id=uid)
        print(f"\nShopMate: {out['answer']}")
        if out["tools_used"]:
            print(f"   [tools: {', '.join(t['tool'] for t in out['tools_used'])}]")
        print()
