---
name: social-media-product-launch-strategy
category: social-media
description: Develop a social media content strategy for a new product launch, leveraging past performance and submitting scheduled posts.
---

## Overview

This skill outlines a systematic approach to developing and submitting a social media content strategy for a new product launch. It includes steps for querying historical data for insights, generating creative content prompts (images, videos, stories), and scheduling them for submission.

## Steps

1.  **Understand Platform and User Context**: Review the product details (e.g., "new pasta launch next week") and identify a unique user ID (`user_id`) from the current session.

2.  **Explore Database for Performance Insights (Optional but Recommended)**:
    *   **List schemas**: Use `pg_schemas()` to identify available database schemas.
    *   **List tables**: Use `pg_tables(schema='chefbook')` (or relevant schema identified above) to see available tables.
    *   **Describe `media_performance_history`**: Use `pg_describe(schema='chefbook', table='media_performance_history')` to understand columns related to follower counts, likes, comments, and shares.
    *   **Calculate Engagement Rate**: Query `media_performance_history` to calculate engagement rates if an `engagement_rate` column doesn't exist directly.
        ```sql
        SELECT
            *,
            (total_likes + total_comments + COALESCE(total_shares, 0))::float / followers AS engagement_rate
        FROM chefbook.media_performance_history
        WHERE user_id = '<USER_ID>' AND followers > 0
        ORDER BY engagement_rate DESC
        LIMIT 5
        ```
        *Pitfall*: Be aware of potential division by zero if `followers` is 0.
    *   **Explore `content` history**: Use `pg_describe` and `pg_query` on the `content` table to identify past successful posts, captions, image links, and feedback.
        ```sql
        SELECT image_link, caption, is_liked, feedback, feedback_tags
        FROM chefbook.content
        WHERE user_id = '<USER_ID>'
        ORDER BY created_at DESC
        LIMIT 10
        ```
    *   *Decision Point*: If historical data yields strong insights, use them to inform content creation. If not, proceed with general best practices.

3.  **Generate Content Strategy**:
    *   **Timing**: Plan the content leading up to and on the launch day. For "next week," aim for pre-launch buzz, launch announcement, and post-launch follow-up.
    *   **Content Types**: Plan for a mix of content types (IMAGE, VIDEO, STORY) to maximize engagement across different social media formats.
    *   **Prompts**: Create detailed, engaging prompts for each content piece, considering visual style, emotional appeal, and call to action.
        *   **Image**: High-quality, appetizing visual.
        *   **Video**: Dynamic, showing preparation or enjoyment.
        *   **Story**: Direct announcement with a clear call to action.
    *   **Calls to Action (CTAs)**: Include specific CTAs (e.g., "Tag a friend," "Try it now," "Link in bio").
    *   **Hashtags**: Use relevant and trending hashtags.

4.  **Submit Strategy**:
    *   Use the `submit_strategy` tool with the generated content items.
    *   Ensure each item has `type`, `scheduled_at` (ISO 8601 UTC), and `prompt`.
    *   Provide a `rationale` for each item.
    *   Crucially, pass the `session_id` from the system prompt exactly.

## Example of a Content Item for `submit_strategy`

```json
{
    "type": "IMAGE",
    "scheduled_at": "2026-04-27T10:00:00Z",
    "prompt": "A close-up, top-down shot of a beautifully plated, rustic-style pasta dish. The pasta should be vibrant, possibly a new shape or color, with fresh ingredients like basil, cherry tomatoes, and a light dusting of parmesan. Soft, natural lighting from the side, a shallow depth of field to highlight the pasta, on a dark, textured wooden table with a slightly blurred linen napkin in the background. Warm, inviting color palette with greens, reds, and creamy pasta tones.",
    "rationale": "Build anticipation for the new pasta with an appealing visual."
}
```

## Pitfalls

*   **Incorrect `user_id`**: Always use the correct `user_id` for database queries.
*   **Missing database columns**: Verify column names with `pg_describe` before querying.
*   **No historical data**: Be prepared to generate strategy based on general best practices if user-specific historical performance data is limited or unavailable.
*   **Incorrect `scheduled_at` format**: Ensure `scheduled_at` is in ISO 8601 UTC format.
*   **Forgetting `session_id`**: The `submit_strategy` tool *requires* the `session_id`.
