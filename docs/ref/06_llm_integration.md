# LLM Integration & Model Selection - OpenClaw Code Extraction

**Source**: OpenClaw LLM integration implementation  
**Purpose**: Reference for building Emonk's LLM/Vertex AI integration  
**Extraction Date**: 2026-02-11

---

## Overview

OpenClaw's LLM integration provides:
- **Multi-provider support**: Anthropic, Google, OpenAI, local models
- **Intelligent routing**: Cost-optimized model selection
- **Model aliases**: User-friendly names
- **Function calling**: Native tool integration
- **Streaming**: Real-time response streaming

---

## Model Selection

### Model Reference Format

```typescript
export type ModelRef = {
  provider: string;  // "anthropic", "google", "openai"
  model: string;     // "claude-opus-4-6", "gemini-2.0-flash"
};

// Parse model string "provider/model"
export function parseModelRef(raw: string, defaultProvider: string): ModelRef | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  
  const slash = trimmed.indexOf("/");
  if (slash === -1) {
    // No provider specified, use default
    const provider = normalizeProviderId(defaultProvider);
    const model = normalizeProviderModelId(provider, trimmed);
    return { provider, model };
  }
  
  const providerRaw = trimmed.slice(0, slash).trim();
  const provider = normalizeProviderId(providerRaw);
  const model = trimmed.slice(slash + 1).trim();
  
  if (!provider || !model) {
    return null;
  }
  
  return { provider, model: normalizeProviderModelId(provider, model) };
}
```

### Model Aliases

```typescript
const ANTHROPIC_MODEL_ALIASES: Record<string, string> = {
  "opus-4.6": "claude-opus-4-6",
  "opus-4.5": "claude-opus-4-5",
  "sonnet-4.5": "claude-sonnet-4-5",
};

// Configuration
agents:
  defaults:
    model: opus-4.6  # Resolves to anthropic/claude-opus-4-6
    models:
      "anthropic/claude-opus-4-6":
        alias: opus
      "google/gemini-2.0-flash":
        alias: flash
```

### Cost-Optimized Routing

```typescript
export function resolveDefaultModelForAgent(params: {
  cfg: OpenClawConfig;
  agentId?: string;
}): ModelRef {
  // 1. Check agent-specific config
  const agentModel = resolveAgentModelPrimary(params.cfg, params.agentId);
  if (agentModel) {
    return parseModelRef(agentModel, DEFAULT_PROVIDER) ?? DEFAULT_MODEL_REF;
  }
  
  // 2. Check global default
  const globalModel = params.cfg.agents?.defaults?.model;
  if (typeof globalModel === "string") {
    return parseModelRef(globalModel, DEFAULT_PROVIDER) ?? DEFAULT_MODEL_REF;
  }
  
  // 3. Fall back to hardcoded default
  return DEFAULT_MODEL_REF;
}

// Example routing logic
function selectModel(task: string): ModelRef {
  if (task.includes("simple") || task.includes("quick")) {
    // Use fast, cheap model
    return { provider: "google", model: "gemini-2.0-flash" };
  } else if (task.includes("complex") || task.includes("reasoning")) {
    // Use powerful model
    return { provider: "anthropic", model: "claude-opus-4-6" };
  } else {
    // Default balanced model
    return { provider: "google", model: "gemini-2.0-pro" };
  }
}
```

---

## Vertex AI Integration

### Gemini Embedding Provider

```typescript
const DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";
const DEFAULT_GEMINI_EMBEDDING_MODEL = "text-embedding-004";

export async function createGeminiEmbeddingProvider(
  options: EmbeddingProviderOptions,
): Promise<{ provider: EmbeddingProvider; client: GeminiEmbeddingClient }> {
  // Resolve API key
  const apiKey = requireApiKey(
    await resolveApiKeyForProvider({
      provider: "google",
      cfg: options.config,
      agentDir: options.agentDir,
    }),
    "google"
  );
  
  // Build client
  const client = {
    baseUrl: options.remote?.baseUrl || DEFAULT_GEMINI_BASE_URL,
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": apiKey,
    },
    model: normalizeGeminiModel(options.model || DEFAULT_GEMINI_EMBEDDING_MODEL),
    modelPath: buildGeminiModelPath(options.model || DEFAULT_GEMINI_EMBEDDING_MODEL),
  };
  
  const embedUrl = `${client.baseUrl}/${client.modelPath}:embedContent`;
  const batchUrl = `${client.baseUrl}/${client.modelPath}:batchEmbedContents`;
  
  // Create provider
  const provider: EmbeddingProvider = {
    id: "gemini",
    model: client.model,
    maxInputTokens: 2048,
    
    embedQuery: async (text: string) => {
      const res = await fetch(embedUrl, {
        method: "POST",
        headers: client.headers,
        body: JSON.stringify({
          content: { parts: [{ text }] },
          taskType: "RETRIEVAL_QUERY",
        }),
      });
      
      if (!res.ok) {
        throw new Error(`gemini embeddings failed: ${res.status}`);
      }
      
      const payload = await res.json();
      return payload.embedding?.values ?? [];
    },
    
    embedBatch: async (texts: string[]) => {
      const requests = texts.map((text) => ({
        model: client.modelPath,
        content: { parts: [{ text }] },
        taskType: "RETRIEVAL_DOCUMENT",
      }));
      
      const res = await fetch(batchUrl, {
        method: "POST",
        headers: client.headers,
        body: JSON.stringify({ requests }),
      });
      
      if (!res.ok) {
        throw new Error(`gemini batch embeddings failed: ${res.status}`);
      }
      
      const payload = await res.json();
      const embeddings = payload.embeddings ?? [];
      return texts.map((_, index) => embeddings[index]?.values ?? []);
    },
  };
  
  return { provider, client };
}
```

### Tool Schema Sanitization (Google)

Google/Gemini has restrictions on JSON schema:

```typescript
const GOOGLE_SCHEMA_UNSUPPORTED_KEYWORDS = new Set([
  "patternProperties",
  "additionalProperties",
  "$schema",
  "$id",
  "$ref",
  "$defs",
  "definitions",
  "examples",
  "minLength",
  "maxLength",
  "minimum",
  "maximum",
  "multipleOf",
  "pattern",
  "format",
  "minItems",
  "maxItems",
  "uniqueItems",
  "minProperties",
  "maxProperties",
]);

export function cleanToolSchemaForGemini(schema: Record<string, unknown>): Record<string, unknown> {
  if (!schema || typeof schema !== "object") {
    return schema;
  }
  
  const cleaned: Record<string, unknown> = {};
  
  for (const [key, value] of Object.entries(schema)) {
    // Skip unsupported keywords
    if (GOOGLE_SCHEMA_UNSUPPORTED_KEYWORDS.has(key)) {
      continue;
    }
    
    // Recursively clean nested objects
    if (value && typeof value === "object" && !Array.isArray(value)) {
      cleaned[key] = cleanToolSchemaForGemini(value as Record<string, unknown>);
    } else {
      cleaned[key] = value;
    }
  }
  
  return cleaned;
}
```

---

## Emonk Adaptation (Python)

### Simple Vertex AI Client

```python
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel
import os

class VertexAIClient:
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        aiplatform.init(
            project=project_id,
            location=location,
            credentials=None  # Uses GOOGLE_APPLICATION_CREDENTIALS
        )
    
    def generate_text(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Generate text response"""
        model = GenerativeModel(model)
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        
        return response.text
    
    def generate_streaming(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash",
        callback=None
    ):
        """Generate with streaming"""
        model = GenerativeModel(model)
        
        response = model.generate_content(
            prompt,
            stream=True
        )
        
        for chunk in response:
            if chunk.text:
                if callback:
                    callback(chunk.text)
                yield chunk.text
    
    def get_embedding(self, text: str, model: str = "text-embedding-004") -> list:
        """Get embedding for text"""
        from vertexai.language_models import TextEmbeddingModel
        
        model = TextEmbeddingModel.from_pretrained(model)
        embeddings = model.get_embeddings([text])
        return embeddings[0].values

# Usage
client = VertexAIClient(
    project_id="your-project-id",
    location="us-central1"
)

# Simple generation
response = client.generate_text("Generate a tweet about AI agents")

# Streaming
for chunk in client.generate_streaming("Write a blog post"):
    print(chunk, end="", flush=True)

# Embeddings
embedding = client.get_embedding("Brand voice guidelines")
```

### Model Router

```python
class ModelRouter:
    def __init__(self, config: dict):
        self.config = config
        self.default_model = config.get("defaultModel", "gemini-2.0-flash")
    
    def select_model(self, task: str, context: dict = None) -> str:
        """Select optimal model for task"""
        # Simple heuristics
        if len(task) < 100:
            # Short task, use fast model
            return "gemini-2.0-flash"
        elif "complex" in task.lower() or "analyze" in task.lower():
            # Complex task, use powerful model
            return "gemini-2.0-pro"
        else:
            # Default model
            return self.default_model
```

---

## Key Takeaways

1. **Multi-provider**: Support multiple LLM providers
2. **Cost optimization**: Route based on task complexity
3. **Model aliases**: User-friendly names
4. **Schema cleaning**: Handle provider-specific requirements
5. **Streaming support**: Real-time responses

---

**Next Document**: [07_terminal_executor.md](07_terminal_executor.md)
