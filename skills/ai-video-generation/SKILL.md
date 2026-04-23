---
name: video-prompt
description:  Generate optimized prompts for AI video generators. Use when the user invokes video-prompt or asks to create, write, craft, or generate a prompt for any AI video generator (e.g. Sora, Runway, Kling, Pika, Hailuo, Veo, Luma Dream Machine, Wan, or similar). Also triggers when the user says "video prompt","AI video prompt", "text-to-video prompt", or "help me describe a video clip".
---

# AI Video Prompt Generator

Generate high-quality, optimized prompts for AI video generators, based on
widely applicable prompting best practices.

---

## Choosing a Model

If the user hasn't specified a model, ask which one they're using so you can
tailor advice. Common options include:

| Model | Provider | Strengths |
|---|---|---|
| Sora | OpenAI | Long clips, strong physics, cinematic quality |
| Veo 2 / Veo 3 | Google (Gemini) | Photorealism, camera control, audio generation |
| Runway Gen-4 | Runway | Character/object consistency, fine-grained control |
| Kling 2.0 | Kuaishou | High motion quality, realistic movement |
| Hailuo (MiniMax) | MiniMax | Fast generation, smooth motion |
| Pika 2.2 | Pika Labs | Creative effects, scene transitions |
| Luma Dream Machine | Luma AI | Fluid motion, strong prompt adherence |
| Wan 2.1 | Alibaba | Open-source, strong multilingual support |
| Others | Various | Apply general principles below |

Different models have different strengths, but the core principles below work
across all of them. Note any model-specific tips in your output when relevant.

---

## Core Principles

Video generation is fundamentally different from image generation. In addition
to composition and lighting, you must direct **motion, time, and sound**.

### Golden Rules

1. **Describe motion explicitly** — Static descriptions produce stiff, jittery
   results. Name every movement with direction, speed, and feel.
   - BAD: `a woman at a window`
   - GOOD: `a woman slowly turns from a rain-streaked window toward camera,
     her expression shifting from melancholy to quiet resolve`

2. **One scene per prompt** — AI video models struggle with hard narrative cuts.
   Describe a single continuous shot or a smooth transition, not a multi-scene
   sequence.

3. **Lead with the shot type and camera move** — Establish the cinematic frame
   before describing content, so the model locks in the visual grammar first.
   - "Slow push-in on a..." / "Aerial drone shot tracking..." /
     "Handheld follow shot of..."

4. **Anchor motion to physics** — Describe how things interact with gravity,
   wind, water, and surfaces. This dramatically improves realism.
   - "her silk dress catches in the breeze," "water droplets bead and roll off
     the hood," "dust kicks up from his footsteps"

5. **Specify duration and pacing** — Short prompts for short clips (2–5 s),
   richer prompts for longer ones (up to ~60 s on supported models).
   - "A 5-second shot of..." sets clear scope for the model.

6. **Natural language over tag soup** — Write as if briefing a film director,
   not listing keywords.

---

## Workflow

### Step 1: Gather the User's Vision

Ask the user to describe what they want. If their description is vague, ask
targeted questions to fill in these dimensions:

| Dimension | What to ask | Examples |
|---|---|---|
| Subject | Who or what is the main focus? | Person, creature, object, abstract scene |
| Action / Motion | What is moving, and how? | Walking slowly, spinning, exploding, drifting |
| Setting / Environment | Where does this take place? | City street, underwater, forest, studio |
| Mood / Atmosphere | What feeling should it evoke? | Tense, dreamy, joyful, eerie |
| Visual Style | What look? | Cinematic, anime, stop-motion, documentary |
| Camera Movement | How does the camera move? | Static, slow push-in, orbit, handheld follow |
| Lighting | What lighting conditions? | Golden hour, neon-lit night, overcast day |
| Duration | How long is the clip? | 3 s, 5 s, 10 s, up to ~60 s |
| Aspect Ratio | What format? | 16:9 (landscape), 9:16 (portrait/vertical), 1:1 |
| Audio / Sound (if supported) | Any ambient sound or music? | Rain, crowd noise, orchestral swell |
| Purpose | Where will this be used? | Social media reel, ad, film pre-viz, presentation |

Do **not** ask all questions at once. Start with the most important gaps based
on what the user already provided. Ask 2–3 questions maximum per round.

---

### Step 2: Build the Prompt

Construct the prompt using this structure (not all elements are required — use
what's relevant):

```
[Shot type + camera movement], [specific subject with details] [action/motion]
in [setting/environment], [lighting description], [mood/atmosphere],
[visual style], [physics/environmental detail], [audio if relevant].
[Duration and aspect ratio if helpful.]
```

**Key techniques to apply:**

**Shot & Camera Language:**
- Shot types: "extreme close-up," "medium shot," "wide establishing shot,"
  "aerial bird's-eye," "low-angle hero shot"
- Camera moves: "slow push-in," "pull back to reveal," "orbit around subject,"
  "handheld follow," "static locked-off," "whip pan," "crane rising shot,"
  "dolly zoom (Vertigo effect)"

**Motion Language:**
- Character motion: "strides purposefully," "stumbles and catches herself,"
  "slowly raises her head," "fingers flutter across piano keys"
- Object motion: "leaves spiral downward," "smoke curls upward and disperses,"
  "waves crash and recede," "shards of glass hang suspended mid-air"
- Camera + subject sync: "camera tracks alongside as he runs," "subject walks
  toward camera while background blurs into bokeh"

**Lighting Specifics:**
- "golden-hour backlight with long shadows," "cold blue moonlight through
  venetian blinds," "flickering candlelight casting warm pools," "neon signs
  reflecting in wet pavement," "overcast diffused light, no harsh shadows"

**Time and Atmosphere:**
- "early morning fog rolling across the valley," "slow-motion at 120fps,"
  "time-lapse of clouds racing overhead," "magic hour — sun just below horizon"

**Physics and Texture Anchors:**
- "her hair lifts in the gust," "raindrops distort the neon reflections,"
  "sand cascades off his boots," "breath visible in freezing air"

**Audio (for models supporting audio generation like Veo 3):**
- "ambient: distant thunder, rain on glass, low cello drone"
- "sound design: footsteps on gravel, creaking door, wind through trees"
- Keep audio descriptions separate from visual descriptions for clarity

**Model-specific tips (mention when relevant):**
- *Sora:* Handles long clips (up to 60 s) well; strong with complex physics;
  use `[SCENE]` breaks only for transitions, not hard cuts
- *Veo 3:* Supports native audio generation — add a separate `[AUDIO]` section;
  strong camera control vocabulary
- *Runway Gen-4:* Excellent character consistency across shots; supports
  reference images for locking subject appearance
- *Kling:* Responds well to explicit motion intensity descriptors ("slow,"
  "fluid," "explosive"); strong at human movement
- *Pika:* Great for stylized effects and scene-to-scene transitions; use
  "transition: [type]" syntax for morphs
- *Luma Dream Machine:* Strong prompt adherence; benefits from explicit
  "looping" instruction for seamless loops
- *Wan 2.1:* Open-source; works well with detailed scene descriptions;
  supports image-to-video with reference uploads

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

TIPS FOR THIS CLIP:
- [Any model-specific parameters, duration advice, or iteration suggestions]
```

---

### Step 4: Offer Refinement

After presenting the prompt, ask the user:

> "Would you like to adjust anything? I can refine the motion, camera work,
> lighting, atmosphere, or pacing. I can also create a variant prompt for a
> different shot angle or visual style."

Continue iterating until the user is satisfied.

---

## Special Capabilities to Leverage

Mention these to the user when relevant:

### Image-to-Video
Most models accept a reference image as the first frame and animate outward
from it. Tips:
- "Use the uploaded image as the first frame; animate by slowly pulling back
  to reveal the full scene"
- "Start from this still photo and add falling snow, breath vapor, and subtle
  camera drift"

### Character and Object Consistency
Models like Runway Gen-4 support reference images for locking appearance:
- "Keep this character's face and outfit consistent across all shots"
- "The red vintage car must look identical in every scene"

### Seamless Loops
For social media or background video:
- "Create a perfectly seamless 4-second loop — ending frame must match the
  opening frame"
- "Looping cinemagraph style: only the [element] moves, everything else is
  frozen"

### Slow Motion and Speed Ramps
- "Shoot at 120fps slow-motion as the [subject] [action]"
- "Speed ramp: start at normal speed, crash to ultra-slow-mo at the moment of
  impact, then ramp back up"

### Style Transfer and Cinematic References
- "Lit and color-graded in the style of a 1970s Italian crime film — desaturated
  tones, warm shadows, heavy film grain"
- "Visual style of a Studio Ghibli hand-painted background — watercolor
  textures, soft edges, lush greens"

### Audio Generation (Veo 3 and select others)
- Describe ambient sound, music mood, and sound design in a separate section
- "AUDIO: thunderstorm ambience, distant thunder rolling, rain intensifying,
  low ominous drone"

---

## Anti-Patterns to Avoid

| Anti-pattern | Fix |
|---|---|
| Static image description | Add explicit motion for every key element |
| Multiple scenes in one prompt | Break into separate prompts, one per shot |
| Vague movement ("it moves") | Name direction, speed, and physical quality |
| Ignoring camera | Always specify shot type and camera movement |
| Missing physics anchors | Add at least one environmental interaction |
| Over-long prompts for short clips | Match prompt complexity to clip duration |
| Contradictory instructions | Remove conflicting direction/style cues |

---

## Example Prompts

**Cinematic character moment:**
> Slow push-in on a weathered detective sitting at a dimly lit diner booth,
> 3 AM, rain streaking the window behind him. He stubs out a cigarette and
> stares into a cold cup of coffee, jaw tightening slightly. Steam curls from
> the cup. Neon signs outside pulse red and blue through the glass.
> Handheld, slight camera drift. Film noir aesthetic, heavy grain, cold blue
> shadows. 6-second clip, 16:9.

**Nature / landscape:**
> Aerial drone shot slowly descending through a gap in a dense Japanese bamboo
> forest at dawn. Shafts of pale gold light pierce the canopy, illuminating
> drifting mist near the ground. Bamboo stalks sway gently in a soft breeze,
> leaves rustling. Silent, meditative atmosphere. Smooth, ultra-stable camera
> movement. Photorealistic, shallow depth of field. 8 seconds, 16:9.

**Product commercial:**
> Extreme close-up, low angle, looking up at a sleek black espresso machine on
> a marble countertop. A rich, dark espresso shot pulls slowly into a white
> ceramic cup — crema blooming and swirling on the surface. Soft directional
> light from the left, warm highlights on the chrome. Steam rises gently. Camera
> holds static. Premium, aspirational feel. 5 seconds, 1:1.

**Action / dynamic:**
> Tracking shot running alongside a lone cyclist sprinting down a rain-slicked
> city street at night, neon reflections streaking across wet asphalt. Camera
> stays level with the rear wheel, close. The rider leans hard into a corner,
> spray flying from the tires. Motion blur on background lights. Urgent,
> adrenaline-charged atmosphere. 4 seconds, 16:9.

**Seamless loop / ambient:**
> A crackling fireplace in a dark, cozy living room. Flames dance and shift
> naturally, logs glow ember-orange, occasional sparks rise and fade. Warm
> amber light pulses softly on surrounding stone. Static, locked-off shot.
> Perfectly seamless 6-second loop. Photorealistic, ultra-detailed.

**Stylized / animated:**
> Studio Ghibli-style animation: a young girl with a wide-brimmed hat stands
> at the edge of a cliff overlooking a vast ocean, wind whipping her dress and
> hair. Seagulls wheel in the distance. She raises her arms slowly as if about
> to fly. Painted watercolor background, soft pastel sky, late afternoon light.
> Gentle, sweeping crane shot rising behind her. 7 seconds, 16:9.

---

## Sources

Prompting advice in this skill is based on widely applicable best practices
drawn from documentation, creator guides, and community knowledge published by
OpenAI (Sora), Google (Veo), Runway, Kling, Pika, Luma AI, and the broader
AI video generation community. Always check the official documentation for your
specific model for the latest capabilities, parameters, and duration limits.