# Intelligent Routing Algorithm

## Overview

The Intelligent Router is the **core decision engine** that determines which provider to use based on query analysis.

---

## How It Works

### Step 1: Keyword Extraction

Query is lowercased and searched for predefined keywords:

```python
query = "mars rover"
query_lower = "mars rover"

# Check against keyword sets
if "mars" in SPACE_KEYWORDS:  # ✓ Found!
    category = "space"
```

### Step 2: Category Detection

```python
def categorize_query(query: str) -> str:
    if any(kw in query_lower for kw in SPACE_KEYWORDS):
        return "space"
    elif any(kw in query_lower for kw in SCIENTIFIC_KEYWORDS):
        return "scientific"
    else:
        return "general"
```

### Step 3: Provider Priority Selection

Based on category, get provider order:

```python
def get_provider_priority(category: str) -> List[str]:
    if category == "space":
        return ["nasa", "wikimedia", "pexels"]
    elif category == "scientific":
        return ["wikimedia", "nasa", "pexels"]
    else:  # general
        return ["pexels", "wikimedia", "nasa"]
```

### Step 4: Routing Decision

```python
def route_query(query: str) -> Tuple[str, List[str]]:
    category = categorize_query(query)
    providers = get_provider_priority(category)
    primary = providers[0]
    fallbacks = providers[1:]
    return primary, fallbacks
```

---

## Query Categories

### SPACE Category

**Keywords:**
```
nasa, mars, moon, saturn, jupiter, galaxy, astronaut, rover, space,
spacecraft, satellite, orbit, cosmic, star, solar, sun, planet,
asteroid, comet, nebula, apollo, hubble, iss, esa, roscosmos
```

**Provider Priority:**
```
NASA (3) → Wikimedia (2) → Pexels (1)
```

**Example:**
```
Query: "mars rover"
Detected: mars, rover
Category: SPACE
Primary: NASA
Fallbacks: [wikimedia, pexels]
```

### SCIENTIFIC Category

**Keywords:**
```
cancer, cancer cell, microscope, biology, neuron, chemistry,
anatomy, bacteria, virus, dna, protein, research, medical,
science, laboratory, experiment, physics, medicine, disease
```

**Provider Priority:**
```
Wikimedia (3) → NASA (2) → Pexels (1)
```

**Example:**
```
Query: "cancer cell"
Detected: cancer, cell
Category: SCIENTIFIC
Primary: Wikimedia
Fallbacks: [nasa, pexels]
```

### GENERAL Category

**Keywords:**
```
nature, dog, cat, city, business, travel, wallpaper, people,
landscape, water, mountain, beach, forest, animal, bird,
flower, building, street, sky, sunset
```

**Provider Priority:**
```
Pexels (3) → Wikimedia (2) → NASA (1)
```

**Example:**
```
Query: "nature photography"
Detected: nature
Category: GENERAL
Primary: Pexels
Fallbacks: [wikimedia, nasa]
```

---

## Multi-Category Queries

### When Multiple Keywords Detected

Query is processed in **priority order**:

1. **Check SPACE keywords first** (highest priority)
2. **Check SCIENTIFIC keywords second**
3. **Default to GENERAL**

### Example 1: Mixed Query

```
Query: "cancer cell from space"
Detected: cancer cell (scientific), space (space)
Processing:
  - Check space keywords: "space" → MATCH
  - Category: SPACE
  - Primary: NASA
  - Fallbacks: [wikimedia, pexels]

Result: Prioritizes space content even though cancer is mentioned
```

### Example 2: Mixed Query 2

```
Query: "microscope comparison"
Detected: microscope (scientific)
Processing:
  - Check space keywords: none
  - Check scientific keywords: "microscope" → MATCH
  - Category: SCIENTIFIC
  - Primary: Wikimedia
  - Fallbacks: [nasa, pexels]

Result: Routes to Wikimedia for scientific content
```

---

## Provider Selection Logic

```
Input Query
    ↓
Normalize (lowercase)
    ↓
Extract Keywords
    ↓
Categorize (space/scientific/general)
    ↓
Get Provider Priority List
    ↓
Filter Enabled Providers
    ↓
Select Primary + Fallbacks
    ↓
Return (primary, [fallback1, fallback2, ...])
```

---

## Ranking System

After collecting results from all providers:

### Deduplication

Remove duplicate titles using MD5 hashing:

```python
title_hash = md5(result['title']).hexdigest()

if title_hash not in seen_hashes:
    deduplicated.append(result)
    seen_hashes.add(title_hash)
```

### Scoring

Each result gets a score based on:

1. **Provider Score:**
   - Primary provider (first): 3 points
   - Secondary provider (second): 2 points
   - Tertiary provider (third): 1 point

2. **Position Score:**
   - Earlier position: higher score
   - Formula: max(0, 10 - position)

3. **Total Score:**
   ```
   total_score = provider_score * 100 + position_score
   ```

### Ranking

Results sorted by total_score (descending):

```
NASA Result #1      → score: 300 + 10 = 310 ✓
NASA Result #2      → score: 300 + 9 = 309 ✓
Wikimedia Result #1 → score: 200 + 10 = 210
Wikimedia Result #2 → score: 200 + 9 = 209
Pexels Result #1    → score: 100 + 10 = 110
```

---

## Fallback Mechanism

If primary provider fails:

```
1. Try Primary (NASA)
   ├─ Success → Return results
   └─ Failure → Continue

2. Try First Fallback (Wikimedia)
   ├─ Success → Return results
   └─ Failure → Continue

3. Try Second Fallback (Pexels)
   ├─ Success → Return results
   └─ Failure → Return empty results
```

---

## Configuration

Keywords are configured in `config.py`:

```python
SPACE_KEYWORDS = [
    "nasa", "mars", "moon", ..., "roscosmos"
]

SCIENTIFIC_KEYWORDS = [
    "cancer", "cancer cell", ..., "disease"
]

GENERAL_KEYWORDS = [
    "nature", "dog", ..., "sunset"
]
```

To add keywords, edit `config.py` and restart the server.

---

## Performance

| Operation | Time |
|-----------|------|
| Query categorization | <1ms |
| Provider selection | <1ms |
| Keyword matching | <1ms |
| **Total routing decision** | **<5ms** |

---

**Intelligent, fast, and automatic! 🧠⚡**
