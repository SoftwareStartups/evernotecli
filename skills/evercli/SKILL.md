---
name: evercli
description: Evernote note management via CLI. Activate when user mentions "Evernote", "notes", "notebooks", or wants to search, read, create, tag, or organize notes. Examples: "Search my Evernote notes", "Create a note", "Tag this note", "List notebooks".
---

# Evercli

## Rules

1. Only activate when "Evernote" or note management is mentioned
2. Pipe output through `jq` to keep context small — data commands output JSON by default (no `--json` flag needed)
3. Use `content` command for note body — it outputs markdown, not JSON
4. Resolve GUIDs progressively: search → note → content
5. If a write command is rate-limited, run `evercli drain` to process queued operations

## Output

Data commands output raw JSON (no envelope). Example shapes:

```bash
# Search returns {notes: [...], total, offset, maxResults}
evercli search "query" | jq '.notes[] | {guid, title}'

# Notebooks/tags return arrays
evercli notebooks | jq '.[] | {guid, name}'

# Content outputs markdown directly (not JSON)
evercli content GUID
```

## Primary Workflow: Find and Read a Note

```bash
# 1. Search for notes
evercli search "meeting notes" | jq '.notes[] | {guid, title, updated}'

# 2. Get note metadata
evercli note GUID | jq '{guid, title, tagNames, updated}'

# 3. Read note content (markdown)
evercli content GUID
```

## Common Patterns

```bash
# Search in a specific notebook with tags
evercli search "status" --notebook "Work" --tag "weekly" | jq '.notes[] | {guid, title}'

# List all notebooks
evercli notebooks | jq '.[] | {guid, name, stack}'

# List all tags
evercli tags | jq '.[] | {guid, name}'

# Create a note in a notebook with tags
evercli create "Meeting Notes" --content "## Agenda\n- Item 1" --notebook "Work" --tag "meeting"

# Tag / untag a note
evercli tag GUID "important" "follow-up"
evercli untag GUID "draft"

# Move a note to another notebook
evercli move GUID "Archive"

# Copy a note (preserves attachments)
evercli copy SOURCE_GUID "Copy of Note" --notebook "Drafts"

# Process queued writes after rate limiting
evercli drain
```

Error: private notes are filtered from results and cannot be accessed.

## References

- **Read commands + jq:** [ref-read.md](ref-read.md)
- **Write commands:** [ref-write.md](ref-write.md)
- **Full help:** `evercli --help`
