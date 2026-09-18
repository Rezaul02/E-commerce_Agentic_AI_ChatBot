"""
MULTI-AGENT SYSTEM (LangGraph supervisor pattern) -- Phase 2
============================================================

Keno multi-agent?
  Ekta agent e 10+ tool dhukale LLM confuse hoy, prompt lomba hoy, cost bare.
  Domain onujayi vag korle protita sub-agent er prompt chhoto o sharp thake.

Architecture:

                    ┌──────────────┐
        user ──────►│  SUPERVISOR  │◄─────────┐
                    └──────┬───────┘          │
                           │ route            │ result
         ┌─────────────────┼─────────────────┐│
         ▼                 ▼                 ▼│
   discovery_agent    order_agent      return_agent
   (search, recs)     (tracking)       (RMA, refund)

History: LangChain er Redis history theke load kore graph e inject kora hoy,
run shesh e abar Redis e save kora hoy -- tai single agent o multi-agent duitai
eki conversation memory share kore.
"""

from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.agent import build_llm
from app.memory import WindowedRedisHistory
from app.prompts import (
    DISCOVERY_AGENT_PROMPT,
    ORDER_AGENT_PROMPT,
    RETURN_AGENT_PROMPT,
    SUPERVISOR_PROMPT,
)
from app.tools import DISCOVERY_TOOLS, ORDER_TOOLS, RETURN_TOOLS

MEMBERS = ["discovery_agent", "order_agent", "return_agent"]


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------
class AgentState(MessagesState):
    """MessagesState theke `messages` field ta ashe (auto-append reducer soho)."""
    next: str = ""
    user_id: str = "guest"
    step_count: int = 0
# --------------------------------------------------------------------------
# Supervisor -- structured output diye routing
# --------------------------------------------------------------------------
class Route(BaseModel):
    """Decision made by the Supervisor."""
    next: Literal["discovery_agent", "order_agent", "return_agent", "FINISH"] = Field(
        ..., description="Which specialist will work next, or FINISH"
    )
    reason: str = Field("", description="One-line explanation for this route")


# def make_supervisor_node(llm):
#     router_llm = llm.with_structured_output(Route)

#     def supervisor(state: AgentState) -> dict:
#         msgs = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
#         decision: Route = router_llm.invoke(msgs)
#         nxt = decision.next
#         return {"next": END if nxt == "FINISH" else nxt}

#     return supervisor

def make_supervisor_node(llm):
    router_llm = llm.with_structured_output(Route)

    def supervisor(state: AgentState) -> dict:
     
        last = state["messages"][-1]
        if getattr(last, "name", None) in MEMBERS:
            return {"next": END}

        msgs = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
        decision: Route = router_llm.invoke(msgs)
        nxt = decision.next
        return {"next": END if nxt == "FINISH" else nxt}

    return supervisor


# --------------------------------------------------------------------------
# Specialist nodes
# --------------------------------------------------------------------------
def make_specialist_node(llm, tools, system_prompt: str, name: str):
    react_agent = create_react_agent(llm, tools=tools, prompt=system_prompt)

    def node(state: AgentState) -> dict:
        result = react_agent.invoke({"messages": state["messages"]})
        last = result["messages"][-1]
        # Sub-agent er uttor ke ekta AIMessage hisebe main state e ferot dei
        return {"messages": [AIMessage(content=last.content, name=name)]}

    return node


# --------------------------------------------------------------------------
# Graph build
# --------------------------------------------------------------------------
def build_graph():
    llm = build_llm()

    builder = StateGraph(AgentState)
    builder.add_node("supervisor", make_supervisor_node(llm))
    builder.add_node("discovery_agent", make_specialist_node(llm, DISCOVERY_TOOLS, DISCOVERY_AGENT_PROMPT, "discovery_agent"))
    builder.add_node("order_agent", make_specialist_node(llm, ORDER_TOOLS, ORDER_AGENT_PROMPT, "order_agent"))
    builder.add_node("return_agent", make_specialist_node(llm, RETURN_TOOLS, RETURN_AGENT_PROMPT, "return_agent"))

    builder.add_edge(START, "supervisor")

    # supervisor -> member OR end
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {**{m: m for m in MEMBERS}, END: END},
    )

    # protita member kaj shesh kore supervisor e fire ashe
    for m in MEMBERS:
        builder.add_edge(m, "supervisor")

    return builder.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# --------------------------------------------------------------------------
# Public entry point (Redis history soho)
# --------------------------------------------------------------------------
def chat_multi_agent(message: str, session_id: str, user_id: Optional[str] = None) -> dict:
    history = WindowedRedisHistory(session_id=session_id)
    past = history.messages                       # Redis theke load
    incoming = HumanMessage(content=message)

    graph = get_graph()
    result = graph.invoke(
        {"messages": past + [incoming], "user_id": user_id or "guest"},
        config={"recursion_limit": 12},           # supervisor loop guard
    )

    new_msgs = result["messages"][len(past) + 1:]
    answer = next((m.content for m in reversed(new_msgs) if m.content), "Dukkhito, uttor toiri korte parlam na.")
    handled_by = next((getattr(m, "name", None) for m in reversed(new_msgs) if getattr(m, "name", None)), None)

    history.add_messages([incoming, AIMessage(content=answer)])   # Redis e save

    return {"answer": answer, "handled_by": handled_by, "session_id": session_id}


if __name__ == "__main__":
    import uuid

    sid = f"graph-{uuid.uuid4().hex[:8]}"
    print(f"ShopMate Multi-Agent CLI | session={sid}\n")
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in {"exit", "quit"}:
            break
        if not msg:
            continue
        out = chat_multi_agent(msg, session_id=sid, user_id="U100")
        print(f"\nShopMate [{out['handled_by']}]: {out['answer']}\n")
