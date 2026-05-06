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

## Workflow

| Need | Command | When |
|------|---------|------|
| Find notes | `search "query"` | Free-text search, optionally filter by notebook/tag |
| Browse notebooks | `notebooks` | See all available notebooks |
| Browse tags | `tags` | See all available tags |
| Read note metadata | `note <guid>` | Need title, notebook, tags, dates for a note |
| Read note content | `content <guid>` | Need full note body as markdown |
| Create a note | `create "title" --content "markdown"` | New note, optionally in a notebook with tags |
| Tag/untag a note | `tag <guid> tag1 tag2` | Add or remove tags |
| Move a note | `move <guid> "Notebook"` | Reorganize into a different notebook |
| Copy a note | `copy <guid> "New Title"` | Duplicate a note including all attachments |
| Retry failed writes | `drain` | After rate-limited write operations |

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

For bulk results, write to `.evernote/` (gitignored) and read selectively rather than streaming everything through context:

```bash
mkdir -p .evernote

# Search — extract key fields only
evercli search "project notes" | jq '[.notes[] | {guid, title, notebook, updated}]' > .evernote/search-results.json

# Note content — write to disk, read selectively
evercli content GUID > .evernote/note-content.md
```

Never read entire note content files into context. Use offset/limit reads on disk files for long notes.

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

## Rate Limiting

Write commands (`create`, `tag`, `untag`, `move`) automatically enqueue when rate-limited and exit successfully (code 0). Run `evercli drain` to retry queued operations. If some still fail, run `drain` again later.

## Image Round-trip

To edit a note that has embedded images:

- **Server-side copy** (no local roundtrip): `evercli copy <guid> "New Title"` duplicates the note and all attachments.
- **Local edit**: extract markdown + resources, edit, re-create with original attachments preserved:

```bash
# 1. Extract markdown and save embedded images
evercli content GUID --save-resources ./res/ > note.md

# 2. Edit note.md locally...

# 3. Re-create with original resources reattached
evercli create "Updated Title" --content "$(cat note.md)" --source-note GUID
```

`--source-note` copies attachments from the existing note onto the new note.

## References

- **Read commands + jq:** [ref-read.md](ref-read.md)
- **Write commands:** [ref-write.md](ref-write.md)
- **Full help:** `evercli --help`
