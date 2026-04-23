---
name: ai-image-generation
description: Instructions for rewriting and refining image generation prompts.
---

# ai-image-generation

When generating image prompts for Chefbook users:

1. **Context First**: Always pull the user's recent feedback (using the `postgres-reader` skill) and inspect their recently generated images (using `s3-reader`) to ensure the new prompt aligns with their established preferences. Avoid motifs, colors, or compositional styles they have previously rated poorly or consistently ignored.
2. **Subject & Composition**: Clearly define the main subject, framing, and angle.
   - For food: Use concrete plating descriptors (e.g., "minimalist white ceramic dish," "delicate herb garnish," "warm natural window lighting"). Avoid generic terms like "delicious."
   - For interior: Describe ambiance via lighting and decor (e.g., "warm golden ambient lighting," "modern rustic interior," "soft focus background").
3. **Format**: The final prompt must be a single, concise block of descriptive text. Style, mood, lighting, and color palette should be explicitly named.
4. **No Meta-Commentary**: The output should be the raw prompt ready for the image generation model. No intros, no pleasantries, no explanations.

**Reference Image & Mask Handling**: When reference images are provided:
- Explicitly tie requested elements to these references (e.g., "Matching the plating style of: [Ref Image URL]").
- If a mask is provided, include clear instructions for preserving unmasked regions.
