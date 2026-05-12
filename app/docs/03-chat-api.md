# Chat API

The `/chat` endpoint accepts a JSON payload with two fields:

- `session_id`: an arbitrary string that identifies the conversation. Repeated calls with the same `session_id` retrieve the prior message history from Postgres so the agent can answer follow-up questions in context.
- `message`: the natural-language question from the user.

Example request:

```
curl -X POST http://VM_IP:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "my-session", "message": "How is the agent state stored?"}'
```

The response is a JSON object containing the generated answer and the names of the source documents that were retrieved as context. If the question cannot be answered from the indexed documents, the model is instructed to say so rather than fabricate.

Each session lives indefinitely in Postgres. To start a fresh conversation, pass a new `session_id`. There is no automatic session expiration in this minimal example, though you can add one easily by deleting LangGraph checkpoints on a schedule.
