---
name: image-prompt
description: Generate optimized prompts for AI image generators tailored for restaurant owners and food businesses. Use when the user invokes /image-prompt or asks to create, write, craft, or generate a prompt for any AI image generator (e.g. Imagen, Midjourney, DALL-E, Stable Diffusion, Flux, Firefly, or similar) in the context of food, dishes, restaurant interiors, menus, or hospitality branding. Also triggers when the user says "image prompt", "food photo prompt", "restaurant image", "menu image", or "help me describe a food photo".
---

# Restaurant & Food Image Prompt Generator

Generate high-quality, optimized prompts for AI image generators — tailored
specifically for restaurant owners, chefs, and food businesses who need
stunning visuals for menus, social media, websites, and marketing.

## API Input Hints

When this skill is used via `/v1/prompts/improve`:

- If `reference_images` are provided, explicitly use them as style/composition/subject anchors.
- If `mask_image` is provided, write a mask-aware edit/inpaint prompt so unmasked regions are preserved.
- Mention reference and mask intent directly in the final prompt text so downstream generators can apply them correctly.

---

## Choosing a Model

If the user hasn't specified a model, ask which one they're using so you can
tailor advice. Common options include:

| Model | Provider | Notes |
|---|---|---|
| Imagen 3 / Imagen 4 | Google (Gemini) | Exceptional food texture and photorealism |
| DALL-E 3 | OpenAI (ChatGPT) | Natural-language friendly, good for plating concepts |
| Midjourney v6+ | Midjourney | Outstanding artistic food photography style |
| Stable Diffusion / Flux | Various | Flexible, fine-tunable for specific cuisines |
| Firefly | Adobe | Commercially safe — ideal for print menus and ads |
| Others | Various | Apply general principles below |

Different models have different strengths, but the core principles below work
across all of them. Note any model-specific tips in your output when relevant.

---

## Core Principles

Great restaurant visuals sell food before the first bite. AI image generators
reward clear, sensory creative direction — not keyword lists.

### Golden Rules

1. **Make it look appetizing first** — Every prompt should prioritize
   appetite appeal: fresh ingredients, vibrant colors, visible steam or
   texture, perfect plating.
   - BAD: `pasta, restaurant, nice, 4k`
   - GOOD: `A steaming bowl of hand-rolled tagliatelle coated in a glossy
     truffle butter sauce, topped with freshly shaved Parmigiano and a
     sprig of thyme, photographed on a rustic linen tablecloth under warm
     side-light, shallow depth of field`

2. **Describe the dish in chef's language** — Use culinary terms for
   texture, preparation, and garnish. This dramatically improves accuracy.
   - "seared," "charred," "slow-braised," "emulsified," "hand-rolled,"
     "torched," "crisped," "lacquered," "deglazed"
   - "garnished with microgreens," "finished with a drizzle of aged
     balsamic," "dusted with sumac"

3. **Nail the surface and setting** — The surface under the food is as
   important as the food itself.
   - Options: "weathered oak board," "slate tile," "white ceramic,"
     "dark matte stone," "linen napkin," "marble countertop," "terracotta"

4. **Match the visual style to the brand** — A fine-dining restaurant
   needs a different aesthetic than a street food pop-up.
   - Fine dining: "minimalist plating, dark moody background, dramatic
     side-lighting"
   - Casual/bistro: "bright natural light, rustic wooden table, relaxed styling"
   - Street food/fast casual: "bold colors, overhead shot, energetic styling"

5. **Provide context about purpose** — Mention where the image will be used.
   - "for a premium restaurant's Instagram feed"
   - "for a printed dinner menu"
   - "for a delivery app listing thumbnail"

---

## Workflow

### Step 1: Gather the Restaurant's Needs

Ask the user to describe what they want. If their description is vague, ask
targeted questions across these dimensions:

| Dimension | What to ask | Examples |
|---|---|---|
| Dish / Subject | What is the dish or item being photographed? | Grilled salmon, cocktail, dessert platter, interior |
| Cuisine / Style | What type of cuisine or brand aesthetic? | Italian, Japanese, Modern European, Street Food |
| Plating Style | How is it plated or presented? | Rustic family-style, fine-dining minimalist, deconstructed |
| Surface & Props | What's under and around the dish? | Dark slate, linen, wooden board, fresh herbs nearby |
| Shot Type | How should it be framed? | Overhead flat lay, 45° hero shot, close-up detail |
| Lighting | What lighting feel? | Natural window light, moody dramatic, warm candlelight |
| Mood / Brand Feel | What atmosphere should the image convey? | Cozy, luxurious, fresh, bold, artisanal |
| Season / Occasion | Any seasonal or event context? | Summer salad, Christmas menu, Valentine's special |
| Usage | Where will the image be used? | Instagram, printed menu, website hero, delivery app |
| Aspect Ratio | What format is needed? | 1:1 (Instagram), 16:9 (website), 4:5 (portrait feed) |

Do **not** ask all questions at once. Start with the most important gaps based
on what the user already provided. Ask 2–3 questions maximum per round.

---

### Step 2: Build the Prompt

Use this structure (not all elements required — use what's relevant):

```
[Photography style] of [dish name with culinary detail and garnish]
served on [surface/vessel], [plating description],
[lighting], [mood/atmosphere], [shot type/angle],
[color palette or brand aesthetic], [props or context details].
[Usage purpose if relevant. Aspect ratio if specified.]
```

**Key techniques to apply:**

**Food Photography Shot Types:**
- "overhead flat lay" — best for bowls, platters, pizza, salads
- "45-degree hero shot" — the classic restaurant standard; shows height and
  layers (burgers, cakes, stacked dishes)
- "straight-on eye-level" — great for drinks, plated mains, tiered desserts
- "tight macro close-up" — texture details: seared crust, chocolate drizzle,
  bubbles in a craft beer
- "lifestyle in-scene" — hands reaching for food, fork mid-lift, casual dining
  context

**Lighting for Food:**
- "soft natural window light from the left, gentle fill shadow on right"
- "warm side-lighting at 45°, highlighting steam and gloss"
- "moody low-key lighting, dark background, single light source"
- "bright airy high-key lighting, white background, fresh feel"
- "warm candlelight ambience, bokeh background"
- "golden-hour light through a restaurant window"

**Culinary Detail Language:**
- Textures: "crispy golden crust," "silky emulsified sauce," "charred grill
  marks," "glossy lacquer," "flaky pastry layers," "velvety foam"
- Freshness cues: "glistening with olive oil," "steam rising gently,"
  "condensation on the glass," "freshly torn basil," "vibrant microgreens"
- Garnish precision: "three drops of truffle oil," "a scattering of fleur de
  sel," "edible flower in the upper-right corner"

**Surface & Prop Direction:**
- "aged oak cutting board with a linen napkin folded to the left"
- "matte black slate tile, no props, negative space on right"
- "white marble with fresh rosemary sprigs and a small ramekin of sauce"
- "terracotta tile with scattered dried chili flakes and a wedge of lemon"

**Brand Aesthetic Descriptors:**
- Fine dining: "dark matte background, minimalist plating, dramatic chiaroscuro,
  luxury editorial feel"
- Farm-to-table / artisan: "rustic textures, warm tones, natural props (linen,
  wood, stone), handcrafted feel"
- Fast casual / street food: "vibrant saturated colors, bold overhead framing,
  energetic styling"
- Café / brunch: "bright airy, white or pastel surfaces, fresh flowers,
  lifestyle feel"
- Bar / cocktails: "moody low-key lighting, dark bar top, glassware reflections,
  ice details"

**Model-specific tips (mention when relevant):**
- *Midjourney:* Add `--style raw` for more realistic food photography; `--ar 4:5`
  for Instagram portrait
- *Stable Diffusion / Flux:* Negative prompts like `--no plastic, artificial,
  cartoon, oversaturated` help keep food looking real
- *DALL-E 3:* Very responsive to cuisine-specific context ("Neapolitan pizza,"
  "kaiseki plating") — be specific
- *Firefly:* Best for commercially safe menu and print use; upload brand
  color swatches as style reference
- *Imagen:* Excels at texture and photorealism; reference image upload useful
  for matching existing menu photography style

---

### Step 3: Present the Prompt with Rationale

```
PROMPT:
─────────────────────────────────────────────
[The generated prompt text]
─────────────────────────────────────────────

WHY THESE CHOICES:
- [Element]: [Brief explanation of why this detail was included]
- [Element]: [How it serves the restaurant's marketing goal]

USAGE TIP:
- [Recommended platform, aspect ratio, or iteration suggestion]
```

---

### Step 4: Offer Refinement

After presenting the prompt, ask the user:

> "Would you like to adjust anything? I can refine the plating style,
> lighting mood, surface, brand aesthetic, or shot angle. I can also write
> a variant prompt for a different usage — for example, one version for
> Instagram and one for a printed menu."

Continue iterating until the user is satisfied.

---

## Restaurant Use Cases — Quick Reference

Mention these to guide the user toward the right prompt type:

| Use Case | Best Shot Type | Key Lighting | Aspect Ratio |
|---|---|---|---|
| Instagram feed post | 45° hero or overhead | Bright natural or warm side-light | 1:1 or 4:5 |
| Instagram Stories / Reels cover | Portrait close-up | Moody or natural | 9:16 |
| Printed menu | Clean overhead or 45° hero | Bright, even, white BG option | Variable |
| Website hero banner | Wide landscape, lifestyle | Natural or golden-hour | 16:9 |
| Delivery app thumbnail | Overhead flat lay, bold | Bright, saturated | 1:1 |
| Google Business / review | Lifestyle in-scene | Warm ambient restaurant light | 4:3 or 16:9 |
| Event / seasonal promotion | Styled with props and branding | Festive, themed | 1:1 or 16:9 |
| Interior / ambience shot | Wide environmental | Warm golden ambient | 16:9 |

---

## Special Capabilities to Leverage

### Reference Image Consistency
Upload an existing dish photo or menu style to match:
- "Match the plating style and color palette of the uploaded reference photo"
- "Keep the same surface (dark slate) and lighting mood as the reference"
- "This is our existing menu photography style — generate a new dish that
  matches it exactly"

### Seasonal and Limited-Time Menu Items
- Describe seasonal ingredients explicitly: "garnished with a candied
  kumquat and a sprig of fresh tarragon — spring menu feel"
- Add seasonal mood: "cozy autumn atmosphere, warm amber tones, fallen
  leaves as background props"

### Interior and Ambience Shots
For restaurant space imagery:
- "Wide-angle interior shot of a warm, candlelit bistro at dinner service,
  soft bokeh on wine glasses, wooden tables with linen napkins, empty
  but inviting, editorial restaurant photography style"

### Menu Text Overlays
Models with strong text rendering (Imagen, DALL-E 3, Firefly) can include
legible text. Always put exact text in quotation marks:
- "Include the text 'Truffle Risotto — €24' in elegant serif type in the
  lower-right corner"
- "Add a subtle 'NEW' badge in the top-left in the restaurant's brand color"
- Only add text when the use case requires it (menu board, promo banner,
  ad creative, story card). For pure food photography, avoid overlays.
- When text is required, specify typography clearly:
  - font style/family (e.g., elegant serif, modern sans-serif, handwritten)
  - font weight (light, regular, semibold, bold)
  - font color and contrast (e.g., warm ivory on dark wood background)
  - placement and hierarchy (headline vs subtext) so the composition stays clean

---

## Anti-Patterns to Avoid

| Anti-pattern | Fix |
|---|---|
| Generic food description ("nice pasta") | Use culinary language: preparation method, garnish, texture |
| Wrong shot type for the platform | Match shot angle to where the image will be used |
| Ignoring the surface | Always specify what the dish sits on |
| No lighting direction | Lighting makes or breaks food photography — always include it |
| Mismatched brand aesthetic | Align the mood and style to the restaurant's positioning |
| Oversaturated / artificial look | Add "natural colors," "true-to-life tones," or negative prompts |
| Cluttered composition | Use "negative space on the right," "minimal props," "clean background" |

---

## Example Prompts

**Fine dining main course (Instagram / menu):**
> Professional food photography of a pan-seared duck breast, skin
> lacquered and caramelized to a deep mahogany, fanned across a smear of
> roasted beetroot purée on a matte white ceramic plate. Garnished with
> pickled blackberries, crispy duck skin shards, and a few drops of
> aged balsamic. Dramatic side-lighting from the left, dark slate
> background, moody and luxurious atmosphere. 45-degree hero shot,
> shallow depth of field. Styled for a fine-dining restaurant's
> Instagram feed. 4:5 aspect ratio.

**Casual café brunch (Instagram / website):**
> Bright, airy food photography of a smashed avocado toast on thick-cut
> sourdough, topped with two poached eggs (yolk just broken and flowing),
> scattered chili flakes, microgreens, and a wedge of lemon. Served on a
> speckled ceramic plate on a white marble surface with a linen napkin to
> the left and a small glass of fresh orange juice slightly out of focus
> in the background. Soft natural window light from the right. Fresh,
> lifestyle feel. Overhead flat lay. 1:1 square format.

**Craft cocktail (bar menu / social):**
> Editorial cocktail photography of a smoked negroni in a crystal-cut
> rocks glass, a large hand-carved ice sphere slowly melting inside,
> a charred orange peel twisted on the rim. Shot straight-on at eye
> level on a dark walnut bar top. Moody low-key lighting, single warm
> light source from above-left, deep shadows. Condensation on the glass.
> Bokeh of warm bar lights in the background. Sophisticated, masculine
> atmosphere. 4:5 portrait.

**Street food / fast casual (delivery app / social):**
> Bold overhead flat lay of a loaded Korean BBQ beef burger, sesame
> brioche bun slightly open to reveal the double patty with melted
> cheddar, gochujang aioli dripping down the side, crispy shallots,
> and pickled daikon. Served in branded kraft paper on a dark concrete
> surface with scattered sesame seeds and a side of fries. Bright,
> saturated lighting, energetic street-food styling. 1:1 square.

**Restaurant interior / ambience:**
> Wide-angle interior photography of a warm, intimate Italian trattoria
> at dinner service. Exposed brick walls, low Edison bulb pendant lights
> casting a golden glow, wooden tables set with white linen and flickering
> tea-light candles. Wine glasses catch the warm light. Slightly shallow
> depth of field, bokeh in the background. Inviting, romantic atmosphere.
> No people — empty but welcoming. Editorial hospitality photography style.
> 16:9 landscape.

**Seasonal / promotional (event marketing):**
> Styled food photography of a Christmas spiced sticky toffee pudding
> served in a deep terracotta ramekin, warm toffee sauce pooling over
> the edge, a quenelle of clotted cream melting on top, dusted with
> gold edible glitter. Christmas holly and cinnamon sticks as background
> props on a dark walnut surface. Warm candlelit ambience, festive and
> indulgent atmosphere. 45-degree hero shot. 1:1 square format.

---

## Sources

Prompting advice in this skill is based on widely applicable best practices
drawn from professional food photography guides, documentation published by
Google (Imagen), OpenAI (DALL-E), Midjourney, Adobe (Firefly), and the
broader AI image generation and food styling community. Always check the
official documentation for your specific model for the latest capabilities
and parameters.
