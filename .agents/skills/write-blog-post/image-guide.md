# Image Generation Guide for Blog Posts

This guide provides specific instructions for generating monkey-themed superhero images using nano_bannan.

## Visual Brand Guidelines

### Core Theme: Comic Book Superhero Monkeys

Every blog cover image should feature:
- **Characters**: Gorillas, monkeys, or other primates as superhero characters
- **Style**: Vibrant comic book/animated illustration style
- **Mood**: Energetic, fun, powerful, inspiring, professional

### Color Palette

Primary colors:
- **Purple**: #7C3AED to #A855F7 (rich, vibrant purples)
- **Orange**: #FB923C to #FDBA74 (warm, sunset oranges)
- **Blue**: #3B82F6 to #60A5FA (bright, superhero blues)
- **Gold/Yellow**: #FCD34D to #FBBF24 (accents and highlights)

Supporting colors:
- Red for superhero suits (#EF4444)
- Dark navy/black for backgrounds (#1E293B)
- White for highlights and comic text

### Composition Patterns

**Pattern 1: Team Pose (MonkeyMode style)**
```
Central hero (gorilla) in foreground wearing superhero suit with emblem
Supporting characters (monkeys, lemurs, etc.) flanking sides
Standing on building rooftop or elevated platform
Purple/orange gradient sunset sky with clouds
Urban cityscape in background
Comic book action words ("POW!", "BOOM!") floating in scene
```

**Pattern 2: Technical Diagram (Skills Architecture style)**
```
Dark background (navy/black)
Central gorilla character representing the core system
Golden circuit-like lines connecting to technical panels
Other monkey characters integrated into diagram
Professional but playful aesthetic
Purple, gold, and blue color scheme
```

**Pattern 3: Action Scene**
```
Monkey heroes in action poses
Dynamic movement and energy
Flying through city or workspace
Tech elements integrated (computers, code, tools)
Vibrant colors with motion blur effects
```

## Example Prompts by Blog Topic

### Development Process/Workflow Posts

```
Comic book style illustration of superhero monkeys working together as a team. 
Central gorilla leader in blue and red superhero suit with 'M' emblem standing 
confidently on a rooftop. Other monkey superheroes in matching uniforms positioned 
around him - a baboon in a cape, a lion with golden mane in blue suit, a lemur 
with striped tail, and a small tarsier, all wearing superhero costumes. Purple 
and orange gradient sunset sky with fluffy clouds. Modern city skyline silhouette 
in background. Comic book 'POW!' and 'BOOM!' text in yellow and cyan. Vibrant, 
energetic, inspiring mood. High detail digital illustration.
```

### Technical Architecture Posts

```
Professional technical diagram illustration with superhero monkey mascots. Dark 
navy background with glowing golden circuit board lines connecting modular panels. 
Central gorilla superhero character in cape representing the core system. Four 
illuminated panels showing icons for different technical components - files, 
search, code, databases. Other smaller monkey characters integrated into the 
diagram - positioned near different modules. Clean, modern design with purple, 
gold, and white accents. Playful but professional aesthetic suitable for 
technical documentation.
```

### AI/Agent Feature Posts

```
Futuristic comic book illustration of monkey AI agents. Central gorilla in 
high-tech superhero armor with glowing blue accents. Surrounding monkey characters 
wearing specialized suits with different emblems representing different capabilities. 
Holographic screens and AI interface elements floating around them. Purple and 
cyan color scheme with neon highlights. Digital cityscape background with data 
streams. Dynamic action poses. Comic book style with modern tech aesthetic.
```

### Education/Learning Posts

```
Inspiring comic book scene of mentor monkey superheroes guiding younger monkey 
sidekicks. Wise gorilla teacher in scholarly cape and superhero suit. Student 
monkeys in training uniforms practicing their skills. School or academy building 
in background. Bright, optimistic color palette - purple sky, golden light, 
blue accents. Comic book speech bubbles showing teaching moments. Warm, 
encouraging, educational mood.
```

### Success Story/Case Study Posts

```
Victory scene of superhero monkey team celebrating achievement on city rooftop. 
Gorilla leader holding trophy or emblem high. Team members in various hero poses 
showing triumph. Dramatic sunset sky with purple and orange clouds. City 
buildings illuminated below. Comic book 'SUCCESS!' text in bold yellow letters. 
Fireworks or light effects in background. Energetic, triumphant, celebratory mood.
```

## Image Generation Workflow

### Step 1: Analyze Blog Topic
- What's the main concept? (process, architecture, feature, success story)
- What mood fits? (energetic, technical, inspiring, educational)
- Who's the audience? (developers, students, general)

### Step 2: Choose Composition Pattern
- Team pose for process/workflow topics
- Technical diagram for architecture topics
- Action scene for feature announcements
- Victory scene for success stories

### Step 3: Construct Prompt

Template structure:
```
[STYLE] illustration of [CHARACTERS] [DOING WHAT]. 
[MAIN CHARACTER DESCRIPTION] in [SETTING]. 
[SUPPORTING CHARACTERS] positioned [WHERE]. 
[BACKGROUND DESCRIPTION]. 
[COLOR PALETTE]. 
[MOOD AND AESTHETIC].
```

### Step 4: Generate with nano_bannan

Call the image generation tool with your prompt and appropriate filename.

### Step 5: Save Correctly

Path: `/Users/kz127/code/auriga-web/public/images/blog/[slug]-cover.jpg`

Naming convention:
- Use the blog post slug (kebab-case)
- Add `-cover` suffix
- Use `.jpg` extension

Examples:
- `monkeymode-workflow-cover.jpg`
- `ai-agents-architecture-cover.jpg`
- `skills-system-explained-cover.jpg`

## Quality Checklist

Before finalizing an image, verify:

- [ ] Features monkey/primate characters as heroes
- [ ] Uses vibrant purple, orange, blue color palette
- [ ] Has energetic, professional aesthetic
- [ ] Matches the blog topic conceptually
- [ ] Fits comic book superhero theme
- [ ] Is visually distinct from other blog covers
- [ ] Works well as a header image (wide aspect ratio)
- [ ] Characters are well-defined and detailed
- [ ] Composition is balanced and eye-catching

## Common Issues and Fixes

### Issue: Image too dark
**Fix**: Add "bright, vibrant, well-lit" to prompt, emphasize golden highlights

### Issue: Too cartoonish/childish
**Fix**: Add "professional, high-detail digital illustration" to prompt

### Issue: Doesn't match brand
**Fix**: Explicitly specify purple/orange gradient sky, comic book style

### Issue: Characters unclear
**Fix**: Describe each character specifically with details about costume and pose

### Issue: Not tech-focused enough
**Fix**: Add tech elements - holographic screens, circuit lines, code elements

## Inline Images (Optional)

If blog post needs additional illustrative images:

### Diagrams and Charts
- Dark background with golden accents
- Include subtle monkey mascot in corner
- Professional technical style
- Save as `[slug]-diagram.jpg` or `[slug]-flow.jpg`

### Screenshot-style Images
- Show UI with monkey mascot integrated
- Use brand colors for highlights
- Save as `[slug]-feature.jpg` or `[slug]-example.jpg`

## Prompt Refinement Tips

**Make prompts more specific by adding:**
- Character details (costume colors, emblems, accessories)
- Lighting details (golden hour, neon glow, dramatic shadows)
- Composition details (low angle, heroic pose, team formation)
- Mood descriptors (triumphant, focused, dynamic, collaborative)
- Style references (comic book, animated, digital art, illustration)

**Avoid vague terms:**
- ❌ "Nice background" → ✅ "Purple gradient sunset sky"
- ❌ "Monkey character" → ✅ "Gorilla in blue superhero suit with 'M' emblem"
- ❌ "Cool effect" → ✅ "Comic book 'POW!' text in yellow with halftone dots"

## Testing and Iteration

If first generation doesn't match expectations:

1. **Identify the issue** - Too dark? Wrong mood? Missing elements?
2. **Refine prompt** - Add specific descriptors for what's missing
3. **Regenerate** - Try again with improved prompt
4. **Compare** - Does new version better match existing blog images?
5. **Adjust** - Keep iterating until it fits the brand

Remember: Consistency across blog images builds brand recognition. All images should feel like they're part of the same superhero monkey universe while being unique to their specific topic.

## Final Notes

The goal is to make blog posts visually distinctive and memorable while maintaining a consistent brand identity. The monkey superhero theme:

- **Differentiates** Auriga/MonkeyMode from generic tech content
- **Humanizes** complex technical topics through playful characters  
- **Engages** readers with vibrant, energetic visuals
- **Reinforces** the brand across all content

When in doubt, reference the two existing cover images as your north star for quality and style.
