# About this application

This is a minimal RAG (retrieval-augmented generation) agent deployed on Nirvana Labs infrastructure. It demonstrates a typical LangChain production stack: a vector store for retrieval, a relational database for conversation state, and a Large Language Model for response generation.

When a user sends a question to the `/chat` endpoint, the application:

1. Embeds the question using a local FastEmbed model.
2. Searches the Qdrant vector store for the four most semantically similar document chunks.
3. Constructs a prompt that includes those chunks as grounded context.
4. Calls an Anthropic Claude model to produce an answer grounded in the retrieved context.
5. Saves the conversation turn to Postgres so subsequent messages in the same session preserve context.

This pattern is the foundation of most production LangChain deployments, from internal knowledge-base assistants to customer-facing support agents.
