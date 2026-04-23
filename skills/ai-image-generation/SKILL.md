---
name: image-prompt
description:
  Generate optimized prompts for AI image generators. Use when the user invokes image-prompt or asks to create, write, craft, or generate a prompt for any AI image generator (e.g. Imagen, Midjourney, DALL-E, Stable Diffusion, Flux,Firefly, or similar). Also triggers when the user says "image prompt", "AI image prompt", or "help me describe an image".
---

# AI Image Prompt Generator

Generate high-quality, optimized prompts for AI image generators, based on
widely applicable prompting best practices.

---

## Choosing a Model

If the user hasn't specified a model, ask which one they're using so you can
tailor advice. Common options include:

| Model | Provider | Notes |
|---|---|---|
| Imagen 3 / Imagen 4 | Google (Gemini) | Strong photorealism, text rendering |
| DALL-E 3 | OpenAI (ChatGPT) | Natural-language friendly |
| Midjourney v6+ | Midjourney | Strong artistic style control |
| Stable Diffusion / Flux | Various | Tag-friendly but supports natural language |
| Firefly | Adobe | Commercially safe, style references |
| Others | Various | Apply general principles below |

Different models have different strengths, but the core principles below work
across all of them. Note any model-specific tips in your output when relevant.

---

## Core Principles

All modern AI image generators understand intent, physics, and composition.
They reward clear creative direction over keyword lists.

### Golden Rules

1. **Natural language over tag soup** — Write as if briefing a human artist,
   not listing keywords.
   - BAD: `dog, park, sunset, 4k, realistic, cinematic`
   - GOOD: `A golden retriever bounding through a sun-dappled park at golden
     hour, shot from a low angle with shallow depth of field`

2. **Specificity matters** — Define subjects precisely with materiality,
   texture, and detail.
   - Instead of "a woman": "a sophisticated elderly woman wearing a vintage
     tweed suit"
   - Include materials: "matte finish," "brushed steel," "soft velvet,"
     "weathered leather"

3. **Provide context about purpose** — Mention the use case or audience.
   - "Create a hero image for a premium coffee brand's website" helps the model
     infer professional lighting, composition, and mood.

4. **Edit, don't re-roll** — When a generated image is mostly correct, request
   specific conversational changes rather than starting over (supported by
   models with edit/chat features like Imagen, DALL-E 3, Firefly).

---

## Workflow

### Step 1: Gather the User's Vision

Ask the user to describe what they want. If their description is vague, ask
targeted questions to fill in these dimensions:

| Dimension | What to ask | Examples |
|---|---|---|
| Subject | Who or what is the main focus? | Person, object, scene, abstract |
| Setting/Environment | Where does this take place? | Urban, nature, studio, fantastical |
| Mood/Atmosphere | What feeling should it evoke? | Serene, dramatic, playful, mysterious |
| Style | What visual style? | Photorealistic, watercolor, cinematic, anime |
| Composition | How should it be framed? | Close-up, wide shot, bird's eye |
| Lighting | What lighting conditions? | Golden hour, dramatic side-light, neon |
| Purpose/Use case | Where will this image be used? | Social media, website, print, presentation |
| Text (if any) | Any text to render in the image? | Put exact text in quotation marks |
| Aspect ratio | Portrait, landscape, or square? | 16:9, 9:16, 1:1, 4:3 |

Do **not** ask all questions at once. Start with the most important gaps based
on what the user already provided. Ask 2–3 questions maximum per round.

---

### Step 2: Build the Prompt

Construct the prompt using this structure (not all elements are required — use
what's relevant):

```
[Style/medium] of [specific subject with details] in [setting/environment],
[action or pose], [lighting description], [mood/atmosphere],
[camera angle/composition], [additional details: texture, color palette, materiality].
[Purpose context if relevant.]
```

**Key techniques to apply:**

- **Camera language:** "wide establishing shot," "tight close-up,"
  "over-the-shoulder," "Dutch angle," "shallow depth of field"
- **Lighting specifics:** "Rembrandt lighting," "backlit with rim light,"
  "soft window light from the left," "dramatic chiaroscuro"
- **Material and texture:** "brushed aluminum," "hand-knit wool,"
  "cracked leather," "translucent glass"
- **Color direction:** "muted earth tones," "high-contrast complementary
  colors," "monochromatic blue palette"
- **Text rendering:** Place exact text in quotation marks — many modern models
  (especially Imagen and DALL-E 3) have strong text legibility
- **Aspect ratio:** Suggest appropriate ratio for the use case

**Model-specific tips (mention when relevant):**
- *Midjourney:* Accepts `--ar 16:9`, `--style`, `--v 6` parameters after the
  prompt
- *Stable Diffusion / Flux:* Negative prompts (`--no blur, watermark`) can be
  helpful
- *DALL-E 3:* Responds well to conversational, intent-driven language
- *Imagen:* Excels at photorealism and text rendering; supports reference
  images for style/character consistency

---

### Step 3: Present the Prompt with Rationale

Output the prompt in a clearly marked block, followed by brief rationale notes:

```
PROMPT:
─────────────────────────────────────────────
[The generated prompt text]
─────────────────────────────────────────────

WHY THESE CHOICES:
- [Element]: [Brief explanation of why this detail was included]
- [Element]: [How it helps the model produce better results]
```

---

### Step 4: Offer Refinement

After presenting the prompt, ask the user:

> "Would you like to adjust anything? I can refine the style, composition,
> lighting, mood, or any other element. You can also ask me to create a variant
> with a different approach."

Continue iterating until the user is satisfied.

---

## Special Capabilities to Leverage

Mention these to the user when relevant:

### Reference Images and Consistency
Many models support multi-image context:
- Use uploaded images as style references: "Use the uploaded image as a strict
  style reference"
- Character consistency: "Keep facial features exactly the same as the
  reference"
- Setting mashups: "Keep the character from Image 1 but place them in the
  setting from Image 2"

### Conversational Editing
After generating an image, models with edit features accept natural-language
changes:
- "Change the sunny day to a rainy night"
- "Remove the person in the background and add a potted plant"
- "Make the text neon blue instead of white"

### Text in Images
Models with strong text rendering (Imagen, DALL-E 3, Firefly) can produce
legible text. Always put exact text in quotation marks. Specify text style if
needed: "bold sans-serif," "handwritten script," "retro neon sign."

### Dimensional Translation
Some models can convert between 2D and 3D:
- Hand-drawn sketches to photorealistic renders
- Floor plans to 3D room visualizations
- Wireframes to high-fidelity UI mockups

---

## Anti-Patterns to Avoid

| Anti-pattern | Fix |
|---|---|
| Tag soup | Rewrite as natural sentences |
| Vague subjects ("a person") | Add specific details |
| Missing mood/lighting | Always include — they dramatically affect output |
| No context | Include purpose/use case when relevant |
| Over-prompting | Remove contradictory or excessive details |

---

## Example Prompts

Use these as calibration for quality:

**Product photography:**
> A flat lay of artisanal coffee beans spilling from a matte black ceramic cup
> onto a weathered oak table, soft directional window light from the upper left,
> warm earth tones with deep shadows, shot from directly above, styled for a
> premium coffee brand's Instagram feed.

**Portrait:**
> A cinematic medium close-up portrait of a jazz musician mid-performance, eyes
> closed, sweat glistening under warm amber stage lighting, shallow depth of
> field with bokeh from string lights in the background, shot on what looks like
> 35mm film with natural grain.

**Text-heavy design:**
> A vintage-style concert poster with the text "MIDNIGHT REVERIE" in bold art
> deco typography at the top, a silhouette of a saxophone player against a deep
> indigo night sky with a full moon, "Live at The Blue Note — March 15, 2026"
> in smaller elegant serif type at the bottom, gold and navy color palette.

**Fantasy/Illustration:**
> A lush watercolor illustration of a hidden forest library, towering bookshelves
> made from living trees with glowing mushrooms as reading lamps, a cozy armchair
> draped in moss-green velvet, shafts of golden sunlight filtering through the
> canopy above, whimsical and enchanting atmosphere.

---

## Sources

Prompting advice in this skill is based on widely applicable best practices
drawn from documentation and guidance published by Google, OpenAI, Midjourney,
Adobe, and the broader AI image generation community. Always check the official
documentation for your specific model for the latest capabilities and parameters.