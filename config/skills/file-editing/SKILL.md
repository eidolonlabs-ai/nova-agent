---
name: file-editing
category: development
description: Safe file editing patterns — read before write, verify after patch
---

# File Editing Skill

## Workflow

1. **Read first** — Always read the file before editing to understand current content
2. **Plan the edit** — Identify the exact text to replace (for patch) or the full content (for write)
3. **Apply the edit** — Use `patch_file` for small changes, `write_file` for full rewrites
4. **Verify** — Read the file back to confirm the edit worked correctly

## When to Use Which Tool

- **`read_file`**: Always use first to understand current state
- **`patch_file`**: For targeted changes (fix a bug, add a line, rename a variable). Requires exact match of the old text.
- **`write_file`**: For creating new files or completely rewriting existing ones. Overwrites all content.
- **`search_files`**: For finding where something is used across the project

## Patch File Tips

- Include enough context in `old_string` to uniquely identify the target (3-5 lines before/after)
- Preserve exact whitespace and indentation
- If patch fails, read the file again — it may have changed

## Pitfalls

- Never guess file contents — always read first
- Don't patch without verifying the result
- Be careful with `write_file` — it overwrites everything
- When editing code, ensure imports are updated if adding new dependencies
