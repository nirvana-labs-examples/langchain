# Adding your own documents

On first startup, the application checks whether the Qdrant collection is empty. If it is, the seed documents in `app/docs/` are chunked, embedded, and indexed automatically so you can test the deployment without any extra steps. After that initial seed, the application never re-ingests automatically.

To add new content after deployment, use the `/ingest` endpoint:

```
curl -X POST http://VM_IP:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "source": "release-notes",
        "texts": [
          "The 1.16 release introduces inline storage for HNSW indexes.",
          "Multi-tenancy can now use a tiered shard strategy."
        ]
      }'
```

Each string in `texts` is split into chunks of approximately 800 characters with a 120-character overlap, embedded, and stored in Qdrant. The `source` field is attached to every chunk and surfaced in `/chat` responses so users can see which documents informed each answer.

This endpoint is intentionally minimal: there is no auth, deduplication, or bulk-file upload. For a production deployment you would add an authentication layer, idempotent ingestion keys, and probably a background worker to handle large corpora.
