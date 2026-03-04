# LegacyLens: AI Cost Analysis

## Development & Testing Costs (Actual)

### Embedding Generation — Voyage Code 2

| Item | Value |
|------|-------|
| Model | Voyage Code 2 (1536 dimensions) |
| Total chunks embedded | 13,613 |
| Average tokens per chunk | 379 |
| Total tokens embedded | ~5.16M tokens |
| Voyage Code 2 pricing | $0.12 per 1M tokens |
| **Total embedding cost** | **~$0.62** |

Note: Embedding is a one-time cost per ingestion run. Re-embedding is only required if chunking strategy changes. Query embeddings (single queries at ~20 tokens each) are negligible — even 10,000 queries would cost ~$0.02.

### LLM Answer Generation — Claude Sonnet 4.5

| Item | Value |
|------|-------|
| Model | claude-sonnet-4-5-20250929 |
| Estimated queries during development | ~300–500 |
| Average input tokens per query | ~1,500 (system prompt + 5 retrieved chunks with metadata) |
| Average output tokens per query | ~500 (generated answer) |
| Input pricing | $3.00 per 1M tokens |
| Output pricing | $15.00 per 1M tokens |
| Estimated input cost | 500 queries × 1,500 tokens = 750K tokens → ~$2.25 |
| Estimated output cost | 500 queries × 500 tokens = 250K tokens → ~$3.75 |
| **Total LLM cost (development)** | **~$6.00** |

### Vector Database — Pinecone

| Item | Value |
|------|-------|
| Plan | Free (Starter) tier |
| Vectors stored | 13,613 of 100,000 limit |
| Storage used | ~42MB of 2GB limit |
| Index | 1 of 5 allowed |
| **Total Pinecone cost** | **$0.00** |

### Infrastructure

| Service | Cost |
|---------|------|
| Railway (backend hosting) | Free tier ($5/mo credit) |
| Vercel (frontend hosting) | Free tier (hobby) |
| GitHub | Free |
| **Total infrastructure cost** | **$0.00** |

### Total Development Spend

| Component | Cost |
|-----------|------|
| Voyage Code 2 (embedding) | $0.62 |
| Claude Sonnet 4.5 (answer generation) | ~$6.00 |
| Pinecone (vector storage) | $0.00 |
| Infrastructure (Railway + Vercel) | $0.00 |
| **Total** | **~$6.62** |

---

## Production Cost Projections

### Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Queries per user per day | 5 | Active developer exploring a codebase |
| Average input tokens per query | 1,500 | System prompt + 5 retrieved chunks |
| Average output tokens per query | 500 | Generated answer with citations |
| Query embedding tokens | 20 | Single natural language question |
| Working days per month | 22 | Standard business month |
| Code understanding feature usage | 2 per user per day | Explain, Docs, Dependencies, Business Logic |
| Feature input tokens | 2,000 | Larger prompt templates |
| Feature output tokens | 800 | Longer generated explanations |

### Cost Breakdown by Scale

#### 100 Users/month

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Query embedding (Voyage) | 100 users × 5 queries × 22 days × 20 tokens = 220K tokens | $0.03 |
| LLM queries (Claude input) | 100 × 5 × 22 × 1,500 = 16.5M tokens | $49.50 |
| LLM queries (Claude output) | 100 × 5 × 22 × 500 = 5.5M tokens | $82.50 |
| Feature calls (Claude input) | 100 × 2 × 22 × 2,000 = 8.8M tokens | $26.40 |
| Feature calls (Claude output) | 100 × 2 × 22 × 800 = 3.52M tokens | $52.80 |
| Pinecone | Free tier (13,613 vectors) | $0.00 |
| Railway | Free tier sufficient | $0.00 |
| Vercel | Free tier sufficient | $0.00 |
| **Total** | | **~$211/mo** |

#### 1,000 Users/month

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Query embedding (Voyage) | 2.2M tokens | $0.26 |
| LLM queries (Claude input) | 165M tokens | $495.00 |
| LLM queries (Claude output) | 55M tokens | $825.00 |
| Feature calls (Claude input) | 88M tokens | $264.00 |
| Feature calls (Claude output) | 35.2M tokens | $528.00 |
| Pinecone | Standard plan (~$70/mo for higher throughput) | $70.00 |
| Railway | Pro plan ($20/mo) | $20.00 |
| Vercel | Pro plan ($20/mo) | $20.00 |
| **Total** | | **~$2,222/mo** |

#### 10,000 Users/month

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Query embedding (Voyage) | 22M tokens | $2.64 |
| LLM queries (Claude input) | 1.65B tokens | $4,950.00 |
| LLM queries (Claude output) | 550M tokens | $8,250.00 |
| Feature calls (Claude input) | 880M tokens | $2,640.00 |
| Feature calls (Claude output) | 352M tokens | $5,280.00 |
| Pinecone | Standard plan (higher read units) | $200.00 |
| Railway | Scaled compute ($100/mo) | $100.00 |
| Vercel | Pro plan | $20.00 |
| **Total** | | **~$21,443/mo** |

#### 100,000 Users/month

| Component | Calculation | Monthly Cost |
|-----------|-------------|-------------|
| Query embedding (Voyage) | 220M tokens | $26.40 |
| LLM queries (Claude input) | 16.5B tokens | $49,500.00 |
| LLM queries (Claude output) | 5.5B tokens | $82,500.00 |
| Feature calls (Claude input) | 8.8B tokens | $26,400.00 |
| Feature calls (Claude output) | 3.52B tokens | $52,800.00 |
| Pinecone | Enterprise plan | $1,000.00 |
| Railway | Multi-instance ($500/mo) | $500.00 |
| Vercel | Enterprise | $500.00 |
| **Total** | | **~$213,226/mo** |

### Summary Table

| Scale | Monthly Cost | Cost per User | Cost per Query |
|-------|-------------|---------------|----------------|
| 100 users | ~$211 | $2.11 | $0.06 |
| 1,000 users | ~$2,222 | $2.22 | $0.06 |
| 10,000 users | ~$21,443 | $2.14 | $0.06 |
| 100,000 users | ~$213,226 | $2.13 | $0.06 |

### Key Observations

**LLM costs dominate at all scales.** Embedding and vector database costs are negligible — even at 100,000 users, Voyage embedding costs under $30/month. Claude Sonnet 4.5 answer generation accounts for 99%+ of costs at every scale.

**Cost scales linearly.** Per-user cost remains stable at ~$2.13/month because the primary cost driver (LLM token consumption) scales directly with query volume. There are no significant economies or diseconomies of scale.

**Optimization strategies for production:**
- **Response caching:** Cache answers for identical or near-identical queries. Even a 20% cache hit rate saves ~$42,000/month at 100K users.
- **Model tiering:** Use Claude Haiku for simple queries (Code Explanation, Documentation Gen) and reserve Sonnet for complex queries (Business Logic, Dependencies). Haiku is ~10x cheaper per token.
- **Query batching:** For the Code Understanding features, batch multiple chunks into a single LLM call where possible.
- **Embedding model switch:** At extreme scale, local sentence-transformers would eliminate embedding API costs entirely, though quality may degrade for code-specific queries.

**Break-even analysis:** At a SaaS price point of $10/user/month, the service becomes profitable at any scale (cost per user ~$2.13). The primary risk is LLM pricing changes, not infrastructure costs.