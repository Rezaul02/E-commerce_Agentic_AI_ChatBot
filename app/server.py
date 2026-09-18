"""
CHAT SERVER — FLASK version
===========================
Cholao:  python -m app.server
     ba: flask --app app.server run --port 8000 --debug
prod:    gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:8000 app.server:app

Endpoint gulo age jemon chhilo temoni — tai ui/streamlit_app.py bodlate hobe na.

⭐ SHOBCHEYE BORO PORIBORTON: STREAMING
FastAPI async chhilo, tai `astream_events` diye shoja token stream kora jeto.
Flask sync (WSGI) — async generator chole na. Tai amra classic pattern use korchi:

    [Thread] agent.invoke(..., callbacks=[QueueCallbackHandler(q)])
                     │  protita token/tool event Queue e push kore
                     ▼
    [Main]   Queue theke get() kore SSE line hisebe yield kore

Eta production-e o thik moto kaj kore, shudhu server ke threaded mode e chalate hobe.
"""

import json
import queue
import threading
import uuid

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from langchain_core.callbacks.base import BaseCallbackHandler

from app.agent import chat, get_conversational_agent
from app.graph import chat_multi_agent
from app.memory import UserProfileStore, clear_session, get_full_history, ping_redis

app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)  # prod e: CORS(app, origins=["https://yourshop.com"])


# ============================ HELPERS ============================
def body():
    return request.get_json(silent=True) or {}


def new_session_id():
    return f"s-{uuid.uuid4().hex[:12]}"


def validate_message(msg):
    if not msg or not isinstance(msg, str) or not msg.strip():
        return "message is required"
    if len(msg) > 2000:
        return "message too long (max 2000 chars)"
    return None


# ============================ BASIC ============================
@app.get("/health")
def health():
    return jsonify({"status": "ok", "redis": ping_redis()})


# ============================ CHAT (single agent) ============================
@app.post("/chat")
def chat_endpoint():
    data = body()
    err = validate_message(data.get("message"))
    if err:
        return jsonify({"detail": err}), 422

    sid = data.get("session_id") or new_session_id()
    try:
        result = chat(data["message"], session_id=sid, user_id=data.get("user_id"))
    except Exception as e:
        return jsonify({"detail": f"Agent error: {e}"}), 500

    return jsonify({
        "answer": result["answer"],
        "session_id": sid,
        "tools_used": result["tools_used"],
        "handled_by": None,
    })


# ============================ CHAT (multi agent) ============================
@app.post("/chat/multi")
def chat_multi_endpoint():
    data = body()
    err = validate_message(data.get("message"))
    if err:
        return jsonify({"detail": err}), 422

    sid = data.get("session_id") or new_session_id()
    try:
        result = chat_multi_agent(data["message"], session_id=sid, user_id=data.get("user_id"))
    except Exception as e:
        return jsonify({"detail": f"Agent error: {e}"}), 500

    return jsonify({
        "answer": result["answer"],
        "session_id": sid,
        "tools_used": [],
        "handled_by": result.get("handled_by"),
    })


# ============================ STREAMING ============================
class QueueCallbackHandler(BaseCallbackHandler):
    """
    LangChain er callback gulo ke ekta thread-safe Queue te push kore.
    Eta diyei sync Flask e token-by-token streaming shomvob hoy.
    """

    def __init__(self, q: "queue.Queue"):
        self.q = q

    # --- LLM token ---
    def on_llm_new_token(self, token: str, **kwargs):
        if token:  # tool-call er somoy khali token ashe, segulo skip
            self.q.put({"type": "token", "content": token})

    # --- Tool lifecycle (UI te "product khujchi..." dekhanor jonno) ---
    def on_tool_start(self, serialized, input_str, **kwargs):
        name = (serialized or {}).get("name", "tool")
        self.q.put({"type": "tool_start", "name": name})

    def on_tool_end(self, output, **kwargs):
        self.q.put({"type": "tool_end"})

    def on_tool_error(self, error, **kwargs):
        self.q.put({"type": "tool_error", "message": str(error)})

    def on_llm_error(self, error, **kwargs):
        self.q.put({"type": "error", "message": str(error)})


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
def chat_stream():
    data = body()
    err = validate_message(data.get("message"))
    if err:
        return jsonify({"detail": err}), 422

    sid = data.get("session_id") or new_session_id()
    user_id = data.get("user_id")
    message = data["message"]

    # streaming=True kora LLM diye banano executor
    agent = get_conversational_agent(streaming=True)

    payload = {
        "input": message,
        "user_id": user_id or "guest",
        "user_profile": UserProfileStore.as_prompt_text(user_id) if user_id else "none",
    }

    q: "queue.Queue" = queue.Queue()
    handler = QueueCallbackHandler(q)

    def worker():
        try:
            agent.invoke(
                payload,
                config={
                    "configurable": {"session_id": sid},
                    "callbacks": [handler],
                },
            )
        except Exception as e:
            q.put({"type": "error", "message": str(e)})
        finally:
            q.put({"type": "done"})   # generator ke thamar signal

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        yield sse({"type": "session", "session_id": sid})
        while True:
            item = q.get()            # worker thread theke event ashe
            yield sse(item)
            if item["type"] == "done":
                break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # nginx buffering bondho
        },
    )


# ============================ SESSION / HISTORY ============================
@app.get("/sessions/<session_id>/history")
def history_endpoint(session_id):
    return jsonify({"session_id": session_id, "messages": get_full_history(session_id)})


@app.delete("/sessions/<session_id>")
def clear_endpoint(session_id):
    clear_session(session_id)
    return jsonify({"session_id": session_id, "cleared": True})


# ============================ USER PROFILE ============================
@app.get("/profile/<user_id>")
def get_profile(user_id):
    return jsonify({"user_id": user_id, "profile": UserProfileStore.get(user_id)})


@app.post("/profile/<user_id>")
def set_profile(user_id):
    UserProfileStore.set(user_id, **body())
    return jsonify({"user_id": user_id, "profile": UserProfileStore.get(user_id)})


if __name__ == "__main__":
    # threaded=True obosshoi lagbe — streaming worker thread er jonno
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True, use_reloader=True)
