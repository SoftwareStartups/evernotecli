# Write Commands

Write commands output JSON. Rate-limited operations are queued automatically — run `evercli drain` to process them.

## Auth

```bash
evercli login                            # Interactive OAuth flow
evercli login --token "YOUR_TOKEN"       # Non-interactive with token
evercli login --skip-validation          # Skip token validation
evercli logout
```

Env var `EVERNOTE_TOKEN` overrides stored credentials.

## Create

| Command | Args | Purpose |
|---------|------|---------|
| `create` | `<title>` | Create a new note |

Flags: `--content <markdown>`, `--notebook <name>`, `--tag <name>` (repeatable), `--source-note <guid>` (copy resources from existing note)

```bash
# Simple note
evercli create "Meeting Notes" | jq '{guid, title}'

# Note with content in a notebook with tags
evercli create "Weekly Status" --content "## Summary\n- On track" --notebook "Work" --tag "weekly" --tag "status" | jq '{guid, title}'

# Re-create a note preserving images from the original
evercli create "Updated Report" -c "New content" --source-note ORIGINAL_GUID | jq '{guid, title}'
```

## Tag / Untag

| Command | Args | Purpose |
|---------|------|---------|
| `tag` | `<guid> <tags...>` | Add tags to a note |
| `untag` | `<guid> <tags...>` | Remove tags from a note |

```bash
evercli tag GUID "important" "follow-up" | jq '{guid, title, tagNames}'
evercli untag GUID "draft" | jq '{guid, title, tagNames}'
```

Note: the `private` tag cannot be added or removed via CLI.

## Move

| Command | Args | Purpose |
|---------|------|---------|
| `move` | `<guid> <notebook>` | Move note to a notebook |

```bash
evercli move GUID "Archive" | jq '{guid, title, notebookGuid}'
```

## Copy

| Command | Args | Purpose |
|---------|------|---------|
| `copy` | `<source-guid> <title>` | Copy note with attachments |

Flag: `--notebook <name>` (default: same as source)

```bash
evercli copy SOURCE_GUID "Copy of Report" | jq '{guid, title}'
evercli copy SOURCE_GUID "Report Backup" --notebook "Backups" | jq '{guid, title}'
```

## Drain Queue

| Command | Args | Purpose |
|---------|------|---------|
| `drain` | | Process queued write operations |

```bash
# After rate-limit errors, replay queued operations
evercli drain
```
