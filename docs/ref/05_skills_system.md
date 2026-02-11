# Skills System & Execution - OpenClaw Code Extraction

**Source**: OpenClaw Skills implementation  
**Purpose**: Reference for building Emonk's skill system  
**Extraction Date**: 2026-02-11

---

## Overview

OpenClaw's skill system provides modular, reusable capabilities through:
- **SKILL.md files**: Markdown documentation with YAML frontmatter
- **CLI tool wrapping**: Skills use existing command-line tools (gh, discord, etc.)
- **Skill discovery**: Auto-detect skills from filesystem
- **MCP integration**: Skills can be delivered via Model Context Protocol

---

## Skill Structure

### SKILL.md Format

```markdown
---
name: github
description: "Interact with GitHub using the `gh` CLI"
metadata:
  openclaw:
    emoji: "🐙"
    requires:
      bins: ["gh"]
    install:
      - id: brew
        kind: brew
        formula: gh
        bins: ["gh"]
        label: Install GitHub CLI (brew)
      - id: apt
        kind: apt
        package: gh
        bins: ["gh"]
        label: Install GitHub CLI (apt)
---

# GitHub Skill

Use the `gh` CLI to interact with GitHub.

## Pull Requests

Check CI status on a PR:

```bash
gh pr checks 55 --repo owner/repo
```

List recent workflow runs:

```bash
gh run list --repo owner/repo --limit 10
```

## JSON Output

Most commands support `--json` for structured output:

```bash
gh issue list --repo owner/repo --json number,title
```
```

### Key Components

1. **YAML Frontmatter**:
   - `name`: Skill identifier
   - `description`: What the skill does
   - `metadata.openclaw.requires`: Dependencies (bins, config)
   - `metadata.openclaw.install`: Installation instructions

2. **Markdown Body**:
   - Usage examples
   - Command patterns
   - Best practices
   - Tips and tricks

---

## Skill Types

### 1. CLI Wrapper Skills

Wrap existing command-line tools:

**GitHub** (`gh` CLI):
```yaml
---
name: github
description: "Interact with GitHub using the `gh` CLI"
metadata:
  openclaw:
    requires:
      bins: ["gh"]
---
```

**Discord** (Discord tool):
```yaml
---
name: discord
description: "Control Discord via the discord tool"
metadata:
  openclaw:
    requires:
      config: ["channels.discord"]
---
```

### 2. Python Script Skills

Custom Python scripts:

```python
#!/usr/bin/env python3
"""
Skill: Search web with Vertex AI
"""
import sys
import json
import os

def search_web(query: str, limit: int = 5) -> dict:
    # Use Vertex AI grounded search
    results = vertex_search(query, limit)
    return {"results": results}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    
    result = search_web(args.query, args.limit)
    print(json.dumps(result))
```

### 3. Shell Script Skills

Bash scripts for simple tasks:

```bash
#!/bin/bash
# Skill: Post to X/Twitter

set -euo pipefail

CONTENT="$1"
TRACE_ID="${2:-unknown}"

# Validate
if [ -z "$CONTENT" ]; then
  echo '{"error": "No content"}' >&2
  exit 1
fi

# Post via API
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $X_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$CONTENT\"}"
```

---

## Skill Discovery

```typescript
export async function loadWorkspaceSkillEntries(
  workspaceDir: string
): Promise<SkillEntry[]> {
  const skillsDir = path.join(workspaceDir, "skills");
  
  // Check if skills directory exists
  try {
    const stat = await fs.stat(skillsDir);
    if (!stat.isDirectory()) {
      return [];
    }
  } catch {
    return [];
  }
  
  // Find all SKILL.md files
  const entries: SkillEntry[] = [];
  const subdirs = await fs.readdir(skillsDir, { withFileTypes: true });
  
  for (const entry of subdirs) {
    if (!entry.isDirectory()) {
      continue;
    }
    
    const skillMdPath = path.join(skillsDir, entry.name, "SKILL.md");
    try {
      const content = await fs.readFile(skillMdPath, "utf-8");
      const parsed = parseSkillMd(content);
      
      entries.push({
        name: parsed.name,
        description: parsed.description,
        path: skillMdPath,
        metadata: parsed.metadata,
        content: parsed.body,
      });
    } catch {
      // Skip invalid skills
      continue;
    }
  }
  
  return entries;
}
```

---

## Skill Examples

### Example 1: GitHub Skill

```markdown
---
name: github
description: "Interact with GitHub using the `gh` CLI"
metadata:
  openclaw:
    emoji: "🐙"
    requires:
      bins: ["gh"]
---

# GitHub Skill

## Pull Requests

Check CI status:
```bash
gh pr checks 55 --repo owner/repo
```

List PRs:
```bash
gh pr list --repo owner/repo --state open
```

## Issues

Create issue:
```bash
gh issue create --title "Bug report" --body "Description" --repo owner/repo
```
```

### Example 2: Web Search Skill (Python)

```markdown
---
name: web-search
description: "Search the web with Vertex AI grounded search"
metadata:
  openclaw:
    emoji: "🔍"
    requires:
      env: ["GOOGLE_APPLICATION_CREDENTIALS"]
---

# Web Search Skill

Search for current information:

```bash
python skills/web-search.py "AI news" --limit 5
```

Output format:
```json
{
  "results": [
    {
      "title": "...",
      "url": "...",
      "snippet": "..."
    }
  ]
}
```
```

### Example 3: Content Generator (Python)

```markdown
---
name: content-generator
description: "Generate social media content with brand voice"
metadata:
  openclaw:
    emoji: "✍️"
---

# Content Generator Skill

Generate platform-specific content:

```bash
python skills/generate-content.py "topic" --platform twitter
```

Platforms: twitter, linkedin, instagram

The skill automatically loads BRAND_VOICE.md for consistency.
```

---

## Emonk Implementation

### Skill Directory Structure

```
skills/
├── web-search/
│   ├── SKILL.md           # Documentation
│   └── search.py          # Python script
├── content-generator/
│   ├── SKILL.md
│   └── generate.py
├── post-to-x/
│   ├── SKILL.md
│   └── post.sh            # Shell script
└── post-to-linkedin/
    ├── SKILL.md
    └── post.py
```

### Skill Loader (Python)

```python
import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Skill:
    name: str
    description: str
    path: Path
    metadata: dict
    content: str

class SkillLoader:
    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
    
    def load_skills(self) -> List[Skill]:
        """Load all skills from directory"""
        if not self.skills_dir.exists():
            return []
        
        skills = []
        for subdir in self.skills_dir.iterdir():
            if not subdir.is_dir():
                continue
            
            skill_md = subdir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            try:
                skill = self.parse_skill(skill_md)
                skills.append(skill)
                self.skills[skill.name] = skill
            except Exception as e:
                print(f"Failed to load skill {subdir.name}: {e}")
        
        return skills
    
    def parse_skill(self, path: Path) -> Skill:
        """Parse SKILL.md file"""
        content = path.read_text()
        
        # Split frontmatter and body
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_yaml = parts[1]
                body = parts[2].strip()
            else:
                frontmatter_yaml = ""
                body = content
        else:
            frontmatter_yaml = ""
            body = content
        
        # Parse frontmatter
        frontmatter = yaml.safe_load(frontmatter_yaml) if frontmatter_yaml else {}
        
        return Skill(
            name=frontmatter.get("name", path.parent.name),
            description=frontmatter.get("description", ""),
            path=path,
            metadata=frontmatter.get("metadata", {}),
            content=body
        )
    
    def get_skill(self, name: str) -> Skill | None:
        """Get skill by name"""
        return self.skills.get(name)
    
    def list_skill_names(self) -> List[str]:
        """List all skill names"""
        return list(self.skills.keys())
```

### Skill Executor

```python
import subprocess
import json

class SkillExecutor:
    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
    
    def execute(self, skill_name: str, args: List[str]) -> dict:
        """Execute a skill script"""
        skill_path = self.skills_dir / skill_name
        
        # Find executable (Python or shell script)
        python_script = skill_path / f"{skill_name}.py"
        shell_script = skill_path / f"{skill_name}.sh"
        
        if python_script.exists():
            cmd = ["python", str(python_script)] + args
        elif shell_script.exists():
            cmd = ["bash", str(shell_script)] + args
        else:
            raise FileNotFoundError(f"No executable for skill {skill_name}")
        
        # Execute with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=self.skills_dir
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr
            }
        
        # Parse JSON output
        try:
            return json.loads(result.stdout)
        except:
            return {
                "success": True,
                "output": result.stdout
            }

# Usage
loader = SkillLoader("./skills")
loader.load_skills()

executor = SkillExecutor("./skills")
result = executor.execute("web-search", ["AI news", "--limit", "5"])
```

---

## Key Takeaways

1. **SKILL.md format**: YAML frontmatter + Markdown body
2. **CLI-first**: Wrap existing tools, don't reinvent
3. **Discoverable**: Auto-load from skills/ directory
4. **Testable**: Can run skills manually via command line
5. **Observable**: Skills output JSON for parsing

---

**Next Document**: [06_llm_integration.md](06_llm_integration.md)
