---
name: write-blog-post
description: Create engaging blog posts about Auriga OS following the established style and format. Use when the user asks to write a blog post, create content for the blog, or add a new article to the blog page. Automatically generates accompanying superhero animal team images using nano_bannan.
---

# Writing Blog Posts for Auriga/MonkeyMode

This skill helps you write compelling, technical blog posts that match the style and format of existing Auriga blog content.

## Blog Post Style Guidelines

### Voice & Tone
- **Technical but accessible**: Explain complex concepts clearly without dumbing them down
- **Story-driven**: Use real-world examples and narratives to illustrate points
- **Honest and direct**: No marketing fluff, focus on genuine insights
- **Educational**: Teach readers something valuable they can apply

### Structure Best Practices
- **Hook immediately**: Start with a compelling problem, statistic, or question
- **Short paragraphs**: 2-4 sentences maximum for readability
- **Scannable content**: Use bullet points, numbered lists, and clear headings
- **Progressive depth**: Start accessible, then dive deeper for technical readers
- **Real examples**: Include concrete code, numbers, and specific scenarios
- **Key takeaways**: Always include actionable insights readers can use

### Content Patterns

**Introduction Pattern:**
1. Start with a relatable problem or challenge
2. Present the solution or insight you'll explore
3. Set expectations for what readers will learn

**Section Pattern:**
- Clear H2 headings that describe the benefit/topic
- Opening paragraph that states the main point
- Supporting details with examples
- Concrete code snippets or data where relevant
- Subsections (H3) for complex topics

**Conclusion Pattern:**
1. Summarize key takeaways as a bulleted or numbered list
2. Connect back to the opening problem
3. End with a forward-looking statement or call to engage

## File Format Requirements

All blog posts are MDX files stored in `/Users/kz127/code/auriga-web/content/blog/`

### Required Frontmatter

```yaml
---
title: "Compelling Title: Subtitle That Explains Value"
description: "SEO-friendly description (150-160 chars) that entices clicks"
date: "YYYY-MM-DD"
category: "AI & Education"
tags: ["Tag1", "Tag2", "Tag3", "Tag4"]
coverImage: "/images/blog/your-slug-cover.jpg"
published: true
---
```

**Frontmatter Guidelines:**
- **title**: Use colons to separate main title from subtitle; be specific and promise value
- **description**: Focus on the benefit or problem solved; max 160 chars for SEO
- **date**: Use today's date in YYYY-MM-DD format
- **category**: Almost always "AI & Education" unless specifically different
- **tags**: 3-5 relevant tags (capitalize first letter)
- **coverImage**: Path to cover image (must be generated)
- **published**: Set to `true` when ready to publish

### Content Structure

After frontmatter:

```markdown
# Introduction

[Compelling hook - problem/question/story]

[What this post covers and why it matters]

## Main Section 1

[Content with clear value proposition]

### Subsection (if needed)

[Detailed exploration]

> "Use blockquotes for key insights or quotes that deserve emphasis"

## Main Section 2

[Continue building the narrative]

**Real-World Example:**

[Concrete scenario showing the concept in action]

## Key Takeaways

[Bulleted or numbered list of actionable insights]

## Conclusion

[Tie everything together; reinforce value]

---

[Optional closing statement]
```

## Blog Post Creation Workflow

Follow these steps when creating a blog post:

### Step 1: Understand the Topic

Ask clarifying questions if needed:
- What's the main message or insight?
- Who's the target audience (developers, students, general)?
- Are there specific examples or data to include?
- What should readers be able to do after reading?

### Step 2: Research Existing Context

If writing about Auriga or MonkeyMode features:
- Review relevant code or documentation
- Check for existing related blog posts
- Understand technical details accurately

### Step 3: Craft the Frontmatter

- Create a compelling title that promises value
- Write an SEO description that makes readers want to click
- Use today's date
- Select 3-5 relevant tags
- Set coverImage path (will generate in next step)

### Step 4: Generate Cover Image

**CRITICAL**: Every blog post needs a superhero-themed cover image with diverse animals.

Use nano_bannan (the image generation tool) to create a cover image following this theme:

**Visual Theme Guidelines:**
- **Style**: Comic book superhero aesthetic with vibrant colors
- **Characters**: Diverse superhero animals - gorillas, lions, bears, eagles, wolves, foxes, etc. (not just monkeys/primates)
- **Setting**: Dynamic scenes with purple/orange/blue gradient skies, urban or futuristic backdrops
- **Comic elements**: "POW!", "BOOM!", "VOTE!", "BUILD!" or other relevant comic book action text
- **Composition**: Team pose on a building/structure, or action scene showing the concept
- **Mood**: Energetic, fun, powerful, inspiring, collaborative
- **Color palette**: Rich purples, warm oranges, bright blues, golden accents
- **Diversity**: Include various animal types to represent different strengths and perspectives

**Example prompts:**

For a post about community collaboration:
```
"Comic book style illustration of diverse superhero animals gathered around a large glowing voting board. 
The team includes a gorilla leader in a blue and purple suit with 'A' emblem, a lion in a cape, a bear 
in armor, an eagle with wings spread, a wolf, and a fox - all in matching superhero uniforms. Purple and 
orange gradient sky background with tech elements. Comic book 'VOTE!' and 'BUILD!' text floating in the 
scene. Vibrant, energetic, collaborative mood."
```

For a post about AI development workflow:
```
"Comic book style illustration of diverse superhero animals in a team pose on a rooftop. A gorilla leader 
in the center wears a blue and red superhero suit with an 'M' emblem, flanked by a lion with cape, bear 
with gadgets, eagle soaring above, and wolf and fox on the sides - all in matching uniforms. Purple and 
orange gradient sunset sky with clouds. Urban cityscape in background. Comic book 'POW!' and 'BOOM!' text 
floating in the scene. Vibrant, energetic, inspiring mood."
```

For a technical architecture post:
```
"Technical diagram style illustration with diverse superhero animal mascots. Central gorilla superhero 
in cape standing confidently, with lion, bear, eagle, wolf forming a circle around a glowing technical 
diagram. Dark background with golden circuit-like lines connecting different technical components 
represented as glowing panels. Professional but playful comic book aesthetic. Purple, gold, and blue 
color scheme."
```

**Generate the image:**

1. Create a descriptive prompt based on the blog post topic
2. Use nano_bannan to generate the image
3. Save it to `/Users/kz127/code/auriga-web/public/images/blog/[slug]-cover.jpg`
4. If additional inline images are needed, generate them as `[slug]-[description].jpg`

### Step 5: Write the Content

Write in sections, following the structure:

1. **Introduction** - Hook the reader immediately
2. **Problem/Context** - Set up why this matters
3. **Main Content** - 3-5 major sections exploring the topic
4. **Real Examples** - Concrete scenarios and code where relevant
5. **Key Takeaways** - Actionable insights
6. **Conclusion** - Tie it all together

**Writing Tips:**
- Keep paragraphs short (2-4 sentences)
- Use bullet points for lists
- Include code blocks for technical content
- Add blockquotes for key insights
- Use H2 for major sections, H3 for subsections
- Never go deeper than H3

### Step 6: Add Code Examples (If Technical)

For technical posts, include well-formatted code:

```python
# Use triple backticks with language
def example_function():
    """Clear docstrings explaining purpose"""
    return "Make code readable and relevant"
```

### Step 7: Create the File

Save the blog post as `/Users/kz127/code/auriga-web/content/blog/[slug].mdx`

**Slug naming:**
- Use kebab-case (lowercase with hyphens)
- Be descriptive but concise
- Match the main topic
- Examples: `monkeymode-ai-driven-development`, `building-auriga-agents-with-skills`

### Step 8: Verify Quality Checklist

Before finalizing, verify:

- [ ] Frontmatter is complete and accurate
- [ ] Title promises clear value
- [ ] Description is compelling and under 160 chars
- [ ] Cover image generated and saved correctly
- [ ] Introduction hooks the reader immediately
- [ ] Each section has a clear H2 heading
- [ ] Paragraphs are short (2-4 sentences)
- [ ] Key takeaways section is present
- [ ] Conclusion ties everything together
- [ ] No spelling or grammar errors
- [ ] Code examples (if any) are properly formatted
- [ ] Published is set to `true`

## Example Posts for Reference

Two excellent example posts to reference:

1. **MonkeyMode: The AI-Driven Development Lifecycle** (`monkeymode-ai-driven-development.mdx`)
   - Great example of process explanation
   - Strong use of structure (4 phases)
   - Concrete real-world example included
   - Clear key takeaways

2. **Building Auriga Agents with Skills** (`building-auriga-agents-with-skills.mdx`)
   - Excellent technical deep-dive
   - Problem → Solution → Impact structure
   - Real numbers and specific examples
   - Shows developer experience improvements

## Common Pitfalls to Avoid

❌ **Don't:**
- Use generic marketing language ("revolutionary", "game-changing" without proof)
- Write long, dense paragraphs (hard to read)
- Skip the cover image (visual is critical)
- Forget actionable takeaways
- Make claims without evidence or examples
- Use overly complex jargon without explanation

✅ **Do:**
- Be specific and concrete
- Include real examples and numbers
- Break content into scannable sections
- Generate monkey superhero cover images
- Provide actionable insights
- Explain technical concepts clearly

## Template for Quick Start

Use this as a starting point:

```markdown
---
title: "[Main Concept]: [Specific Benefit or Insight]"
description: "[What readers will learn and why it matters] (150-160 chars)"
date: "YYYY-MM-DD"
category: "AI & Education"
tags: ["Tag1", "Tag2", "Tag3"]
coverImage: "/images/blog/your-slug-cover.jpg"
published: true
---

# Introduction

[Hook: Problem, question, or surprising insight]

[Brief context of what this post covers]

## The Problem/Challenge

[Explain the issue this post addresses]

[Why it matters to readers]

## The Solution/Insight

[Main content section 1]

### Key Aspect 1

[Details and examples]

### Key Aspect 2

[Details and examples]

## Real-World Example

[Concrete scenario showing the concept in practice]

[Specific numbers, outcomes, or code]

## Key Takeaways

- Actionable insight 1
- Actionable insight 2
- Actionable insight 3

## Conclusion

[Summary of main points]

[Forward-looking statement or call to engage]

---

_[Optional closing thought]_
```

## Image Generation with nano_bannan

When generating images, use this process:

1. **Analyze the blog topic** - What's the main concept?
2. **Create a descriptive prompt** following the visual theme guidelines
3. **Include key elements:**
   - Diverse superhero animal characters (gorillas, lions, bears, eagles, wolves, foxes, etc.)
   - Comic book aesthetic
   - Vibrant purple/orange/blue colors
   - Dynamic action or team pose showing collaboration
   - Urban, futuristic, or tech background as appropriate
   - Relevant comic book text ("VOTE!", "BUILD!", "POW!", etc.)
4. **Generate and save** to correct path in public/images/blog/
5. **Verify** the image matches the playful, energetic brand style

The goal is to maintain visual consistency across all blog posts while making each image unique and relevant to its specific topic. The diverse animal team represents different strengths and perspectives coming together—reinforcing the collaborative nature of the Auriga community.

## Final Notes

Remember: The best blog posts:
- Teach something genuinely useful
- Use real examples and specifics
- Are easy to scan and read
- Have engaging superhero animal team visuals
- Leave readers with actionable insights

When in doubt, reference the existing blog posts as examples of tone, structure, and quality.
