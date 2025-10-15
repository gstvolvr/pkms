# Personal Knowledge Management System (PKMS)

A unified CLI tool for managing your [Obsidian](http://obsidian.md/) vault, with support for metadata management, entity linking, photo integration, and AI-powered search.

## Features

- 📝 **Metadata Management** - Automatically enrich daily notes with people, locations, and dates from photos
- 🔗 **Entity Linking** - Auto-link people and places using aliases
- 📷 **Photo Integration** - Sync photo metadata and embed photos in notes
- 🔍 **RAG Search** - Query your vault using local Ollama LLMs
- 📊 **Analytics** - Visualize vault statistics and relationships

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd pkms

# Install in development mode
pip install -e .
```

## Prerequisites

For RAG search functionality:

1. Install Ollama from [ollama.ai](https://ollama.ai/)
2. Pull the required models:
   ```bash
   ollama pull nomic-embed-text  # For embeddings
   ollama pull llama3            # For text generation
   ```

## Configuration

By default, PKMS looks for your vault at `~/obsidian/vida` and photos at `~/photos`. Override with:

```bash
export PKMS_VAULT_PATH=/path/to/your/vault
export PKMS_PHOTOS_PATH=/path/to/your/photos
```

Or use command-line flags:
```bash
pkms --vault /path/to/vault --photos /path/to/photos <command>
```

## Usage

### Metadata Commands

```bash
# Initialize frontmatter for notes
pkms metadata init

# Enrich metadata from photos (interactive)
pkms metadata enrich

# Auto-approve people from approved list
pkms metadata enrich --auto-approve

# Count pending metadata items
pkms metadata count

# Review and standardize metadata
pkms metadata review --interactive

# Find outlier people in notes
pkms metadata outliers --interactive
```

### Default People/Locations (NEW!)

Automatically populate people/locations based on cohabitation and residence dates:

```bash
# Check current statistics
pkms defaults stats

# Show what defaults would apply for a date
pkms defaults show 2024-10-15

# Preview changes (dry run)
pkms defaults apply --dry-run

# Apply defaults to all notes
pkms defaults apply

# Only apply people (not locations)
pkms defaults apply --no-locations

# Only apply locations (not people)
pkms defaults apply --no-people
```

**Setup:** Add to person/location files:
```yaml
# people/family/Spouse.md
---
cohabitated_start: "2020-06-15"
cohabitated_end: "2023-08-30"  # Optional, omit if still cohabitating
---

# locations/City.md
---
lived_start: "2018-01-01"
lived_end: "2022-12-31"  # Optional, omit if still living there
---
```

See [RESIDENCE_DEFAULTS.md](RESIDENCE_DEFAULTS.md) for complete documentation.

### Link Management

```bash
# Add entity links interactively
pkms links add

# Count pending link candidates
pkms links count
```

### Photo Management

```bash
# Add photo grids to notes
pkms photos add

# Sync photo metadata to notes
pkms photos sync

# Create notes from photo metadata
pkms photos sync --create-notes
```

### Search (RAG)

```bash
# Index your vault
pkms search index

# Query your vault
pkms search query "What are my notes about machine learning?"

# Interactive query mode
pkms search query --interactive

# Use different model
pkms search query --model mistral "your question"
```

### Analytics

```bash
# Show vault statistics
pkms stats

# Show detailed statistics
pkms stats --detailed
```

### Visualizations

```bash
# Show timeline chart for a person (by month)
pkms viz person "Courtney"

# Group by year
pkms viz person "Courtney" --group-by year

# Group by quarter
pkms viz person "Ruby" --group-by quarter

# Adjust chart width
pkms viz person "Roberto" --width 80
```

### File Management

```bash
# Generate date files from photos
pkms files generate-dates

# Remove empty date files
pkms files cleanup
```

## Examples

**Enrich all notes with photo metadata:**
```bash
pkms metadata init
pkms photos sync --create-notes
pkms metadata enrich --auto-approve
```

**Add entity links across your vault:**
```bash
pkms links add
```

**Set up RAG search:**
```bash
pkms search index
pkms search query --interactive
```

**View vault statistics:**
```bash
pkms stats --detailed
```

## Legacy Scripts

The original scripts in `bin/` are still available but deprecated. Use the new CLI commands instead.
