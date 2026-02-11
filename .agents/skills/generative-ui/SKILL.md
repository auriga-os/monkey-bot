---
name: generative-ui
description: Build self-contained generative UI components for LangGraph agents with Tailwind CSS, dark mode, and Shadow DOM support. Use when creating UI components in agents/*/ui/, adding new generative UI cards, or working with LoadExternalComponent in auriga-agents.
---

# Generative UI Components for LangGraph Agents

## Architecture Overview

Generative UI components live in `agents/{agent_name}/ui/` in the `auriga-agents` repo. They are:
- **Bundled by LangGraph CLI** (esbuild) at startup
- **Served from the LangGraph API server** as external assets
- **Loaded at runtime** by `LoadExternalComponent` from `@langchain/langgraph-sdk/react-ui`
- **Rendered inside a Shadow DOM** — CSS from the host page does NOT apply

This means components must be **fully self-contained** with their own styles.

## Directory Structure

Every agent with UI follows this layout:

```
agents/{agent_name}/ui/
├── index.tsx          # Entry point — exports ComponentMap + imports styles.css
├── styles.css         # Tailwind 4 entry — REQUIRED for styling
├── hooks.ts           # Shared hooks (useIsDarkMode)
├── types.ts           # TypeScript interfaces for component props
├── lib/
│   └── utils.ts       # cn() utility (clsx + tailwind-merge)
├── components/
│   ├── MyCard.tsx      # Individual UI components
│   └── MyListCard.tsx
└── node_modules/      # Local npm deps (tailwindcss, lucide-react, etc.)
```

## Setup Checklist

### 1. Register in `langgraph.json`

```json
{
  "ui": {
    "my_agent": "./agents/my_agent/ui/index.tsx"
  }
}
```

### 2. Install local npm dependencies

```bash
cd agents/{agent_name}/ui
npm install tailwindcss@latest lucide-react framer-motion clsx tailwind-merge
npm install --save-dev @types/node
```

These must be **local** to the `ui/` directory so LangGraph's bundler can resolve them.

### 3. Create `styles.css` (critical)

```css
@import "tailwindcss";
@source "./components";
@source "./lib";

@custom-variant dark (&:where(.dark, .dark *));
```

**Why each line matters:**
- `@import "tailwindcss"` — Tailwind 4 entry point, generates utility CSS
- `@source` — tells Tailwind which directories to scan for class names
- `@custom-variant dark` — switches from media-query dark mode to class-based, required because Shadow DOM isolates from the host `<html class="dark">`

### 4. Create `hooks.ts`

```typescript
import { useEffect, useState } from "react";

export function useIsDarkMode() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const checkDark = () => {
      const isDarkClass =
        document.documentElement.classList.contains("dark") ||
        document.body.classList.contains("dark");
      const isDarkData =
        document.documentElement.getAttribute("data-theme") === "dark" ||
        document.body.getAttribute("data-theme") === "dark";
      setIsDark(isDarkClass || isDarkData);
    };

    checkDark();

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.attributeName === "class" ||
          mutation.attributeName === "data-theme"
        ) {
          checkDark();
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });
    observer.observe(document.body, { attributes: true });

    return () => observer.disconnect();
  }, []);

  return isDark;
}
```

**Why:** Inside Shadow DOM, Tailwind's `dark:` variants can't see the host's `<html class="dark">`. This hook reads the host document and returns a boolean. Components wrap their JSX in `<div className={isDark ? "dark" : ""}>` to propagate the theme.

### 5. Create `lib/utils.ts`

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 6. Create `index.tsx`

```typescript
import "./styles.css";

import { MyCard } from "./components/MyCard";
import { MyListCard } from "./components/MyListCard";

const ComponentMap = {
  MyCard,
  MyListCard,
} as const;

export default ComponentMap;
export { MyCard, MyListCard };
```

**Key:** `import "./styles.css"` must be present — the bundler injects this CSS into the Shadow DOM.

## Component Pattern

Every component follows this structure:

```tsx
import React from "react";
import { motion } from "framer-motion";
import { cn } from "../lib/utils";
import { useIsDarkMode } from "../hooks";
import type { MyCardProps } from "../types";

export function MyCard({ title, description }: MyCardProps) {
  const isDark = useIsDarkMode();

  return (
    <div className={isDark ? "dark" : ""}>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className={cn(
          "bg-white dark:bg-zinc-900",
          "border border-gray-200 dark:border-zinc-800",
          "rounded-xl p-4",
          "transition-all duration-200"
        )}
      >
        <h3 className="text-lg font-bold text-gray-900 dark:text-zinc-100">
          {title}
        </h3>
        <p className="text-sm text-gray-600 dark:text-zinc-400">
          {description}
        </p>
      </motion.div>
    </div>
  );
}
```

**Rules:**
1. Outermost `<div className={isDark ? "dark" : ""}>` — propagates theme into Shadow DOM
2. Use `cn()` for conditional classes — never template literals for Tailwind classes
3. Always provide both light and `dark:` variants
4. Use `framer-motion` for animations
5. Use `lucide-react` for icons

## Communicating with the Frontend Layout

Since components run inside Shadow DOM, they can't access React context from the host app. Use **CustomEvents** on `window` to communicate:

### From component → layout (dispatching)

```tsx
// In the agent's UI component
window.dispatchEvent(
  new CustomEvent("my-agent-action", {
    detail: { action: "save", itemId: "123", data: { ... } }
  })
);
```

### From layout → listening (in auriga-web)

```tsx
// In the frontend layout component
useEffect(() => {
  const handler = (event: CustomEvent<{ action: string; itemId: string }>) => {
    const { action, itemId } = event.detail;
    // Handle the action, update state, call stream.submit(), etc.
  };

  window.addEventListener("my-agent-action", handler as EventListener);
  return () => window.removeEventListener("my-agent-action", handler as EventListener);
}, []);
```

**Naming convention:** `{agent-name}-{action}` (e.g., `financial-advisor-save`, `financial-advisor-view-details`)

## Color Palette Reference

| Element | Light | Dark |
|---------|-------|------|
| Card background | `bg-white` | `dark:bg-zinc-900` |
| Container background | `bg-gray-50` | `dark:bg-[#121214]` |
| Primary text | `text-gray-900` | `dark:text-zinc-100` |
| Secondary text | `text-gray-600` | `dark:text-zinc-400` |
| Muted text | `text-gray-500` | `dark:text-zinc-500` |
| Border | `border-gray-200` | `dark:border-zinc-800` |
| Badge background | `bg-gray-100` | `dark:bg-zinc-800` |
| Active/accent | `bg-blue-600` | `dark:bg-blue-500/20` |
| Success | `text-green-700` | `dark:text-green-400` |

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| "Loading component" forever | `lucide-react` or other dep not in local `node_modules` | `npm install` in the `ui/` directory |
| No styling at all | Missing `styles.css` or missing `import "./styles.css"` in index | Add both |
| Always dark mode | Tailwind 4 defaults to `prefers-color-scheme` media query | Add `@custom-variant dark (&:where(.dark, .dark *))` to styles.css |
| Build error "Could not resolve X" | Dependency not installed locally | `npm install X` in `ui/` dir |
| Stale components after changes | Browser caching old bundle | Hard refresh (Cmd+Shift+R) |
| Custom events not received | Dispatching inside Shadow DOM scope | Always use `window.dispatchEvent()` |

## Backend: Emitting UI Components

In the agent's Python tool, emit UI by returning a `Command` with `ui` messages:

```python
ui_message = {
    "name": "MyCard",         # Must match key in ComponentMap
    "props": {                 # Passed as React props
        "title": "Hello",
        "description": "World",
    },
    "metadata": {
        "message_id": last_ai_message_id,
    },
}

return Command(
    update={
        "messages": tool_messages,
        "ui": [ui_message],
    }
)
```

The `name` field must exactly match a key in the `ComponentMap` exported from `index.tsx`.
