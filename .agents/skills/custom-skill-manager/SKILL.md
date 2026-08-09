---
name: custom-skill-manager
description: Manage and execute user-defined custom skills in VedaApex backend and workspace. Use when user wants to add, list, remove, or execute custom skills or trigger-based behavior rules.
---

# Custom Skill Manager

This skill allows the agent to create, list, manage, and execute custom skills for users.

## Trigger Patterns
- "custom skill add karo"
- "[naam] skill add karo"
- "ye skill add karo - [description]"
- "skills dikhao" / "meri skills batao"
- "[naam] skill hatao"

## Capabilities & Usage
1. **Adding a Skill (`POST /api/v1/skills`)**:
   - Save name, description, trigger_keywords, and system prompt instructions into the database.
   - Confirm with: `✅ Skill '[naam]' add ho gaya. Ab jab bhi [naam] se related kaam bologe, main isi tarah se karunga.`

2. **Listing Skills (`GET /api/v1/skills`)**:
   - List all active user skills with name and description.

3. **Deleting a Skill (`DELETE /api/v1/skills/{id}`)**:
   - Delete skill by ID or slug name and confirm deletion.

4. **Prompt Matching & Execution (`POST /api/v1/skills/execute`)**:
   - Automatically match user message against active skills' `trigger_keywords`.
   - Augment system prompt with matched skills' instructions before calling LLM.
