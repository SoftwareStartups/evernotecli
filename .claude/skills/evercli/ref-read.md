# Read Commands

Data commands output JSON by default. No `--json` flag needed. Pipe through `jq` to extract fields.

## Search

| Command | Args | Purpose |
|---------|------|---------|
| `search` | `[query]` | Search notes (optional query) |

Flags: `--notebook <name>`, `--tag <name>` (repeatable), `--max <number>` (default 20, max 100), `--offset <number>`

```bash
# Basic search
evercli search "meeting notes" | jq '.notes[] | {guid, title, updated}'

# Filter by notebook
evercli search "status" --notebook "Work" | jq '.notes[] | {guid, title}'

# Filter by tag(s)
evercli search "report" --tag "quarterly" --tag "finance" | jq '.notes[] | {guid, title}'

# Paginate results
evercli search "project" --max 10 --offset 20 | jq '{total, notes: [.notes[] | {guid, title}]}'

# Count results
evercli search "draft" | jq '.total'
```

## Notebooks

| Command | Args | Purpose |
|---------|------|---------|
| `notebooks` | | List all notebooks |

```bash
evercli notebooks | jq '.[] | {guid, name, stack}'

# Find a notebook GUID by name
evercli notebooks | jq -r '.[] | select(.name == "Work") | .guid'
```

## Note Metadata

| Command | Args | Purpose |
|---------|------|---------|
| `note` | `<guid>` | Show note metadata |

```bash
evercli note GUID | jq '{guid, title, tagNames, notebookGuid, created, updated, contentLength}'
```

## Note Content

| Command | Args | Purpose |
|---------|------|---------|
| `content` | `<guid>` | Show note body as markdown |

Flag: `--save-resources <directory>` — save embedded images/files to directory, rewrite refs to local paths

```bash
# Read note content (markdown output, not JSON)
evercli content GUID

# Save embedded images to a directory
evercli content GUID --save-resources ./attachments
```

## Tags

| Command | Args | Purpose |
|---------|------|---------|
| `tags` | | List all tags |

```bash
evercli tags | jq '.[] | {guid, name}'

# Find a tag GUID by name
evercli tags | jq -r '.[] | select(.name == "important") | .guid'
```
