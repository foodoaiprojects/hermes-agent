---
name: video-prompt
description: 
  Generate optimized prompts for AI video generators tailored for restaurant owners and food businesses. Use when the user invokes /video-prompt or asks to create, write, craft, or generate a prompt for any AI video generator (e.g. Sora, Runway, Kling, Pika, Hailuo, Veo, Luma Dream Machine, Wan, or similar) in the context of food, dishes, restaurant interiors, cooking processes, or hospitality marketing. Also triggers when the user says  "video prompt", "food video prompt", "restaurant reel", "menu video",  "cooking video", or "help me describe a food video".
---

# Restaurant & Food Video Prompt Generator

Generate high-quality, optimized prompts for AI video generators — tailored
specifically for restaurant owners, chefs, and food businesses who need
compelling video content for social media, websites, ads, and menus.

## API Input Hints

When this skill is used via `/v1/prompts/improve`:

- If `reference_images` are provided, use them as visual anchors for shot style, subject continuity, and scene framing.
- If `mask_image` is provided, write instructions for masked editing/preservation where supported by the target workflow.
- Keep the final prompt explicit about reference usage so the downstream video model can preserve look and identity.

---

## Choosing a Model

If the user hasn't specified a model, ask which one they're using so you can
tailor advice. Common options include:

| Model | Provider | Strengths for Restaurant Use |
|---|---|---|
| Sora | OpenAI | Long clips, cinematic quality, strong physics for liquids/steam |
| Veo 2 / Veo 3 | Google (Gemini) | Photorealism, camera control, audio generation (Veo 3) |
| Runway Gen-4 | Runway | Subject consistency, fine control over food textures |
| Kling 2.0 | Kuaishou | Smooth motion, great for pouring and plating sequences |
| Hailuo (MiniMax) | MiniMax | Fast generation, clean food close-ups |
| Pika 2.2 | Pika Labs | Creative effects, good for sizzle reels and social content |
| Luma Dream Machine | Luma AI | Fluid motion, strong for atmospheric restaurant ambience |
| Wan 2.1 | Alibaba | Open-source, good with detailed culinary descriptions |
| Others | Various | Apply general principles below |

Different models have different strengths, but the core principles below work
across all of them. Note any model-specific tips in your output when relevant.

---

## Core Principles

Restaurant video has one job: make the viewer hungry and curious. In addition
to visuals, you must direct **motion, time, and sensory atmosphere**.

### Golden Rules

1. **Every frame should sell the food or the feeling** — Describe motion that
   makes food look irresistible: melting, drizzling, sizzling, steaming,
   pulling apart.
   - BAD: `pizza being made`
   - GOOD: `an extreme close-up of a pizza being pulled apart, molten
     mozzarella stretching into long ribbons, steam rising from the
     charred crust, slow and deliberate motion`

2. **One shot per prompt** — AI video models work best on a single continuous
   shot. Describe one moment in time, not a sequence of scenes.

3. **Lead with the shot type and camera move** — Establish the cinematic
   framing before describing the food.
   - "Slow macro push-in on..." / "Overhead flat-lay with a slow pour..." /
     "Handheld follow shot of a chef's hands..."

4. **Describe physics explicitly** — Food has wonderful natural physics.
   Name them and the model will render them.
   - "steam curling upward," "sauce cascading off the spoon in a thick ribbon,"
     "ice clinking and swirling," "cheese bubbling and browning at the edges"

5. **Match the vibe to the brand** — A Michelin-starred restaurant needs
   slow, cinematic, moody clips. A street food brand needs fast, bold,
   energetic cuts.

6. **Specify duration and platform** — Short tight clips (3–5 s) for
   Instagram Reels/TikTok; longer atmospheric pieces (8–15 s) for websites
   and ads.

---

## Workflow

### Step 1: Gather the Restaurant's Needs

Ask the user to describe what they want. If their description is vague, ask
targeted questions across these dimensions:

| Dimension | What to ask | Examples |
|---|---|---|
| Subject | What dish, drink, ingredient, or scene? | Pasta, cocktail, chef plating, restaurant interior |
| Key Motion | What is the hero movement in the clip? | Cheese pull, sauce pour, sizzle, steam rising, hands plating |
| Setting | Where is this taking place? | Kitchen pass, dining room, bar, outdoor terrace |
| Shot Type | How should it be framed? | Overhead, 45° hero, macro close-up, wide ambient |
| Camera Movement | How does the camera move? | Static, slow push-in, slow pull-back, orbit around dish |
| Lighting | What lighting feel? | Warm candlelit, bright natural, moody dramatic, neon bar |
| Brand Mood | What atmosphere to convey? | Luxurious, rustic, fresh, energetic, intimate |
| Duration | How long is the clip? | 3 s, 5 s, 8 s, 10–15 s |
| Platform | Where will this be posted? | Instagram Reel, TikTok, website hero, YouTube ad |
| Aspect Ratio | What format? | 9:16 (Reels/TikTok), 16:9 (website/YouTube), 1:1 (feed) |
| Audio (if supported) | Any ambient sound or music? | Sizzle, pouring, ambient chatter, music mood |

Do **not** ask all questions at once. Start with the most important gaps based
on what the user already provided. Ask 2–3 questions maximum per round.

---

### Step 2: Build the Prompt

Use this structure (not all elements required — use what's relevant):

```
[Shot type + camera movement], [dish/subject with culinary detail]
[hero motion with physics description], [setting and surface],
[lighting description], [mood/atmosphere], [visual style].
[Audio if relevant. Duration and aspect ratio.]
```

**Key techniques to apply:**

**Shot & Camera Language for Food Video:**
- "extreme macro close-up, static" — melting, bubbling, steam details
- "overhead flat lay, slow pour from above" — sauces, dressings, toppings
- "45-degree hero angle, slow push-in" — the classic restaurant hero shot
- "eye-level straight-on, slight drift" — cocktails, plated mains
- "handheld follow, chef's POV" — kitchen prep, plating sequences
- "wide ambient pull-back" — restaurant atmosphere, dining room reveals

**Hero Motion Vocabulary (the money shots):**
- Cheese: "molten mozzarella pulls apart in slow, satisfying ribbons"
- Sauce: "thick hollandaise cascades off the spoon in an unbroken stream"
- Steam: "aromatic steam curls upward from the bowl in soft wisps"
- Sizzle: "butter foams and sizzles as the steak hits the cast-iron pan"
- Pour: "dark coffee drips slowly into a white ceramic cup, crema blooming"
- Ice: "crushed ice tumbles into a crystal glass, cocktail poured over in
  a slow arc"
- Slice: "a knife glides through a perfectly set mousse, revealing clean
  layers within"
- Dip: "a crust of sourdough is torn and dipped slowly into warm burrata"
- Drizzle: "honey drizzled in a thin golden thread over warm ricotta toast"
- Flame: "a blowtorch caramelizes the crème brûlée surface, sugar bubbling
  and browning to amber"

**Lighting for Food Video:**
- "soft natural window light, gentle side-shadow, warm and fresh"
- "warm tungsten side-light, deep shadows, moody and intimate"
- "bright overhead ring light, vibrant and saturated, social-media ready"
- "candlelight ambience, flickering warm bokeh in background"
- "golden-hour light streaming through restaurant windows"
- "cool back-light with rim highlight on steam and gloss"

**Physics and Sensory Anchors:**
- "condensation beads running down the cold glass"
- "herbs wilt slightly as they hit the hot pan, releasing a burst of steam"
- "the sauce pools naturally at the edge of the plate"
- "ice slowly melts in the amber liquid, edges dissolving"
- "dough stretches thin and translucent as the pizza base is pulled"

**Audio (for models supporting audio generation like Veo 3):**
- "AUDIO: aggressive sizzle as steak hits the pan, fading to a gentle
  simmer, ambient kitchen background noise"
- "AUDIO: soft pour of wine, crystal clink, distant murmur of a dinner
  service"
- "AUDIO: crisp crunch as the fork breaks through the crème brûlée,
  quiet and satisfying"
- Keep audio descriptions in a separate section for clarity

**Brand Aesthetic Descriptors:**
- Fine dining / Michelin: "slow, meditative pacing, dark moody palette,
  deliberate motion, cinematic grain"
- Farm-to-table / artisan: "warm natural light, rustic textures, unhurried
  motion, earthy tones"
- Brunch café / all-day dining: "bright airy, fresh colors, lifestyle feel,
  slight handheld energy"
- Street food / fast casual: "fast pacing, bold colors, punchy motion,
  high energy, vibrant"
- Bar / cocktails: "moody low-key lighting, slow elegant pours, reflections
  in glassware, smoky atmosphere"

**Model-specific tips (mention when relevant):**
- *Sora:* Handles fluid dynamics (pours, melts) exceptionally well; use for
  longer 8–15 s atmospheric clips
- *Veo 3:* Add a separate `[AUDIO]` block for synchronized sound design;
  strong camera move vocabulary
- *Runway Gen-4:* Best for maintaining dish consistency across multiple shots;
  upload reference image of the dish
- *Kling:* Excellent at smooth, realistic human hand motion — ideal for
  chef plating and cooking sequences
- *Pika:* Great for quick sizzle-reel style content and social-first clips;
  use for punchy 3–5 s Reels
- *Luma Dream Machine:* Strong for atmospheric restaurant ambience clips and
  seamless loops; good for website backgrounds

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

PLATFORM TIP:
- [Recommended aspect ratio, duration, posting context, or iteration advice]
```

---

### Step 4: Offer Refinement

After presenting the prompt, ask the user:

> "Would you like to adjust anything? I can refine the hero motion, camera
> angle, lighting mood, or brand atmosphere. I can also write a variant —
> for example, one version for Instagram Reels and a longer version for your
> website."

Continue iterating until the user is satisfied.

---

## Restaurant Use Cases — Quick Reference

| Use Case | Best Shot | Duration | Aspect Ratio | Mood |
|---|---|---|---|---|
| Instagram Reel / TikTok | Macro hero motion or overhead pour | 3–7 s | 9:16 | Punchy, energetic |
| Instagram feed loop | 45° hero, slow push-in | 4–6 s loop | 1:1 or 4:5 | Clean, appetizing |
| Website hero background | Wide ambient, slow drift | 8–15 s loop | 16:9 | Atmospheric, immersive |
| YouTube / paid ad | Cinematic sequence + hero shot | 10–30 s | 16:9 | Brand-appropriate |
| Google Business / listing | Clean 45° hero of key dish | 5–8 s | 16:9 or 1:1 | Appetizing, true-to-life |
| Chef's table / tasting menu | Slow macro plating sequence | 8–12 s | 16:9 | Luxurious, artful |
| Seasonal / event promo | Styled themed shot with motion | 5–10 s | 9:16 or 16:9 | Festive, themed |
| Menu launch | Dish hero + reveal motion | 5–8 s | 1:1 or 16:9 | Fresh, exciting |
| Restaurant ambience | Wide interior, warm ambient | 10–15 s loop | 16:9 | Inviting, warm |

---

## Special Capabilities to Leverage

### Image-to-Video from Dish Photos
Upload an existing dish photo and animate it:
- "Start from this still photo of our signature risotto and animate steam
  rising gently from the bowl, with a slow camera drift to the right"
- "Take this plated dessert image as the first frame and slowly pull back
  to reveal the full table setting"

### Seamless Loops for Website Backgrounds
- "Create a perfectly seamless 6-second loop of steam rising from a bowl of
  ramen — ending frame must match the opening frame exactly"
- "Looping cinemagraph: only the flickering candle flame moves; everything
  else on the restaurant table is completely still"

### Seasonal and Event Content
- "Slow macro shot of mulled wine being poured into a glass, cinnamon sticks
  and star anise floating to the surface, winter holiday atmosphere, warm
  amber light, 5 seconds"
- "Valentine's Day: close-up of a chocolate fondant being cut open, warm
  liquid chocolate flowing out slowly, rose petals slightly blurred in the
  background, candlelit, romantic"

### Kitchen Process and Chef Storytelling
- "Handheld follow shot of a chef's hands carefully placing microgreens on
  a plated dish with tweezers, kitchen pass in the background with warm
  light, deliberate and precise motion"
- "Wide shot of a wood-fired pizza oven, flames visible inside, a pizza
  being slid in on a long wooden peel, embers glowing"

### Audio-Synchronized Content (Veo 3 and select models)
- Match audio exactly to the visual moment:
  - "VISUAL: steak placed on a cast-iron grill. AUDIO: aggressive hiss and
    sizzle, then settling to a steady sear"
  - "VISUAL: champagne poured into a flute. AUDIO: fizzing bubbles, subtle
    clink, ambient dinner party background"

---

## Anti-Patterns to Avoid

| Anti-pattern | Fix |
|---|---|
| Static food description with no motion | Identify the hero movement and describe it with physics |
| Multiple scenes in one prompt | One shot per prompt — break sequences into separate prompts |
| Vague motion ("food moving") | Name the specific action: pour, pull, sizzle, drizzle, slice |
| No camera direction | Always specify shot type and whether camera moves or holds |
| Wrong duration for platform | Short (3–5 s) for Reels/TikTok; longer (8–15 s) for web/ads |
| Mismatched brand vibe | Fine dining needs slow/moody; street food needs fast/bold |
| Ignoring physics | Add at least one sensory physics detail per clip |

---

## Example Prompts

**Cheese pull hero (Instagram Reel):**
> Extreme macro close-up, static camera. A wood-fired margherita pizza is
> slowly pulled apart by two hands, molten fior di latte mozzarella
> stretching into long, satisfying ribbons between the two halves. Steam
> rises from the charred leopard-spotted crust. Warm overhead lighting,
> dark stone surface below. Slow, deliberate motion. Mouth-watering,
> indulgent atmosphere. 4 seconds, 9:16.

**Fine dining plating sequence (website / editorial):**
> Handheld follow shot from above, chef's POV, watching precise hands
> use tweezers to place a single edible viola flower as the final garnish
> on a minimalist fine-dining plate: a smear of cauliflower purée, three
> pieces of butter-poached lobster, dots of caviar butter. Kitchen pass
> glowing warmly in the background, rest of the brigade slightly blurred.
> Slow, deliberate, meditative pacing. Dark, moody, luxurious atmosphere.
> 8 seconds, 16:9.

**Cocktail pour (bar menu / social):**
> Straight-on eye-level, slight slow push-in. A bartender's hand tips
> a jigger of aged dark rum over a large hand-carved ice sphere in a
> crystal rocks glass. The liquid cascades in a slow, unbroken stream,
> swirling amber around the ice, which begins to cloud the edges slightly.
> A flamed orange peel rests on the rim. Moody low-key bar lighting,
> single warm source from above-left. Dark walnut bar top. Sophisticated,
> atmospheric. 5 seconds, 1:1.
> AUDIO: quiet liquid pour, faint ice crackle, distant ambient bar murmur.

**Street food sizzle (TikTok / Reel):**
> Dynamic 45-degree shot with slight handheld energy. A loaded smash
> burger patty pressed hard onto a screaming-hot flat-top griddle,
> butter foaming and sizzling aggressively around the edges, edges
> crisping and browning fast. A slice of American cheese draped over
> the top, beginning to melt at the corners. Bold, saturated colors,
> bright overhead light. Fast, energetic, high-appetite atmosphere.
> 4 seconds, 9:16.
> AUDIO: aggressive full sizzle as the patty hits — loud, satisfying.

**Restaurant ambience loop (website hero):**
> Wide-angle slow drift through a warm, candlelit Italian trattoria
> at the height of dinner service. Tables set with white linen, wine
> glasses catching the golden light, low Edison bulb pendants hanging
> above. The camera glides slowly between tables, guests slightly
> blurred in soft bokeh. The room hums with warmth and life.
> Cinematic, romantic, inviting atmosphere. Smooth, imperceptible
> camera movement. Perfectly seamless 12-second loop. 16:9.

**Seasonal dessert (event promotion):**
> Slow macro push-in. A blowtorch caramelizes the surface of a classic
> crème brûlée, sugar bubbling and crackling as it transforms from pale
> gold to deep amber. Tiny wisps of caramel smoke drift upward. Camera
> moves in gradually as the sugar sets and hardens to a glassy shell.
> Warm, intimate candlelit ambience, dark background. Indulgent,
> celebratory atmosphere. 6 seconds, 1:1.

---

## Sources

Prompting advice in this skill is based on widely applicable best practices
drawn from professional food videography guides, documentation published by
OpenAI (Sora), Google (Veo), Runway, Kling, Pika, Luma AI, and the broader
AI video generation and food content creation community. Always check the
official documentation for your specific model for the latest capabilities,
parameters, and maximum duration limits.
