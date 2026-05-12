# Frequently asked questions

**Which LLM does the agent use?**
The agent calls a local Ollama model running on the same Nirvana VM. There is no external LLM API, no API key, and no third-party network call for inference. The default model is set via the `OLLAMA_MODEL` environment variable and defaults to `qwen2.5:3b-instruct`. Swap it for any model Ollama supports by changing that single value and restarting the stack.

**Does the application need any external API key?**
No. Both the embedding model (FastEmbed) and the language model (Ollama) run locally on the VM. The deployment requires only a Nirvana account for provisioning the VM itself.

**Why was a 3B model chosen as the default?**
A 3B-parameter model fits comfortably in memory on a `n1-standard-8` VM, leaves enough room for Qdrant, Postgres, Redis, and the FastAPI process, and produces usable answers on CPU within roughly ten seconds. Larger models such as `llama3.1:8b-instruct` or `qwen2.5:7b-instruct` produce better answers but take noticeably longer on CPU inference. A user who wants higher quality can pull a larger model and restart the stack.

**How are conversations remembered?**
Each `session_id` corresponds to a LangGraph thread persisted in Postgres. When the agent receives a follow-up message, LangGraph loads the prior turns from Postgres before invoking the retrieval and generation nodes, so conversation memory survives application restarts.

**Why is Redis included if the application can work without it?**
Redis records lightweight per-session activity such as turn counts and last-active timestamps. It is a stand-in for the kind of fast cache layer a real production agent would use for rate limiting, recently-seen queries, or hot session state. The deployment intentionally includes it so the stack mirrors a realistic production deployment.

**Can the agent answer questions outside the seeded documents?**
The system prompt instructs the model to ground answers in the retrieved context and to admit when the answer is not contained in the documents. The model may still use general knowledge for definitional questions, but it should refuse to invent specifics that the documents do not support.
