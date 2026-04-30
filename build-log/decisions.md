# Decisions log

Running architectural decisions. Format per accountability-plan.md §"Decisions log — tracked artifact".

Anticipated entries to fill in as Phase 1 lands:
- Postgres + pgvector over DynamoDB + dedicated vector DB
- Postgres SKIP LOCKED queue over Redis Streams or SQS
- In-process LRU cache over Redis for single-instance deploy
- SSE over WebSockets for streaming LLM responses
- Postgres FTS over Elasticsearch for the corpus size
- S3 + presigned URLs over API-server-mediated uploads
- Redis for rate limiting only
- CLIP + text-embedding-3 architecture choice
- Hybrid retrieval pipeline shape (filter → vector → rerank)
