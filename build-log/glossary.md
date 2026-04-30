# Musarde — Glossary

Running list of terms that are new-ish for me in this project. The point isn't an ML textbook — it's a quick reference of things I've actually had to learn for Musarde, with enough context to remember why they matter here.

**Format per entry:**
- One-line definition.
- One-to-three sentences on what it does in *this* project.
- Where applicable: where the trade-off lives (interview-talking-point territory).

**How to extend:** add an entry whenever I ask Claude (or a doc, or a paper) to explain a term. If the term has a real architectural choice attached, also add the decision to `/build-log/decisions.md`. Glossary is for vocabulary; decisions log is for what I picked and why.

---

## Vision & multimodal

**CLIP** — Image-text dual encoder. Takes an image *or* a caption and maps it to a ~512–768-dimensional vector, trained contrastively so that an image and its caption land near each other in vector space.
- Default backbone for the in-gallery vision feature: phone photo → CLIP embedding → nearest-neighbor in indexed collection.
- Known failure modes that drive Musarde's eval design: near-identical compositions (Monet haystacks), text-heavy works (Jenny Holzer, Barbara Kruger), fine-grained distinctions within a tight visual category, heavy perspective distortion. The SAM ~100-work distribution and the Week 7 hybrid retrieval exist *because* of these.

**OpenCLIP** — Community reimplementation/retraining of CLIP. The thing people actually use when they say "CLIP" in 2026 — original OpenAI CLIP isn't really maintained as a product. Default variant: ViT-L/14 trained on LAION-2B.

**SigLIP** — Google's CLIP-alternative. Uses sigmoid loss instead of CLIP's softmax contrastive loss; outperforms CLIP on most public retrieval benchmarks, especially with smaller batch sizes.
- The OpenCLIP-vs-SigLIP decision is in the Week 1 checklist. SigLIP gives a stronger interview talking point (specific reason why), OpenCLIP gives ecosystem maturity.

**Image embedding** — A vector representation of an image. With CLIP, ~512–768 dimensions. Stored in pgvector alongside the artwork row. Similarity = cosine distance.

**Multimodal** — Working across modalities (image + text). CLIP is the canonical multimodal model: it can compare an image to a caption directly because they share a vector space.

**Vision encoder / ViT** — Vision Transformer. The architecture inside CLIP that turns an image into a vector. ViT-L/14 means a "large" variant operating on 14×14 image patches.

---

## Text embeddings

**text-embedding-3-small / -large** — OpenAI's text embedding models. Small is 1536d, large is 3072d. The current v1 default; flagged as the weakest stack pick — Voyage-3 beats it on retrieval benchmarks.

**MTEB** — Massive Text Embedding Benchmark. The standard public leaderboard for comparing text embedding models on retrieval, classification, clustering, etc. The thing to check before defaulting to a popular embedding model.

**Matryoshka embeddings** — Embeddings trained so that truncating to fewer dimensions still produces useful similarity. Lets you store a smaller vector (e.g. 512d from a 1536d model) for ~3x storage and pgvector latency win at <2% quality loss.

---

## Retrieval & RAG

**RAG (Retrieval-Augmented Generation)** — Pattern: before asking the LLM to answer, retrieve top-k relevant chunks from your corpus and stuff them into the prompt. The model answers from those documents instead of (or in addition to) its parametric memory.
- Used in Week 5 reading companion. The senior story is never "I built RAG" — it's the eval that distinguishes a working RAG from a broken one.
- Solves three LLM problems: doesn't know your data, hallucinates confidently, has stale knowledge.

**Chunking** — Splitting documents into smaller pieces for embedding/retrieval. Trade-off: too small → loses context; too large → retrieval imprecise, blows context budget. Week 5 decision: fixed-size + overlap vs. semantic-boundary chunking.

**Top-k / retrieval k** — Number of chunks (or items) retrieved before generation. Typical k for RAG: 5–20 depending on chunk size and prompt budget.

**BM25** — Classic lexical (keyword-based) retrieval algorithm. Old but very strong; complements vector search well because it catches exact-match cases vector search misses.

**Hybrid retrieval** — Combining vector search + lexical (BM25 / Postgres FTS) + (optionally) LLM rerank. The thing that closes the gap when pure CLIP/embedding retrieval hits a ceiling. Week 7 deliverable.

**Reranker** — A second-stage scorer that reorders the top-k from initial retrieval. Slow but accurate. Three flavors: none / cross-encoder (BGE-reranker, Cohere Rerank) / LLM-as-judge.

**Cross-encoder** — Reranker architecture that takes (query, candidate) as a single joint input and outputs a relevance score. More accurate than dual-encoder vector similarity but quadratic in cost — only feasible for re-scoring a small candidate set.

**LLM-as-judge** — Using an LLM to score relevance / quality directly via prompt. Most flexible reranker option, also most expensive and slowest. Useful when domain expertise matters (which it does for art writing).

**Query rewriting** — Reformulating the user's query before retrieval, e.g. expanding "is this work about death" → "mortality, the funereal, memento mori." A common fix for query–document vocabulary mismatch.

**Iterative retrieval** — Retrieve once, look at the results, generate a follow-up query, retrieve again. Handles multi-hop questions that single-shot retrieval can't. The "light" version (one conditional follow-up round) is Week 5; full agentic RAG is out of scope for v1.

**Multi-hop question** — A question whose answer requires combining information from multiple retrieved chunks across multiple retrieval steps. "What earlier work by this artist does this piece reference?" — needs the current work's description first, then a different artwork by the same artist.

**Held-out work** — In the Week 5 eval: an artwork whose criticism is *not* in the corpus, used to measure generalization rather than memorization. Verify with grep, not intuition.

---

## Agents & tool use

**Tool use / function calling** — LLM API feature where the model can choose to call structured tools (functions you define) instead of just generating text. The model returns a tool-call request; you execute it; you feed the result back; loop until the model is done.
- Week 2 deliverable is a planning agent built on raw Claude function-calling API, not a framework.

**Agent loop** — The control flow around tool use: send prompt → model decides (text or tool call) → if tool call, execute and feed result back → repeat → stop on terminal condition. Loop semantics are what get defended in interviews.

**Tool surface** — The set of tools exposed to the agent and their signatures. Week 2 surface: `search_collection`, `filter_by_metadata`, `estimate_time_budget`, `lookup_artist_context`, `find_related_works`.
- Granularity trade-off (a Week 2 decision): one mega-tool vs. fine composable tools. Composable wins for observability and debugging; mega-tools win for fewer LLM steps.

**Termination policy** — How the agent decides to stop. Combinations of: max steps (5–8 in Week 2), hard timeout, "good enough" signal from the model, repeated-state detection. Without a real policy, agents loop forever.

**Agent trace / observability** — Per-step log of (step number, tool called, args, result, model reasoning, latency, cost). The artifact that turns "I built an agent" into "I instrumented an agent." Persisted to Postgres in Week 2.

**History management** — How prior tool calls and results are kept in the prompt across loop iterations. Three flavors: full (expensive, blows context), summarized (cheaper, lossy), windowed (last N). Decision in Week 2.

**Raw API vs. framework** — Building agent control flow against the raw Claude function-calling API vs. using something like LangGraph. The Week 1 Day 7 decision; raw API wins here because the loop is simple enough that explicit control beats opaque framework behavior.

---

## Linked data (Getty / Week 6)

**Linked Open Data (LOD)** — Pattern of publishing structured data on the web with stable URIs and machine-readable links between resources. Getty publishes its collection this way; Met (CSV) and AIC (REST) do not.
- The most architecturally novel adapter in v1. The interview answer for "what's the hardest integration" lives here.

**RDF (Resource Description Framework)** — Data model where everything is expressed as (subject, predicate, object) triples. The substrate beneath JSON-LD and SPARQL.

**JSON-LD** — JSON serialization of RDF. Looks like normal nested JSON but has a `@context` that maps keys to URIs. For v1 Getty parsing: treat as nested JSON with known shapes; full JSON-LD library (pyld) is overkill.

**SPARQL** — Query language for RDF data. Like SQL but for graphs. Getty exposes a SPARQL endpoint at `data.getty.edu`. The Week 6 fetch-strategy decision is SPARQL crawl vs. bulk export.

**Linked Art** — Domain-specific data model for cultural heritage built on top of JSON-LD/RDF. Getty's collection data is in this format. Has typed nodes (Production, Artist, Place, Material) rather than flat records — meaning a single artwork is a small graph, not a row.

**Production event** — In Linked Art, the model for "this artwork was made." Each artwork can have multiple production events (creation, casting, restoration); the Week 6 normalization picks the original creation.

**IIIF (International Image Interoperability Framework)** — Standard for serving images at scale, used by AIC, Getty, and many others. Each artwork has a manifest URL; the manifest tells you how to fetch the image at any size/region.

---

## ML ops (LLM/embedding-flavored)

**Embedding model versioning** — Storing `embedding_model_version` alongside every vector so that, when the model changes, you can re-embed incrementally and serve a consistent index. Week 1 design.

**Batched ML inference** — Running embedding generation in batches with checkpointing, idempotency, retry/DLQ. The pattern that turns "generate CLIP embeddings" from a script into a real pipeline. Closest analogue to the Alexa-recommendation-platform shape.

**Content-addressed cache** — Cache keyed by hash-of-inputs (model, prompt, params). Embeddings are deterministic given input + version, so they cache trivially. LLM responses cache the same way at temperature 0 with a stable prompt. 10x dev cost reduction.

**A/B retrieval infrastructure** — Running multiple retrieval strategies in parallel, routing a percentage of queries to each, logging results with strategy tags, analyzing offline. The infrastructure story behind hybrid retrieval — "I shipped a system that lets us safely change models," not "I shipped a model."

**Continuous eval harness** — Pipeline that re-runs the eval suite on every meaningful change (new prompt, new embedding model, new retrieval strategy), tracks scores over time, catches regressions before merge. Week 11 deliverable if continuing past Week 6.

**ML observability / structured logging** — Per-call logging of (input hash, model, latency, token count, cost, output hash) for every LLM and embedding call. Aggregated into Postgres for queryable metrics. The optional 6th resume bullet rides on this producing a real finding.

---

## Eval methodology

**Top-k accuracy** — Fraction of queries where the correct answer appears in the top-k results. The headline metric for the SAM multimodal eval (top-5).

**Comprehension-rubric eval** — Eval format for the Week 5 reading companion: read the explanation → answer 3 questions about the work → score the answers. Stress-tests whether the explanation actually conveys understanding, not just plausibility.

**Three-way comparison / ablation** — Comparing three system variants on the same eval to isolate the contribution of each component. Week 5: vanilla LLM no-RAG / single-shot RAG / iterative RAG.

**Generalization vs. memorization** — Eval design concern: if the held-out questions' answers are already in the training corpus, you're measuring memorization, not generalization. Hence the grep check on held-out works' criticism in Week 5.

**Eval set capture protocol** — The discipline of collecting eval data with enough metadata that ground-truth pairing isn't ambiguous later. Week 4: photo of work + photo of label + condition tags, paired by timestamp or explicit key.

---

## Things I already know but worth pinning here for completeness

(Skim — these are well-known from Amazon work, listed only because they show up in interview-talking-point conversations.)

**pgvector** — Postgres extension for vector similarity search. Cosine / L2 / inner product distance over up to ~16K-dim vectors. Indexed via IVFFlat or HNSW.

**SSE (Server-Sent Events)** — One-way HTTP streaming from server to client. Used for streaming LLM responses to the in-gallery PWA. Picked over WebSockets because the channel is one-way and SSE plays better with Vercel's serverless model.

**Presigned S3 URL** — Short-lived URL that lets a client upload directly to S3 without going through the API server. Used for in-gallery photo upload.

**SKIP LOCKED** — Postgres clause that lets multiple workers dequeue jobs without blocking each other. The basis of the Postgres-backed embedding job queue.

**Postgres FTS** — Postgres's built-in full-text search. The lexical half of hybrid retrieval; chosen over Elasticsearch for operational simplicity at this scale.

**DLQ (Dead Letter Queue)** — Where jobs go after exhausting retries. Standard ingestion-pipeline fault tolerance.

---

## Pointer back to chats

If I want to re-read the long-form versions of any of these, the deepest explainers were in the Apr 30 chats: project plan review (CLIP failure modes, RAG mechanics, Linked Open Data shape) and stack-decisions stress test (CLIP/SigLIP/embedding alternatives, cost flags). Listed here so future me doesn't have to grep blindly.