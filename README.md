# 🛍️ E-commerce Agentic Chatbot — সম্পূর্ণ গাইড (বাংলা)

**স্ট্যাক:** LangChain + LangGraph · GPT-4o-mini · Redis · **Flask** · Streamlit
**প্ল্যাটফর্ম:** Ubuntu 22.04 / 24.04 · **Docker ছাড়া**

> এই ফাইলটা পুরনো `README_BANGLA.md` আর `CHANGES_BANGLA.md` — দুটোরই জায়গা নিচ্ছে। ওই দুটো মুছে ফেলতে পারেন।

---

## সূচিপত্র

| # | বিষয় |
|---|---|
| ০ | প্রজেক্ট ওভারভিউ ও আর্কিটেকচার |
| ১ | ফোল্ডার স্ট্রাকচার ⚠️ |
| ২ | Ubuntu সেটআপ (Redis + venv) |
| ৩ | চালানো |
| ৪ | Dummy API (Flask) |
| ৫ | Tool Calling System |
| ৬ | History Management (Redis) |
| ৭ | System Prompt |
| ৮ | Agent (gpt-4o-mini) |
| ৯ | Chat Server (Flask) + Streaming |
| ১০ | Multi-Agent (LangGraph) |
| ১১ | টেস্ট স্ক্রিপ্ট |
| ১২ | প্রোডাকশন ডিপ্লয়মেন্ট |
| ১৩ | পরবর্তী উন্নয়ন |
| ১৪ | সমস্যা ও সমাধান ⚠️ |

---

## ধাপ ০ — প্রজেক্টটা কী

চারটা কাজ করে এই বট:

| কাজ | উদাহরণ | যে tool চলে |
|---|---|---|
| Product discovery | "৫ হাজারের মধ্যে হেডফোন দেখাও" | `search_products` |
| Order tracking | "ORD-1001 কোথায়?" | `track_order`, `list_my_orders` |
| Returns | "এটা ফেরত দিতে চাই" | `check_return_eligibility` → confirm → `create_return_request` |
| Recommendation | "আমার জন্য কিছু সাজেস্ট করো" | `recommend_products` |

**মূল ধারণা:** LLM নিজে কোনো ডেটা জানে না। LLM শুধু সিদ্ধান্ত নেয় — *"এই প্রশ্নের উত্তর দিতে কোন ফাংশন কল করতে হবে, কী argument দিয়ে?"* — এটাই **tool calling**। ডেটা আসে আপনার API থেকে।

### আর্কিটেকচার

```
┌─────────────┐     ┌──────────────────────────────────────┐
│  Streamlit  │────▶│   Chat Server (Flask :8000)          │
│    :8501    │◀────│                                       │
└─────────────┘     │  ┌────────────────────────────────┐  │
                    │  │ RunnableWithMessageHistory     │  │
                    │  │   (LangChain)                  │──┼──▶ ┌─────────┐
                    │  └───────────┬────────────────────┘  │    │  Redis  │
                    │              ▼                        │◀───│  :6379  │
                    │  ┌────────────────────────────────┐  │    └─────────┘
                    │  │ AgentExecutor                  │  │
                    │  │   LLM: gpt-4o-mini             │──┼──▶ OpenAI API
                    │  │   Tools: ১০টা                  │  │
                    │  └───────────┬────────────────────┘  │
                    └──────────────┼───────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │  Dummy E-commerce API (Flask :8001)  │
                    │  /products /orders /returns /recs    │
                    └──────────────────────────────────────┘
```

চারটা জিনিস চলবে: **Redis** (systemd service), **Dummy API** (:8001), **Chat Server** (:8000), **UI** (:8501)।

---

## ধাপ ১ — ফোল্ডার স্ট্রাকচার ⚠️

**এটাই সবচেয়ে বেশি ভুল হয়।** ফাইলগুলো অবশ্যই এই কাঠামোতে থাকতে হবে:

```
multi_agent_chatbot/          ← প্রজেক্ট root (নামে কোনো স্পেস রাখবেন না!)
├── .env                      ← OPENAI_API_KEY এখানে
├── requirements.txt
├── setup_ubuntu.sh
├── run_all.sh
├── README_BANGLA.md
├── venv/
│
├── dummy_api/                ← Dummy backend
│   ├── __init__.py           ← খালি ফাইল, কিন্তু থাকতেই হবে
│   ├── data.py               ← নকল ডেটাবেস
│   └── main.py               ← Flask endpoints
│
├── app/                      ← Agent
│   ├── __init__.py           ← খালি ফাইল, কিন্তু থাকতেই হবে
│   ├── config.py             ← env variable
│   ├── api_client.py         ← dummy API কল করার layer
│   ├── tools.py              ← ⭐ Tool calling system
│   ├── memory.py             ← ⭐ Redis history
│   ├── prompts.py            ← System prompt
│   ├── agent.py              ← ⭐ gpt-4o-mini tool-calling agent
│   ├── graph.py              ← LangGraph multi-agent
│   └── server.py             ← Flask chat server
│
└── ui/
    └── streamlit_app.py
```

### ফাইল ফ্ল্যাট হয়ে থাকলে (সব এক ফোল্ডারে) — ঠিক করুন

```bash
cd ~/Downloads/multi_agent_chatbot

mkdir -p dummy_api app ui
mv data.py main.py dummy_api/
mv config.py api_client.py tools.py memory.py prompts.py agent.py graph.py server.py app/
mv streamlit_app.py ui/
touch dummy_api/__init__.py app/__init__.py
rm -f docker-compose.yml
```

### ⚠️ ফোল্ডারের নামে স্পেস রাখবেন না

`"multi_agent_chatbot "` (শেষে স্পেস) — এটা script, venv, systemd সবখানে অদ্ভুত এরর দেয়। যাচাই:

```bash
ls -d ~/Downloads/multi_agent* | cat -A     # শেষে $ এর আগে স্পেস আছে কিনা
```

থাকলে:

```bash
cd ~/Downloads && mv "multi_agent_chatbot " multi_agent_chatbot
```

**রিনেমের পরে venv অবশ্যই নতুন করে বানাতে হবে** — venv-এর ভেতরে পুরনো absolute path হার্ডকোড থাকে (ধাপ ২.২ দেখুন)।

---

## ধাপ ২ — Ubuntu সেটআপ (Docker ছাড়া)

### ২.১ — Redis নেটিভভাবে

```bash
sudo apt update
sudo apt install -y redis-server

# systemd দিয়ে ম্যানেজ
sudo sed -i 's/^supervised .*/supervised systemd/' /etc/redis/redis.conf

# শুধু localhost-এ bind (নিরাপত্তা)
sudo sed -i 's/^# *bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf

# RAM ভরলে পুরনো key আগে মুছবে — chat history-র জন্য উপযুক্ত
echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf

sudo systemctl enable redis-server
sudo systemctl restart redis-server
redis-cli ping        # PONG আসতে হবে
```

দরকারি কমান্ড:

```bash
sudo systemctl status redis-server
redis-cli KEYS 'chat:*'              # কোন কোন session আছে
redis-cli LRANGE chat:s-abc123 0 -1  # একটা session-এর মেসেজ
redis-cli TTL chat:s-abc123          # কত সেকেন্ড পরে expire
redis-cli FLUSHDB                    # সব মুছুন (সাবধান)
```

### ২.২ — Python environment

```bash
sudo apt install -y python3 python3-venv python3-pip build-essential

cd ~/Downloads/multi_agent_chatbot
python3 -m venv venv
source venv/bin/activate

which python          # venv/bin/python দেখাতে হবে

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
nano .env             # OPENAI_API_KEY বসান
```

> **নোট:** Ubuntu-তে `python` কমান্ড থাকে না, শুধু `python3`। venv active থাকলে `python` কাজ করে — কারণ venv নিজে একটা symlink বানায়। তাই `(venv)` দেখেও `python: command not found` এলে বুঝবেন venv ভাঙা, নতুন করে বানাতে হবে।

**অথবা একটা কমান্ডে সব:** `bash setup_ubuntu.sh`

---

## ধাপ ৩ — চালানো

### ⚠️ সবসময় project root থেকে, `-m` দিয়ে

```bash
cd ~/Downloads/multi_agent_chatbot
source venv/bin/activate

python -m dummy_api.main        # ✅
python dummy_api/main.py        
```

**কেন?**

| কমান্ড | `sys.path`-এ যা বসে | ফল |
|---|---|---|
| `python dummy_api/main.py` | `dummy_api/` ফোল্ডার | `app`/`dummy_api` package দেখা যায় না → ❌ |
| `python -m dummy_api.main` | current directory (root) | দুটোই দেখা যায় → ✅ |

`-m` ফাইল কোথায় আছে তা দেখে না, **আপনি কোথা থেকে কমান্ড দিলেন** সেটা দেখে।

### তিনটা টার্মিনালে

```bash
# Terminal 1 — Dummy API
source venv/bin/activate && python -m dummy_api.main

# Terminal 2 — Chat Server
source venv/bin/activate && python -m app.server

# Terminal 3 — UI
source venv/bin/activate && streamlit run ui/streamlit_app.py
```

### অথবা এক কমান্ডেok 

```bash
bash run_all.sh          # তিনটাই ব্যাকগ্রাউন্ডে, Ctrl+C দিলে সব বন্ধ
tail -f logs/chat_server.log
```

খোলার পর: http://localhost:8501

---

## ধাপ ৪ — Dummy API (Flask)

```bash
python -m dummy_api.main
curl http://localhost:8001/           # সব route-এর লিস্ট
```

| Endpoint | কাজ |
|---|---|
| `GET /products` | query, category, brand, price range, sort দিয়ে সার্চ |
| `GET /products/<id>` | ফুল ডিটেইল |
| `GET /stock/<id>` | স্টক আছে কিনা |
| `GET /orders/<order_id>` | স্ট্যাটাস + টাইমলাইন |
| `GET /users/<user_id>/orders` | সাম্প্রতিক অর্ডার লিস্ট |
| `GET /returns/eligibility/<order_id>` | রিটার্ন করা যাবে কিনা |
| `POST /returns` | RMA তৈরি (write action) |
| `GET /recommendations` | content-based সাজেশন |
| `GET /policy/<topic>` | return/refund/shipping/warranty/payment |

**টেস্ট ডেটা:**
- ইউজার: `U100` (Rafiq, Dhaka), `U200` (Nusrat, Chattogram)
- অর্ডার: `ORD-1001` (in_transit), `ORD-1002` (delivered), `ORD-2001` (delivered), `ORD-2002` (cancelled)
- প্রোডাক্ট: `P1001`–`P4001`

### Flask-এ যে ৫টা জিনিস আলাদা

**① Query parameter — auto type-cast নেই।** Flask-এ সব `str` হিসেবে আসে, তাই `q_str / q_float / q_int / q_bool` — চারটা হেল্পার লেখা আছে।

**② Exception:** `HTTPException(404, detail=...)` → `raise ApiError("...", 404)` + `@app.errorhandler`। রেসপন্স ফরম্যাট `{"detail": "..."}` রাখা হয়েছে, তাই `api_client.py` বদলাতে হয়নি।

**③ Response:** `return {...}` → `return jsonify({...})`

**④ Pydantic body model → manual validation** (`POST /returns` দেখুন)

**⑤ ⚠️ Route order গুরুত্বপূর্ণ:**

```python
@app.get("/returns/eligibility/<order_id>")   # এটা আগে
@app.get("/returns/<rma_id>")                 # এটা পরে
```

উল্টো লিখলে Flask "eligibility" কে `rma_id` ধরে নেবে।

**যা হারালো:** FastAPI-র `/docs` (Swagger)। বিকল্প — `GET /` এ route লিস্ট।

**ডিজাইন সিদ্ধান্ত:** dummy API-তে ইচ্ছা করেই বাস্তব business rule রাখা — ৭ দিনের পরে রিটার্নে `409`, cancelled অর্ডারে রিটার্নে error। একটা এজেন্ট শুধু happy path-এ চললে সেটা ডেমো, প্রোডাক্ট না।

---

## ধাপ ৫ — Tool Calling System ⭐

`app/tools.py` — পুরো প্রজেক্টের হৃদয়।

```python
class SearchProductsInput(BaseModel):                    # ① Schema
    query: Optional[str] = Field(None, description="Free-text keywords...")
    max_price: Optional[float] = Field(None, description="Customer budget in BDT")

@tool("search_products", args_schema=SearchProductsInput)
def search_products(query=None, max_price=None, ...) -> str:
    """Catalog theke product khoje ber kore..."""        # ② Description
    try:
        return _ok({...})                                 # ③ Compact return
    except APIError as e:
        return _err(e)
```

### ৪টা নিয়ম

**নিয়ম ১ — description-ই LLM-এর ডকুমেন্টেশন।** LLM কোড দেখে না, শুধু নাম + docstring + argument description দেখে। docstring-এ লিখুন *কখন* ব্যবহার করতে হবে এবং *কখন নয়*:
> "...Specific ekta product er detail dorkar hole `get_product_details` use korbe." ← এই এক লাইন ভুল tool কল অর্ধেক কমায়।

**নিয়ম ২ — tool কখনো exception ছুঁড়বে না।** Error-ও string: `{"error": true, "message": "Order not found"}`। তাহলে এজেন্ট নিজেই বলতে পারবে "অর্ডার আইডিটা মিলছে না"। Exception হলে পুরো chain ক্র্যাশ করত।

**নিয়ম ৩ — রিটার্ন ছোট রাখুন।** `_slim_product()` দেখুন — ১০টা প্রোডাক্টের ফুল JSON ≈ ৩০০০ টোকেন, দরকারি ফিল্ড ≈ ৪০০। খরচ বাঁচে, LLM কম confuse হয়।

**নিয়ম ৪ — write আর read আলাদা।** `create_return_request` irreversible। docstring + system prompt — দুই জায়গায় confirmation-এর কথা লেখা আছে। দুই জায়গায় বললে মেনে চলার হার অনেক বাড়ে।

### ১০টা tool

```
Discovery : search_products, get_product_details, check_stock, recommend_products
Order     : track_order, list_my_orders
Returns   : check_return_eligibility, create_return_request, get_return_status
Common    : get_store_policy
```

### Multi-step tool calling

ইউজার: *"আমার শেষ অর্ডারটার কী অবস্থা?"*

```
Turn 1 → LLM: order_id নেই → list_my_orders(user_id="U100")
Turn 2 → LLM: এখন track_order(order_id="ORD-1001")
Turn 3 → LLM: বাংলায় final answer
```

`AgentExecutor` লুপটা নিজে চালায়। আপনি শুধু `max_iterations` দিয়ে সীমা বাঁধেন।

---

## ধাপ ৬ — History Management (Redis) ⭐

`app/memory.py` — ৩ লেভেল:

### L1 — Short-term: `RedisChatMessageHistory`
`langchain-redis` প্যাকেজ। প্রতিটা মেসেজ Redis list-এ, key: `chat:{session_id}`, TTL ২৪ ঘণ্টা।

### L2 — Window: `WindowedRedisHistory`
**সমস্যা:** ৫০ টার্ন কথা বললে প্রতি রিকোয়েস্টে ৫০টা মেসেজ যাবে → খরচ ও latency বাড়বে, মাঝের ইনফো হারাবে ("lost in the middle")।

**সমাধান:** সব মেসেজ Redis-এ **থাকবে** (অডিট), কিন্তু LLM-কে শুধু **শেষ N টা**:

```python
@property
def messages(self):        return self._inner.messages[-self.window:]   # LLM
@property
def full_messages(self):   return self._inner.messages                  # UI/audit
```

`.env`-এ `HISTORY_WINDOW=20`।

### L3 — Long-term: `UserProfileStore`
"আমার বাজেট ৫০০০", "Aura ব্র্যান্ড পছন্দ" — এগুলো `profile:{user_id}` hash-এ, TTL ছাড়া। System prompt-এ inject হয়। ফলে নতুন সেশনেও বট ইউজারকে চেনে।

### সব জোড়া লাগে কীভাবে

```python
RunnableWithMessageHistory(
    executor, get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output",
)
agent.invoke({"input": msg, ...}, config={"configurable": {"session_id": sid}})
```

লোড, সেভ — সব LangChain করে। আপনি একটা `redis.set()` লিখবেন না।

---

## ধাপ ৭ — System Prompt

`app/prompts.py` — ৭টা ব্লক, প্রতিটার কারণ:

| ব্লক | কেন |
|---|---|
| **ভাষা** | না বললে GPT ইংরেজিতে চলে যায় |
| **কাজ** | scope সীমিত করা |
| **Grounding rule** | সবচেয়ে গুরুত্বপূর্ণ — "price, stock, status কখনো নিজে বানাবে না" |
| **Tool strategy** | আন্দাজে argument না দিয়ে clarifying question |
| **Write confirmation** | রিটার্নের আগে explicit "হ্যাঁ" |
| **Format** | ছোট উত্তর, bullet, ১২০ শব্দের মধ্যে |
| **Privacy** | অন্য ইউজারের ডেটা না দেখানো, OTP/কার্ড না চাওয়া |

```python
[("system", SYSTEM_PROMPT),
 MessagesPlaceholder("chat_history"),      # Redis থেকে এখানে বসে
 ("human", "{input}"),
 MessagesPlaceholder("agent_scratchpad")]  # tool call/result এখানে জমে
```

> ⚠️ `agent_scratchpad` না থাকলে `create_tool_calling_agent` কাজ করবে না — সবচেয়ে কমন ভুল।

---

## ধাপ ৮ — Agent (gpt-4o-mini)

```python
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
executor = AgentExecutor(agent=agent, tools=ALL_TOOLS, max_iterations=8, ...)
```

**কেন `create_tool_calling_agent`, ReAct নয়?** ReAct LLM-এর টেক্সট parse করে ("Action: ...") — ফরম্যাট একটু এদিক-ওদিক হলেই ভাঙে। `create_tool_calling_agent` OpenAI-র নেটিভ function calling ব্যবহার করে — argument JSON schema মেনে আসে। অনেক বেশি নির্ভরযোগ্য।

**কেন `temperature=0.2`?** Tool calling-এ সৃজনশীলতা নয়, ধারাবাহিকতা দরকার। ০ দিলে উত্তর রোবটিক, ০.২ ভারসাম্য।

**সেটিংস:** `max_iterations=8` (লুপ গার্ড) · `max_execution_time=60` · `return_intermediate_steps=True` (ডিবাগ) · `verbose=True` (prod-এ `False`)

### Executor caching — Flask-এর জন্য জরুরি পরিবর্তন

Flask-এ `/chat` আর `/chat/stream` একই প্রসেসে চলে। তাই streaming ও non-streaming এর জন্য **আলাদা cached executor** দরকার:

```python
_executors: Dict[bool, AgentExecutor] = {}

def get_executor(streaming: bool = False) -> AgentExecutor:
    if streaming not in _executors:
        _executors[streaming] = build_agent_executor(streaming=streaming)
    return _executors[streaming]
```

আগের single-global ভার্সনে `/chat` আগে হিট হলে `/chat/stream`-এ কোনো টোকেন আসত না।

### প্রথম টেস্ট

```bash
python -m app.agent
```

```
You: 5000 takar moddhe valo headphone ache?
You: oi tar detail dao          ← এখানেই বোঝা যাবে Redis history কাজ করছে
You: ORD-1001 kothay ache?
```

---

## ধাপ ৯ — Chat Server (Flask) + Streaming

```bash
python -m app.server
```

| Endpoint | কাজ |
|---|---|
| `POST /chat` | single agent |
| `POST /chat/multi` | multi-agent (LangGraph) |
| `POST /chat/stream` | SSE streaming |
| `GET /sessions/<sid>/history` | পুরো হিস্ট্রি |
| `DELETE /sessions/<sid>` | সেশন মুছুন |
| `GET/POST /profile/<user_id>` | long-term preference |

### ⭐ Streaming — Flask-এ যেভাবে করতে হয়

**সমস্যা:** Flask sync (WSGI), তাই `astream_events` (async generator) চলে না।

**সমাধান — Thread + Queue:**

```
┌─────────────────────────────────────────────────┐
│  Worker Thread                                  │
│    agent.invoke(..., callbacks=[handler])       │
│    প্রতিটা token/tool event → Queue.put()       │
└──────────────────┬──────────────────────────────┘
                   │ queue.Queue (thread-safe)
┌──────────────────▼──────────────────────────────┐
│  Main Thread (Flask generator)                  │
│    while True: item = q.get(); yield sse(item)  │
└─────────────────────────────────────────────────┘
```

```python
class QueueCallbackHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token, **kw):
        if token: self.q.put({"type": "token", "content": token})
    def on_tool_start(self, serialized, input_str, **kw):
        self.q.put({"type": "tool_start", "name": serialized.get("name")})

def worker():
    try:
        agent.invoke(payload, config={"configurable": {"session_id": sid},
                                      "callbacks": [handler]})
    except Exception as e:
        q.put({"type": "error", "message": str(e)})
    finally:
        q.put({"type": "done"})        # generator থামার সিগন্যাল
threading.Thread(target=worker, daemon=True).start()
```

**তিনটা জিনিস খেয়াল রাখুন:**

1. `finally`-তে `done` push **বাধ্যতামূলক** — না হলে exception-এ generator চিরকাল `q.get()`-এ আটকে থাকবে।
2. `app.run(threaded=True)` — worker thread চলতে দিতে হবে।
3. `X-Accel-Buffering: no` হেডার — nginx-এর পিছনে না দিলে streaming দেখা যাবে না।

**Streaming কেন দরকার?** ২-৩টা tool কল মানে ৫-৮ সেকেন্ড। ফাঁকা স্ক্রিনে ইউজার ভাবে হ্যাং করেছে। `tool_start` ইভেন্ট দিয়ে UI-তে দেখানো যায় *"প্রোডাক্ট খুঁজছি..."* — perceived latency নাটকীয়ভাবে কমে।

---

## ধাপ ১০ — Multi-Agent (LangGraph)

### কেন দরকার?

১০টা tool একটা এজেন্টে চলে। ৪০টা হলে: বিশাল prompt → বেশি খরচ; কাছাকাছি tool গুলো LLM গুলিয়ে ফেলে; সব business rule এক prompt-এ ঢোকানো অসম্ভব।

### Supervisor Pattern

```
                 ┌──────────────┐
   user ────────▶│  SUPERVISOR  │◀────────┐
                 └──────┬───────┘         │ result
                        │ route           │
      ┌─────────────────┼─────────────────┤
      ▼                 ▼                 ▼
discovery_agent    order_agent      return_agent
(৪টা tool)        (৩টা tool)       (৪টা tool)
```

Supervisor tool চালায় না — শুধু routing করে। প্রতিটা specialist-এর ছোট prompt + অল্প tool → accuracy বেশি।

### Routing — structured output

```python
class Route(BaseModel):
    next: Literal["discovery_agent", "order_agent", "return_agent", "FINISH"]
router_llm = llm.with_structured_output(Route)
```

টেক্সট parse না করে typed object — LLM ভুল নাম বলতে পারে না।

```bash
python -m app.graph       # অথবা POST /chat/multi
```

> **কখন কোনটা?** Tool ≤ ১০ এবং domain সরল হলে single agent-ই যথেষ্ট (কম latency — supervisor মানে প্রতি টার্নে একটা extra LLM রাউন্ড)। Tool বাড়লে বা domain-ভিত্তিক আলাদা rule দরকার হলে multi-agent।

---

## ধাপ ১১ — টেস্ট স্ক্রিপ্ট

### curl দিয়ে

```bash
curl http://localhost:8001/health
curl "http://localhost:8001/products?query=headphone&max_price=5000"
curl http://localhost:8001/returns/eligibility/ORD-2001

curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"5000 takar moddhe headphone dekhao","session_id":"t1","user_id":"U100"}'

# Streaming
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"ORD-1001 kothay ache?","session_id":"t1","user_id":"U100"}'

redis-cli KEYS 'chat:*'
curl http://localhost:8000/sessions/t1/history
```

### UI-তে ডেমো (এই ক্রমে)

```
১.  "hi"                                       → tool কল হবে না
২.  "5000 takar moddhe valo headphone ache?"   → search_products(max_price=5000)
৩.  "oi tar detail ta dao"                     → ⭐ memory কাজ করছে
৪.  "eta stock e ache?"                        → check_stock
৫.  "ORD-1001 er ki obostha?"                  → track_order
৬.  "amar recent order gulo dekhao"            → list_my_orders
৭.  "ORD-2002 return korte chai"               → ⭐ error handling (cancelled)
৮.  "ORD-2001 er saree ta return korbo"        → ⭐ confirmation চাইবে
৯.  "haan confirm"                             → RMA তৈরি
১০. "refund kobe pabo?"                        → get_store_policy
১১. "amar jonno kichu suggest koro"            → recommend_products
১২. "U200 er order dekhao" (U100 হিসেবে)        → ⭐ প্রত্যাখ্যান করবে
```

**৩, ৭, ৮, ১২ আলাদা করে দেখান** — এগুলোই প্রমাণ করে এটা নিছক LLM wrapper নয়, বরং মেমরি, error recovery, write-safety আর access control সহ একটা প্রকৃত এজেন্ট।

---

## ধাপ ১২ — প্রোডাকশন (Ubuntu, Docker ছাড়া)

### ১২.১ — Gunicorn

Flask-এর নিজের সার্ভার dev-only:

```bash
gunicorn -w 2 -k gthread --threads 8 --timeout 120 -b 127.0.0.1:8000 app.server:app
gunicorn -w 2 -k gthread --threads 4 -b 127.0.0.1:8001 dummy_api.main:app
```

> `-k gthread` **অবশ্যই** — ডিফল্ট `sync` worker-এ একটা streaming রিকোয়েস্ট পুরো worker আটকে রাখবে।
> `--timeout 120` — এজেন্টের tool কলে সময় লাগে, ডিফল্ট ৩০ সেকেন্ডে কেটে যাবে।

### ১২.২ — systemd

`/etc/systemd/system/shopmate-chat.service`:

```ini
[Unit]
Description=ShopMate Chat Server
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=ehz
WorkingDirectory=/home/ehz/apps/multi_agent_chatbot
Environment="PATH=/home/ehz/apps/multi_agent_chatbot/venv/bin"
ExecStart=/home/ehz/apps/multi_agent_chatbot/venv/bin/gunicorn \
    -w 2 -k gthread --threads 8 --timeout 120 \
    -b 127.0.0.1:8000 app.server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shopmate-chat
sudo journalctl -u shopmate-chat -f
```

`shopmate-api.service` একইভাবে (পোর্ট 8001, `dummy_api.main:app`)।

### ১২.৩ — Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_buffering off;        # ⚠️ streaming এর জন্য বাধ্যতামূলক
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## ধাপ ১৩ — পরবর্তী উন্নয়ন

**RAG দিয়ে সার্চ** — এখন keyword matching। ইউজার লেখে *"কানে ব্যথা করে না এমন হেডফোন"* — keyword মিলবে না। প্রোডাক্ট ডেসক্রিপশন embed করে **Redis Vector Search**-এ রাখুন (Redis তো আছেই), একটা `semantic_product_search` tool যোগ করুন। Hybrid (keyword + vector) সবচেয়ে ভালো।

**Guardrails** — প্রম্পট ইনজেকশন ফিল্টার · rate limit (Redis-এই: `INCR ratelimit:{user}:{minute}`) · PII মাস্কিং · ⚠️ **`user_id` কখনো LLM-এর হাতে ছাড়বেন না** — নাহলে ইউজার লিখতে পারে *"U200 এর অর্ডার দেখাও"*। এখন এটা session context থেকে আসে; প্রোডাকশনে tool-এর ভেতরেই server-side চেক বসান।

**Human handoff** — এজেন্ট পরপর ২ বার ব্যর্থ হলে, ইউজার রেগে গেলে, বা নিজে চাইলে। একটা `escalate_to_human` tool যেটা টিকিট তৈরি করে।

**Observability** — LangSmith (`LANGCHAIN_TRACING_V2=true`)। প্রতিটা tool call, টোকেন খরচ, latency ট্রেসে দেখা যায়। এজেন্ট ডিবাগে এটা ছাড়া চলে না।

**Evaluation** — ৩০-৫০টা টেস্ট কেস: `{প্রশ্ন, প্রত্যাশিত tool, প্রত্যাশিত তথ্য}`। মাপুন tool selection accuracy, argument accuracy, groundedness, task completion rate। Prompt বদলানোর পর চালান — নাহলে বুঝবেন না উন্নতি হলো নাকি regression।

**খরচ নিয়ন্ত্রণ** — `HISTORY_WINDOW` কমান · tool রেসপন্স slim · prompt caching · সাধারণ FAQ Redis ক্যাশ থেকে।

### ৪ সপ্তাহের রোডম্যাপ

| সপ্তাহ | কাজ | Deliverable |
|---|---|---|
| ১ | Dummy API + tools + single agent + Redis history | CLI-তে চলমান বট |
| ২ | Flask server + streaming + UI + guardrails | ডেমো-রেডি ওয়েব অ্যাপ |
| ৩ | LangGraph multi-agent + RAG + human handoff | স্কেলেবল আর্কিটেকচার |
| ৪ | Eval + LangSmith + systemd/nginx ডিপ্লয়মেন্ট | প্রোডাকশন রিলিজ |

---

## ধাপ ১৪ — সমস্যা ও সমাধান ⚠️

### সেটআপ / Ubuntu

| সমস্যা | কারণ ও সমাধান |
|---|---|
| `ModuleNotFoundError: No module named 'dummy_api'` | root থেকে `-m` দিয়ে চালান: `python -m dummy_api.main`। ফোল্ডার স্ট্রাকচার ও `__init__.py` আছে কিনা দেখুন (ধাপ ১) |
| `Command 'python' not found` — যদিও `(venv)` দেখাচ্ছে | venv ভাঙা (সাধারণত ফোল্ডার রিনেম করার পর)। `rm -rf venv && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` |
| `error: externally-managed-environment` | venv অ্যাক্টিভেট করুন — Ubuntu 24.04-এ system pip বন্ধ (PEP 668) |
| `ls` আউটপুটে ফোল্ডারের নামে স্পেস | `mv "name " name`, তারপর venv নতুন করে বানান |
| `python3 -m venv` কাজ করছে না | `sudo apt install -y python3-venv` |
| যাচাই করতে | `python -c "import dummy_api.data as d; print(len(d.PRODUCTS))"` → `10` আসবে |

### Redis

| সমস্যা | সমাধান |
|---|---|
| `ConnectionError` / `Connection refused` | `sudo systemctl start redis-server` · `redis-cli ping` |
| History মনে থাকছে না | প্রতি রিকোয়েস্টে একই `session_id` যাচ্ছে কিনা দেখুন |
| History কোথায় দেখব | `redis-cli KEYS 'chat:*'` → `redis-cli LRANGE chat:<sid> 0 -1` |

### Flask

| সমস্যা | সমাধান |
|---|---|
| `/returns/eligibility` কাজ করছে না | route order — `eligibility` রুট আগে declare করুন |
| Bangla অক্ষর `\u09be` হয়ে আসছে | `app.json.ensure_ascii = False` সেট আছে কিনা |
| `Port already in use` | `sudo lsof -i :8000` → `kill -9 <PID>` |
| gunicorn-এ timeout | `--timeout 120` বাড়ান |

### Agent

| সমস্যা | সমাধান |
|---|---|
| `agent_scratchpad` error | prompt-এ `MessagesPlaceholder("agent_scratchpad")` আছে কিনা |
| Tool কল হচ্ছেই না | docstring অস্পষ্ট — আরও স্পষ্ট করে লিখুন |
| এজেন্ট দাম বানিয়ে বলছে | system prompt-এ grounding rule জোরদার করুন, temperature কমান |
| Streaming-এ টোকেন আসছে না | (ক) `threaded=True` (খ) `get_conversational_agent(streaming=True)` (গ) gunicorn-এ `-k gthread` |
| Streaming হ্যাং | `worker()`-এর `finally`-তে `done` push হচ্ছে কিনা |
| খুব ধীর | `HISTORY_WINDOW` কমান, tool রেসপন্স slim করুন, streaming ব্যবহার করুন |

---

## দ্রুত রেফারেন্স

```bash
# একবার
bash setup_ubuntu.sh
nano .env                         # OPENAI_API_KEY

# প্রতিবার
cd ~/Downloads/multi_agent_chatbot
source venv/bin/activate
bash run_all.sh                   # → http://localhost:8501

# আলাদা আলাদা
python -m dummy_api.main          # :8001
python -m app.server              # :8000
streamlit run ui/streamlit_app.py # :8501
python -m app.agent               # CLI টেস্ট
python -m app.graph               # multi-agent CLI

# ডিবাগ
redis-cli ping
redis-cli KEYS 'chat:*'
tail -f logs/chat_server.log
curl http://localhost:8000/health
```
