---
name: file-editing
category: development
description: Safe file editing patterns — read before write, patch with context, verify after
---

# File Editing Skill

## The Golden Rule

**Always read before you write.** Never assume file contents. Always verify after editing.

## Workflow

1. **Read** — `read_file(path)` to understand current content and exact whitespace
2. **Plan** — identify the exact text to replace (patch) or the full new content (write)
3. **Edit** — `patch_file` for targeted changes, `write_file` for new files or full rewrites
4. **Verify** — `read_file(path)` again to confirm the edit applied correctly

## Tool Selection Guide

| Situation | Tool |
|-----------|------|
| Understand current content | `read_file` |
| Fix a bug, add/remove a line, rename a variable | `patch_file` |
| Create a new file | `write_file` |
| Completely rewrite a file | `write_file` |
| Find where something is used across the project | `search_files` |
| Find the exact text to use in `old_string` | `read_file` with `offset`/`limit` |

## patch_file Tips

- Include **3–5 lines of context** before and after the target in `old_string` — enough to be unique
- Copy `old_string` **exactly** from the file — whitespace, indentation, and blank lines must match
- If the patch fails with "not found", re-read the file — it may have changed or your string has a typo
- `patch_file` replaces only the **first** occurrence — if the string appears multiple times, add more context
- After patching, always verify with `read_file` around the changed lines

## read_file Tips

- Use `offset` and `limit` to read large files in sections: `read_file(path, offset=50, limit=30)`
- The response includes `Lines X-Y of Z` — use this to navigate large files
- For very large files, use `search_files` first to find the relevant line numbers

## write_file Tips

- `write_file` **overwrites everything** — include the complete file content
- For large files, prefer `patch_file` to avoid accidentally dropping content
- Always read the file first if it already exists, so you don't lose existing content

## Pitfalls

- Never guess file contents — always read first
- Don't patch without verifying the result afterward
- Don't use `write_file` on an existing file without reading it first
- When adding code that uses new imports, update the import section too
- Whitespace matters — a single extra space in `old_string` will cause the patch to fail
- Don't assume line endings — read the file to see what's actually there
