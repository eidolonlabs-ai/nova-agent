---
name: example-skill
category: general
description: Example skill demonstrating slash command support
---

# Example Skill

This is an example skill that demonstrates the new slash command feature in Nova Agent.

## Features

You can now load skills directly using slash commands:
- Type `/example-skill` to load this skill
- Type `/skills` to list all available skills
- Tab completion is supported for all skill names

## How to Use

1. Create a skill directory in `~/.nova/skills/your-skill-name/`
2. Add a `SKILL.md` file with YAML frontmatter
3. Load it anytime with `/your-skill-name`

## Benefits

- Quick access to project-specific knowledge
- No need to manually call `skill_view` tool
- Natural command-line workflow
- Full autocomplete support
