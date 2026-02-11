# Memory & Persistence System - OpenClaw Code Extraction

**Source**: OpenClaw Memory implementation  
**Purpose**: Reference for building Emonk's memory/persistence system  
**Extraction Date**: 2026-02-11

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Memory Manager](#memory-manager)
3. [File-Based Storage](#file-based-storage)
4. [Embedding System](#embedding-system)
5. [Vector Search](#vector-search)
6. [Hybrid Search (FTS + Vector)](#hybrid-search-fts--vector)
7. [Caching Strategy](#caching-strategy)
8. [Key Takeaways](#key-takeaways)
9. [Emonk Adaptations](#emonk-adaptations)

---

## Architecture Overview

### Memory System Purpose

OpenClaw's memory system provides:
- **Persistent storage** for agent knowledge (markdown files)
- **Vector search** for semantic similarity
- **Full-text search** for keyword matching
- **Hybrid search** combining both approaches
- **Automatic sync** with filesystem watches

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│            Memory Index Manager                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │       File System Watcher                   │         │
│  │   - Monitor MEMORY.md                      │         │
│  │   - Monitor memory/                        │         │
│  │   - Auto-sync on changes                   │         │
│  └─────────────┬──────────────────────────────┘         │
│                │                                          │
│                ▼                                          │
│  ┌────────────────────────────────────────────┐         │
│  │         SQLite Database                     │         │
│  │   ┌────────────────────────────┐           │         │
│  │   │  chunks_vec                │           │         │
│  │   │  (Vector embeddings)       │           │         │
│  │   └────────────────────────────┘           │         │
│  │   ┌────────────────────────────┐           │         │
│  │   │  chunks_fts                │           │         │
│  │   │  (Full-text search)        │           │         │
│  │   └────────────────────────────┘           │         │
│  │   ┌────────────────────────────┐           │         │
│  │   │  embedding_cache           │           │         │
│  │   │  (Cached embeddings)       │           │         │
│  │   └────────────────────────────┘           │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
│  ┌────────────────────────────────────────────┐         │
│  │      Embedding Provider                     │         │
│  │   - OpenAI (text-embedding-3-small)        │         │
│  │   - Gemini (text-embedding-004)            │         │
│  │   - Voyage (voyage-3)                      │         │
│  │   - Local (llama.cpp)                      │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│   MEMORY.md      │       │  memory/*.md     │
│   (Root file)    │       │  (Subdirectory)  │
└──────────────────┘       └──────────────────┘
```

### Key Design Patterns

1. **File-Based**: Store knowledge in markdown files
2. **Auto-Sync**: Watch filesystem for changes
3. **Chunking**: Split large files into searchable chunks
4. **Caching**: Cache embeddings to reduce API calls
5. **Hybrid Search**: Combine vector + keyword search

---

## Memory Manager

### Overview

The Memory Manager (`src/memory/manager.ts`) is the main entry point for memory operations.

### Memory Index Manager Class

```typescript
export class MemoryIndexManager implements MemorySearchManager {
  private readonly cfg: OpenClawConfig;
  private readonly agentId: string;
  private readonly workspaceDir: string;
  private readonly settings: ResolvedMemorySearchConfig;
  private provider: EmbeddingProvider;
  private db: DatabaseSync;                      // SQLite database
  private readonly sources: Set<MemorySource>;   // "memory" | "sessions"
  private watcher: FSWatcher | null = null;      // Chokidar file watcher
  private dirty = false;                         // Needs sync flag
  private syncing: Promise<void> | null = null;  // Sync in progress
  
  // Constants
  private static readonly META_KEY = "memory_index_meta_v1";
  private static readonly VECTOR_TABLE = "chunks_vec";
  private static readonly FTS_TABLE = "chunks_fts";
  private static readonly EMBEDDING_CACHE_TABLE = "embedding_cache";
  private static readonly SESSION_DIRTY_DEBOUNCE_MS = 5000;
  private static readonly EMBEDDING_BATCH_MAX_TOKENS = 8000;
  private static readonly SNIPPET_MAX_CHARS = 700;
  
  static async get(params: {
    cfg: OpenClawConfig;
    agentId: string;
  }): Promise<MemoryIndexManager | null> {
    const settings = resolveMemorySearchConfig(cfg, agentId);
    if (!settings) {
      return null;
    }
    
    // Check cache
    const workspaceDir = resolveAgentWorkspaceDir(cfg, agentId);
    const key = `${agentId}:${workspaceDir}:${JSON.stringify(settings)}`;
    const existing = INDEX_CACHE.get(key);
    if (existing) {
      return existing;
    }
    
    // Create new manager
    const providerResult = await createEmbeddingProvider({
      config: cfg,
      agentDir: resolveAgentDir(cfg, agentId),
      provider: settings.provider,
      model: settings.model,
      fallback: settings.fallback,
    });
    
    const manager = new MemoryIndexManager({
      cacheKey: key,
      cfg,
      agentId,
      workspaceDir,
      settings,
      providerResult,
    });
    
    INDEX_CACHE.set(key, manager);
    return manager;
  }
  
  private constructor(params: {
    cacheKey: string;
    cfg: OpenClawConfig;
    agentId: string;
    workspaceDir: string;
    settings: ResolvedMemorySearchConfig;
    providerResult: EmbeddingProviderResult;
  }) {
    this.cacheKey = params.cacheKey;
    this.cfg = params.cfg;
    this.agentId = params.agentId;
    this.workspaceDir = params.workspaceDir;
    this.settings = params.settings;
    this.provider = params.providerResult.provider;
    this.sources = new Set(params.settings.sources);
    
    // Open/create database
    this.db = this.openDatabase();
    this.ensureSchema();
    
    // Set up filesystem watcher
    this.ensureWatcher();
    
    // Mark dirty if memory source enabled
    this.dirty = this.sources.has("memory");
  }
  
  private openDatabase(): DatabaseSync {
    const agentDir = resolveAgentDir(this.cfg, this.agentId);
    const dbPath = path.join(agentDir, "memory-index.db");
    ensureDir(path.dirname(dbPath));
    
    // Use node:sqlite (built-in from Node 22.5+)
    const sqlite = requireNodeSqlite();
    const db = new sqlite.DatabaseSync(dbPath);
    
    // Enable WAL mode for better concurrency
    db.exec("PRAGMA journal_mode = WAL");
    db.exec("PRAGMA synchronous = NORMAL");
    
    return db;
  }
  
  private ensureSchema() {
    // Create tables if they don't exist
    ensureMemoryIndexSchema(this.db);
    
    // Load sqlite-vec extension for vector similarity
    if (this.settings.store.vector.enabled) {
      loadSqliteVecExtension(this.db, this.settings.store.vector.extensionPath);
    }
  }
}
```

### File System Watcher

```typescript
private ensureWatcher() {
  if (this.watcher) {
    return;
  }
  
  if (!this.sources.has("memory")) {
    return;
  }
  
  // Watch MEMORY.md and memory/ directory
  const watchPaths = [
    path.join(this.workspaceDir, "MEMORY.md"),
    path.join(this.workspaceDir, "memory.md"),
    path.join(this.workspaceDir, "memory"),
  ];
  
  this.watcher = chokidar.watch(watchPaths, {
    ignoreInitial: true,
    persistent: true,
    awaitWriteFinish: {
      stabilityThreshold: 500,  // Wait 500ms after last change
      pollInterval: 100,
    },
  });
  
  // Debounce changes
  let timer: NodeJS.Timeout | null = null;
  const markDirty = () => {
    if (timer) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => {
      this.dirty = true;
      this.triggerSync();
    }, 1000);
  };
  
  this.watcher.on("add", markDirty);
  this.watcher.on("change", markDirty);
  this.watcher.on("unlink", markDirty);
}
```

### Sync Operation

```typescript
async sync(params?: {
  force?: boolean;
  report?: (update: MemorySyncProgressUpdate) => void;
}): Promise<void> {
  if (this.syncing) {
    return this.syncing;  // Already syncing
  }
  
  if (!params?.force && !this.dirty) {
    return;  // Nothing to sync
  }
  
  this.syncing = this.runSync(params);
  try {
    await this.syncing;
    this.dirty = false;
  } finally {
    this.syncing = null;
  }
}

private async runSync(params?: {
  report?: (update: MemorySyncProgressUpdate) => void;
}): Promise<void> {
  const report = params?.report ?? (() => {});
  
  // 1. List all memory files
  const files = await listMemoryFiles(this.workspaceDir);
  report({ phase: "scanning", completed: 0, total: files.length });
  
  // 2. Build file entries with hashes
  const entries: MemoryFileEntry[] = [];
  for (const absPath of files) {
    const entry = await buildFileEntry(absPath, this.workspaceDir);
    entries.push(entry);
  }
  
  // 3. Determine which files need reindexing
  const toIndex: MemoryFileEntry[] = [];
  for (const entry of entries) {
    const existing = this.db.prepare(
      "SELECT hash FROM chunks_vec WHERE source_path = ? LIMIT 1"
    ).get(entry.path);
    
    if (!existing || existing.hash !== entry.hash) {
      toIndex.push(entry);
    }
  }
  
  if (toIndex.length === 0) {
    report({ phase: "complete", completed: entries.length, total: entries.length });
    return;
  }
  
  report({ phase: "indexing", completed: 0, total: toIndex.length });
  
  // 4. Remove old chunks for files being reindexed
  const stmt = this.db.prepare("DELETE FROM chunks_vec WHERE source_path = ?");
  for (const entry of toIndex) {
    stmt.run(entry.path);
  }
  
  // 5. Chunk and embed each file
  let completed = 0;
  for (const entry of toIndex) {
    await this.indexFile(entry);
    completed++;
    report({ phase: "indexing", completed, total: toIndex.length });
  }
  
  report({ phase: "complete", completed: entries.length, total: entries.length });
}
```

---

## File-Based Storage

### Overview

Memory files are stored in markdown format in predictable locations:
- `MEMORY.md` (root file)
- `memory/` directory (multiple files)

### Memory File Structure

```markdown
# Brand Voice Guidelines

## Core Values
- Authentic, data-driven insights
- No hype or empty promises
- Technical but accessible

## Tone Guidelines
- Use "we" not "I" (team voice)
- Lead with questions, not declarations
- Include concrete examples

## Writing Style
- Sentence length: 10-20 words average
- Active voice preferred
- Minimize jargon

## Forbidden Phrases
- "Game-changer", "Revolutionary"
- "Unlock", "Secrets", "Hack"
```

### File Discovery

```typescript
export async function listMemoryFiles(
  workspaceDir: string,
  extraPaths?: string[],
): Promise<string[]> {
  const result: string[] = [];
  
  // Check root MEMORY.md files
  const memoryFile = path.join(workspaceDir, "MEMORY.md");
  const altMemoryFile = path.join(workspaceDir, "memory.md");
  
  const addMarkdownFile = async (absPath: string) => {
    try {
      const stat = await fs.lstat(absPath);
      if (stat.isSymbolicLink() || !stat.isFile()) {
        return;
      }
      if (!absPath.endsWith(".md")) {
        return;
      }
      result.push(absPath);
    } catch {}
  };
  
  await addMarkdownFile(memoryFile);
  await addMarkdownFile(altMemoryFile);
  
  // Walk memory/ directory
  const memoryDir = path.join(workspaceDir, "memory");
  try {
    const dirStat = await fs.lstat(memoryDir);
    if (!dirStat.isSymbolicLink() && dirStat.isDirectory()) {
      await walkDir(memoryDir, result);
    }
  } catch {}
  
  // Add extra paths (from config)
  const normalizedExtraPaths = normalizeExtraMemoryPaths(workspaceDir, extraPaths);
  for (const inputPath of normalizedExtraPaths) {
    try {
      const stat = await fs.lstat(inputPath);
      if (stat.isDirectory()) {
        await walkDir(inputPath, result);
      } else if (stat.isFile() && inputPath.endsWith(".md")) {
        result.push(inputPath);
      }
    } catch {}
  }
  
  // Deduplicate via realpath
  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const entry of result) {
    let key = entry;
    try {
      key = await fs.realpath(entry);
    } catch {}
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(entry);
  }
  
  return deduped;
}
```

### File Entry Building

```typescript
export async function buildFileEntry(
  absPath: string,
  workspaceDir: string,
): Promise<MemoryFileEntry> {
  const stat = await fs.stat(absPath);
  const content = await fs.readFile(absPath, "utf-8");
  const hash = hashText(content);  // SHA-256
  
  return {
    path: path.relative(workspaceDir, absPath).replace(/\\/g, "/"),
    absPath,
    mtimeMs: stat.mtimeMs,
    size: stat.size,
    hash,
  };
}

export function hashText(value: string): string {
  return crypto.createHash("sha256").update(value).digest("hex");
}
```

---

## Embedding System

### Overview

The Embedding System converts text chunks into vector embeddings for semantic search.

### Embedding Providers

OpenClaw supports multiple embedding providers with automatic fallback:

```typescript
export type EmbeddingProvider = {
  id: string;
  model: string;
  maxInputTokens?: number;
  embedQuery: (text: string) => Promise<number[]>;
  embedBatch: (texts: string[]) => Promise<number[][]>;
};

export async function createEmbeddingProvider(
  options: EmbeddingProviderOptions,
): Promise<EmbeddingProviderResult> {
  const requestedProvider = options.provider;
  const fallback = options.fallback;
  
  // Provider creation
  const createProvider = async (id: "openai" | "local" | "gemini" | "voyage") => {
    if (id === "local") {
      return await createLocalEmbeddingProvider(options);
    }
    if (id === "gemini") {
      return await createGeminiEmbeddingProvider(options);
    }
    if (id === "voyage") {
      return await createVoyageEmbeddingProvider(options);
    }
    return await createOpenAiEmbeddingProvider(options);
  };
  
  // Auto-select provider
  if (requestedProvider === "auto") {
    // Try local if model file exists
    if (canAutoSelectLocal(options)) {
      try {
        const local = await createProvider("local");
        return { ...local, requestedProvider };
      } catch (err) {
        // Continue to remote providers
      }
    }
    
    // Try remote providers in order
    for (const provider of ["openai", "gemini", "voyage"] as const) {
      try {
        const result = await createProvider(provider);
        return { ...result, requestedProvider };
      } catch (err) {
        if (isMissingApiKeyError(err)) {
          continue;  // Try next provider
        }
        throw err;  // Fatal error
      }
    }
    
    throw new Error("No embeddings provider available.");
  }
  
  // Try requested provider with fallback
  try {
    const primary = await createProvider(requestedProvider);
    return { ...primary, requestedProvider };
  } catch (primaryErr) {
    if (fallback && fallback !== "none" && fallback !== requestedProvider) {
      try {
        const fallbackResult = await createProvider(fallback);
        return {
          ...fallbackResult,
          requestedProvider,
          fallbackFrom: requestedProvider,
          fallbackReason: formatErrorMessage(primaryErr),
        };
      } catch (fallbackErr) {
        throw primaryErr;  // Report primary error
      }
    }
    throw primaryErr;
  }
}
```

### OpenAI Embedding Provider

```typescript
export const DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small";

async function createOpenAiEmbeddingProvider(
  options: EmbeddingProviderOptions,
): Promise<{ provider: EmbeddingProvider; client: OpenAiEmbeddingClient }> {
  const apiKey = resolveOpenAiApiKey(options.config);
  if (!apiKey) {
    throw new Error("No API key found for provider: openai");
  }
  
  const client = new OpenAI({
    apiKey,
    baseURL: options.remote?.baseUrl,
  });
  
  const provider: EmbeddingProvider = {
    id: "openai",
    model: options.model || DEFAULT_OPENAI_EMBEDDING_MODEL,
    maxInputTokens: 8191,  // text-embedding-3-small limit
    
    embedQuery: async (text: string) => {
      const response = await client.embeddings.create({
        model: options.model || DEFAULT_OPENAI_EMBEDDING_MODEL,
        input: text,
        encoding_format: "float",
      });
      return response.data[0].embedding;
    },
    
    embedBatch: async (texts: string[]) => {
      const response = await client.embeddings.create({
        model: options.model || DEFAULT_OPENAI_EMBEDDING_MODEL,
        input: texts,
        encoding_format: "float",
      });
      return response.data.map((item) => item.embedding);
    },
  };
  
  return { provider, client };
}
```

### Local Embedding Provider (llama.cpp)

```typescript
const DEFAULT_LOCAL_MODEL = "hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf";

async function createLocalEmbeddingProvider(
  options: EmbeddingProviderOptions,
): Promise<EmbeddingProvider> {
  const modelPath = options.local?.modelPath?.trim() || DEFAULT_LOCAL_MODEL;
  const modelCacheDir = options.local?.modelCacheDir?.trim();
  
  // Lazy-load node-llama-cpp
  const { getLlama, resolveModelFile, LlamaLogLevel } = await importNodeLlamaCpp();
  
  let llama: Llama | null = null;
  let embeddingModel: LlamaModel | null = null;
  let embeddingContext: LlamaEmbeddingContext | null = null;
  
  const ensureContext = async () => {
    if (!llama) {
      llama = await getLlama({ logLevel: LlamaLogLevel.error });
    }
    if (!embeddingModel) {
      const resolved = await resolveModelFile(modelPath, modelCacheDir || undefined);
      embeddingModel = await llama.loadModel({ modelPath: resolved });
    }
    if (!embeddingContext) {
      embeddingContext = await embeddingModel.createEmbeddingContext();
    }
    return embeddingContext;
  };
  
  return {
    id: "local",
    model: modelPath,
    
    embedQuery: async (text) => {
      const ctx = await ensureContext();
      const embedding = await ctx.getEmbeddingFor(text);
      return sanitizeAndNormalizeEmbedding(Array.from(embedding.vector));
    },
    
    embedBatch: async (texts) => {
      const ctx = await ensureContext();
      const embeddings = await Promise.all(
        texts.map(async (text) => {
          const embedding = await ctx.getEmbeddingFor(text);
          return sanitizeAndNormalizeEmbedding(Array.from(embedding.vector));
        }),
      );
      return embeddings;
    },
  };
}

function sanitizeAndNormalizeEmbedding(vec: number[]): number[] {
  // Replace NaN/Inf with 0
  const sanitized = vec.map((value) => (Number.isFinite(value) ? value : 0));
  
  // Normalize to unit length
  const magnitude = Math.sqrt(sanitized.reduce((sum, value) => sum + value * value, 0));
  if (magnitude < 1e-10) {
    return sanitized;
  }
  return sanitized.map((value) => value / magnitude);
}
```

### Chunking Strategy

```typescript
export function chunkMarkdown(
  content: string,
  chunking: { tokens: number; overlap: number },
): MemoryChunk[] {
  const lines = content.split("\n");
  const maxChars = Math.max(32, chunking.tokens * 4);  // ~4 chars per token
  const overlapChars = Math.max(0, chunking.overlap * 4);
  const chunks: MemoryChunk[] = [];
  
  let current: Array<{ line: string; lineNo: number }> = [];
  let currentChars = 0;
  
  const flush = () => {
    if (current.length === 0) {
      return;
    }
    const text = current.map((entry) => entry.line).join("\n");
    const startLine = current[0].lineNo;
    const endLine = current[current.length - 1].lineNo;
    chunks.push({
      startLine,
      endLine,
      text,
      hash: hashText(text),
    });
  };
  
  const carryOverlap = () => {
    // Keep last N chars for overlap
    if (overlapChars <= 0 || current.length === 0) {
      current = [];
      currentChars = 0;
      return;
    }
    let acc = 0;
    const kept: Array<{ line: string; lineNo: number }> = [];
    for (let i = current.length - 1; i >= 0; i -= 1) {
      const entry = current[i];
      acc += entry.line.length + 1;
      kept.unshift(entry);
      if (acc >= overlapChars) {
        break;
      }
    }
    current = kept;
    currentChars = kept.reduce((sum, entry) => sum + entry.line.length + 1, 0);
  };
  
  // Process each line
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i] ?? "";
    const lineNo = i + 1;
    const lineSize = line.length + 1;  // +1 for newline
    
    // Flush if adding this line would exceed max
    if (currentChars + lineSize > maxChars && current.length > 0) {
      flush();
      carryOverlap();
    }
    
    current.push({ line, lineNo });
    currentChars += lineSize;
  }
  
  flush();
  return chunks;
}
```

**Configuration**:
- Default chunk size: 512 tokens (~2048 chars)
- Default overlap: 128 tokens (~512 chars)
- Ensures context continuity across chunks

---

## Vector Search

### SQLite Schema

```sql
-- Main chunks table with vector embeddings
CREATE TABLE IF NOT EXISTS chunks_vec (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,     -- "memory" or "session"
  source_path TEXT NOT NULL,     -- Relative file path
  source_hash TEXT NOT NULL,     -- SHA-256 of file content
  chunk_hash TEXT NOT NULL,      -- SHA-256 of chunk text
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  text TEXT NOT NULL,
  embedding BLOB,                -- Float32Array as binary
  indexed_at INTEGER NOT NULL    -- Unix timestamp
);

CREATE INDEX idx_chunks_source ON chunks_vec(source_type, source_path);
CREATE INDEX idx_chunks_hash ON chunks_vec(chunk_hash);

-- Full-text search table (FTS5)
CREATE VIRTUAL TABLE chunks_fts USING fts5(
  chunk_id UNINDEXED,
  source_path UNINDEXED,
  text,
  content='chunks_vec',
  content_rowid='id'
);

-- Embedding cache (to avoid re-embedding)
CREATE TABLE IF NOT EXISTS embedding_cache (
  text_hash TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  cached_at INTEGER NOT NULL
);
```

### Vector Similarity Search

```typescript
export async function searchVector(params: {
  db: DatabaseSync;
  queryEmbedding: number[];
  limit: number;
  threshold?: number;
}): Promise<MemorySearchResult[]> {
  const { db, queryEmbedding, limit, threshold = 0.0 } = params;
  
  // Convert query to blob
  const queryBlob = vectorToBlob(queryEmbedding);
  
  // Use sqlite-vec for cosine similarity
  const results = db.prepare(`
    SELECT 
      id,
      source_path,
      start_line,
      end_line,
      text,
      vec_distance_cosine(embedding, ?) AS distance
    FROM chunks_vec
    WHERE embedding IS NOT NULL
      AND vec_distance_cosine(embedding, ?) < ?
    ORDER BY distance ASC
    LIMIT ?
  `).all(queryBlob, queryBlob, 1.0 - threshold, limit);
  
  return results.map((row) => ({
    source: row.source_path,
    startLine: row.start_line,
    endLine: row.end_line,
    text: row.text,
    score: 1.0 - row.distance,  // Convert distance to similarity
    snippet: truncateSnippet(row.text, SNIPPET_MAX_CHARS),
  }));
}

function vectorToBlob(embedding: number[]): Buffer {
  return Buffer.from(new Float32Array(embedding).buffer);
}
```

---

## Hybrid Search (FTS + Vector)

### Overview

Hybrid search combines full-text search (keyword matching) with vector search (semantic similarity) for better results.

### Search Flow

```typescript
export async function search(params: {
  query: string;
  limit?: number;
  threshold?: number;
}): Promise<MemorySearchResult[]> {
  const limit = params.limit ?? 10;
  const threshold = params.threshold ?? 0.5;
  
  // 1. Embed query
  const queryEmbedding = await this.provider.embedQuery(params.query);
  
  // 2. Vector search
  const vectorResults = await searchVector({
    db: this.db,
    queryEmbedding,
    limit: limit * 2,  // Get more candidates
    threshold,
  });
  
  // 3. Keyword search (if hybrid enabled)
  let keywordResults: MemorySearchResult[] = [];
  if (this.fts.enabled && this.fts.available) {
    const ftsQuery = buildFtsQuery(params.query);
    keywordResults = await searchKeyword({
      db: this.db,
      query: ftsQuery,
      limit: limit * 2,
    });
  }
  
  // 4. Merge results using reciprocal rank fusion
  const merged = mergeHybridResults({
    vectorResults,
    keywordResults,
    vectorWeight: 0.7,  // Favor semantic similarity
    keywordWeight: 0.3,
    limit,
  });
  
  return merged;
}
```

### Full-Text Search Query Building

```typescript
export function buildFtsQuery(query: string): string {
  // Tokenize and clean
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .map((token) => token.replace(/[^\w-]/g, ""))
    .filter((token) => token.length >= 2);
  
  if (tokens.length === 0) {
    return "";
  }
  
  // Build FTS5 query
  // Use prefix matching (*) for better recall
  return tokens.map((token) => `${token}*`).join(" OR ");
}
```

### Result Merging (Reciprocal Rank Fusion)

```typescript
export function mergeHybridResults(params: {
  vectorResults: MemorySearchResult[];
  keywordResults: MemorySearchResult[];
  vectorWeight: number;
  keywordWeight: number;
  limit: number;
}): MemorySearchResult[] {
  const { vectorResults, keywordResults, vectorWeight, keywordWeight, limit } = params;
  
  // Build score map
  const scoreMap = new Map<string, { result: MemorySearchResult; score: number }>();
  
  // Add vector scores
  vectorResults.forEach((result, rank) => {
    const key = `${result.source}:${result.startLine}:${result.endLine}`;
    const rrfScore = vectorWeight / (rank + 60);  // k=60 in RRF formula
    scoreMap.set(key, { result, score: rrfScore });
  });
  
  // Add keyword scores
  keywordResults.forEach((result, rank) => {
    const key = `${result.source}:${result.startLine}:${result.endLine}`;
    const rrfScore = keywordWeight / (rank + 60);
    const existing = scoreMap.get(key);
    if (existing) {
      existing.score += rrfScore;  // Combine scores
    } else {
      scoreMap.set(key, { result, score: rrfScore });
    }
  });
  
  // Sort by combined score
  const merged = Array.from(scoreMap.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((item) => ({
      ...item.result,
      score: item.score,
    }));
  
  return merged;
}
```

---

## Caching Strategy

### Embedding Cache

```typescript
// Check cache before embedding
async function getCachedEmbedding(
  textHash: string,
  provider: string,
  model: string,
): Promise<number[] | null> {
  const row = this.db.prepare(`
    SELECT embedding
    FROM embedding_cache
    WHERE text_hash = ?
      AND provider = ?
      AND model = ?
  `).get(textHash, provider, model);
  
  if (!row) {
    return null;
  }
  
  return parseEmbedding(row.embedding);
}

// Store embedding in cache
async function cacheEmbedding(
  textHash: string,
  embedding: number[],
  provider: string,
  model: string,
): Promise<void> {
  const blob = vectorToBlob(embedding);
  this.db.prepare(`
    INSERT OR REPLACE INTO embedding_cache (text_hash, embedding, provider, model, cached_at)
    VALUES (?, ?, ?, ?, ?)
  `).run(textHash, blob, provider, model, Date.now());
}

function parseEmbedding(blob: Buffer): number[] {
  const float32Array = new Float32Array(
    blob.buffer,
    blob.byteOffset,
    blob.byteLength / 4
  );
  return Array.from(float32Array);
}
```

### Cache Eviction

```typescript
// Limit cache size
async function evictOldCacheEntries(maxEntries: number): Promise<void> {
  const count = this.db.prepare("SELECT COUNT(*) as count FROM embedding_cache").get();
  
  if (count.count <= maxEntries) {
    return;
  }
  
  const toDelete = count.count - maxEntries;
  
  // Delete oldest entries
  this.db.prepare(`
    DELETE FROM embedding_cache
    WHERE text_hash IN (
      SELECT text_hash
      FROM embedding_cache
      ORDER BY cached_at ASC
      LIMIT ?
    )
  `).run(toDelete);
}
```

**Default**: Cache up to 10,000 embeddings

---

## Key Takeaways

### Architecture Insights

1. **File-Based**: Markdown files for easy editing
2. **SQLite**: Lightweight, embedded database
3. **Hybrid Search**: Best of keyword + semantic
4. **Auto-Sync**: File watcher for real-time updates
5. **Multi-Provider**: OpenAI, Gemini, Voyage, local

### Critical Patterns

1. **Chunking**:
   - 512 token chunks with 128 token overlap
   - Line-based splitting for markdown
   - Hash-based change detection

2. **Embedding**:
   - Caching to reduce API costs
   - Batch processing for efficiency
   - Normalization for consistency

3. **Search**:
   - Reciprocal rank fusion for hybrid results
   - Configurable vector/keyword weights
   - Snippet extraction for context

4. **Performance**:
   - WAL mode for SQLite concurrency
   - Debounced file watching (1 second)
   - Lazy loading of embedding models

### Configuration Example

```yaml
memory:
  enabled: true
  sources:
    - memory        # MEMORY.md and memory/
    - sessions      # Session transcripts
  
  provider: auto    # auto, openai, gemini, voyage, local
  model: text-embedding-3-small
  fallback: gemini
  
  chunking:
    tokens: 512
    overlap: 128
  
  query:
    hybrid:
      enabled: true
      vectorWeight: 0.7
      keywordWeight: 0.3
  
  cache:
    enabled: true
    maxEntries: 10000
```

---

## Emonk Adaptations

### What to Keep

1. **File-Based Storage**: Easy to edit, version control
2. **SQLite Database**: Simple, no external dependencies
3. **Embedding Caching**: Reduce API costs
4. **File Watching**: Auto-sync on changes

### What to Simplify

1. **No Hybrid Search**: Start with vector-only
2. **Single Provider**: OpenAI or Gemini only
3. **Simpler Chunking**: Fixed 512-token chunks
4. **No Session Search**: Focus on brand voice memory

### Emonk-Specific Implementation

#### 1. Simple Memory Manager (Python)

```python
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict
import numpy as np
from openai import OpenAI

class MemoryManager:
    def __init__(self, workspace_dir: str, openai_api_key: str):
        self.workspace_dir = Path(workspace_dir)
        self.db_path = self.workspace_dir / ".emonk" / "memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path))
        self.client = OpenAI(api_key=openai_api_key)
        self.init_schema()
    
    def init_schema(self):
        """Create database schema"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                chunk_hash TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                text TEXT NOT NULL,
                embedding BLOB,
                indexed_at INTEGER NOT NULL
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                cached_at INTEGER NOT NULL
            )
        """)
        self.db.commit()
    
    def list_memory_files(self) -> List[Path]:
        """List all memory markdown files"""
        files = []
        
        # Check root MEMORY.md
        memory_file = self.workspace_dir / "MEMORY.md"
        if memory_file.exists():
            files.append(memory_file)
        
        # Check memory/ directory
        memory_dir = self.workspace_dir / "memory"
        if memory_dir.exists():
            files.extend(memory_dir.rglob("*.md"))
        
        return files
    
    def hash_text(self, text: str) -> str:
        """SHA-256 hash of text"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def chunk_markdown(self, content: str, chunk_size: int = 2048) -> List[Dict]:
        """Split content into chunks"""
        lines = content.split("\n")
        chunks = []
        current = []
        current_chars = 0
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1
            if current_chars + line_size > chunk_size and current:
                # Flush chunk
                text = "\n".join(current)
                chunks.append({
                    "startLine": i - len(current) + 1,
                    "endLine": i,
                    "text": text,
                    "hash": self.hash_text(text),
                })
                current = []
                current_chars = 0
            
            current.append(line)
            current_chars += line_size
        
        # Flush remaining
        if current:
            text = "\n".join(current)
            chunks.append({
                "startLine": len(lines) - len(current) + 1,
                "endLine": len(lines),
                "text": text,
                "hash": self.hash_text(text),
            })
        
        return chunks
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding with caching"""
        text_hash = self.hash_text(text)
        
        # Check cache
        row = self.db.execute(
            "SELECT embedding FROM embedding_cache WHERE text_hash = ?",
            (text_hash,)
        ).fetchone()
        
        if row:
            return np.frombuffer(row[0], dtype=np.float32)
        
        # Generate embedding
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        
        # Cache it
        self.db.execute(
            "INSERT OR REPLACE INTO embedding_cache (text_hash, embedding, cached_at) VALUES (?, ?, ?)",
            (text_hash, embedding.tobytes(), int(time.time()))
        )
        self.db.commit()
        
        return embedding
    
    def sync(self):
        """Sync all memory files to database"""
        files = self.list_memory_files()
        
        for file_path in files:
            # Read file
            content = file_path.read_text()
            file_hash = self.hash_text(content)
            rel_path = str(file_path.relative_to(self.workspace_dir))
            
            # Check if already indexed
            row = self.db.execute(
                "SELECT source_hash FROM chunks WHERE source_path = ? LIMIT 1",
                (rel_path,)
            ).fetchone()
            
            if row and row[0] == file_hash:
                continue  # Already indexed
            
            # Delete old chunks
            self.db.execute("DELETE FROM chunks WHERE source_path = ?", (rel_path,))
            
            # Chunk and embed
            chunks = self.chunk_markdown(content)
            for chunk in chunks:
                embedding = self.get_embedding(chunk["text"])
                self.db.execute("""
                    INSERT INTO chunks (source_path, source_hash, chunk_hash, start_line, end_line, text, embedding, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel_path,
                    file_hash,
                    chunk["hash"],
                    chunk["startLine"],
                    chunk["endLine"],
                    chunk["text"],
                    embedding.tobytes(),
                    int(time.time())
                ))
            
            self.db.commit()
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for relevant chunks"""
        # Embed query
        query_embedding = self.get_embedding(query)
        
        # Get all chunks
        rows = self.db.execute(
            "SELECT source_path, start_line, end_line, text, embedding FROM chunks"
        ).fetchall()
        
        # Calculate cosine similarity
        results = []
        for row in rows:
            chunk_embedding = np.frombuffer(row[4], dtype=np.float32)
            similarity = np.dot(query_embedding, chunk_embedding)
            results.append({
                "source": row[0],
                "startLine": row[1],
                "endLine": row[2],
                "text": row[3],
                "score": float(similarity),
            })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
```

#### 2. File Watcher

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MemoryWatcher(FileSystemEventHandler):
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.dirty = False
    
    def on_modified(self, event):
        if event.src_path.endswith(".md"):
            self.dirty = True
            # Debounce sync
            if hasattr(self, "_timer"):
                self._timer.cancel()
            self._timer = threading.Timer(1.0, self.sync)
            self._timer.start()
    
    def sync(self):
        if self.dirty:
            self.memory_manager.sync()
            self.dirty = False

# Start watcher
observer = Observer()
handler = MemoryWatcher(memory_manager)
observer.schedule(handler, workspace_dir, recursive=True)
observer.start()
```

#### 3. Configuration

```yaml
# config.yaml
memory:
  enabled: true
  workspace: ./workspace
  chunkSize: 2048
  embedding:
    provider: openai
    model: text-embedding-3-small
  cache:
    maxEntries: 1000
```

### Key Implementation Priorities

1. **Phase 1**: Basic file-based storage + sync
2. **Phase 2**: Embedding and caching
3. **Phase 3**: Vector search
4. **Phase 4**: File watching
5. **Phase 5**: GCP Storage backup (optional)

---

## References

- OpenClaw Memory Manager: `src/memory/manager.ts`
- OpenClaw File Storage: `src/memory/internal.ts`
- OpenClaw Embeddings: `src/memory/embeddings.ts`
- OpenClaw Hybrid Search: `src/memory/hybrid.ts`

**Next Document**: [04_cron_scheduler.md](04_cron_scheduler.md)
