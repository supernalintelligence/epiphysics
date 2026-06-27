# Prediction Framework: Entity Identification, Hierarchy, and Coupling

## The Prediction Problem

Given current state X and coupling structure Γ, predict next state X' and next coupling structure Γ':

```
(X, Γ) → (X', Γ')
```

Both states AND couplings evolve. A trade war doesn't just change US-China state — it changes the coupling structure itself (new tariffs create new couplings, old trade channels decouple).

## Entity Taxonomy

Every prediction question involves entities at multiple levels. Failing to identify the right level causes systematic errors.

### Level 1: Visible Entities
Named actors explicitly in the question. Easy to extract.
- "Detroit Pistons", "Donald Trump", "Gibraltar"

### Level 2: Container Entities
Define the rules, constraints, and competitive structure. The visible entity operates WITHIN these.
- Pistons ⊂ NBA Central Division ⊂ NBA ⊂ US professional sports
- Trump ⊂ US Government ⊂ US-Russia relations ⊂ Global nuclear order
- Gibraltar ⊂ UK Overseas Territories ⊂ Mediterranean security

Container entities matter because they determine:
- What coupling types exist (zero-sum within a division, cooperative within an alliance)
- What constraints apply (salary caps, treaty terms, geographic limits)
- What the base rate looks like (how often does a bottom team win a division?)

### Level 3: Hidden/Latent Entities
Drive outcomes but aren't named in the question. The hardest to identify and the most predictive.
- **Base rates**: What fraction of teams with Pistons' current record win their division? This is a HIDDEN ENTITY with high coupling to the outcome.
- **Momentum/form**: Recent trajectory (last 10 games, last quarter's economic data)
- **Structural factors**: Injury reports, coaching changes, election cycles, reporting methodology changes
- **Question mechanics**: "10x of near-zero = any nonzero" is a HIDDEN COUPLING between the baseline count entity and the threshold entity

### Level 4: Intersecting/Overlapping Entities
Entities that participate in multiple containers simultaneously.
- Trump is in {US Government} AND {US-Russia relations} AND {Republican Party} AND {Global trade system}
- A company is in {S&P 500} AND {its sector} AND {its supply chain} AND {its regulatory jurisdiction}
- Cross-container couplings are the most valuable for prediction (politics affecting markets, climate affecting agriculture)

## Coupling Types

### Direct Coupling (A → B)
Observable influence. Trump announces tariff → market drops.
- Strength: measurable from historical response magnitude
- Asymmetry: typically high (presidents affect markets more than markets affect presidents)

### Hierarchical/Containment (A ⊂ B)
Entity inherits properties and constraints from container.
- Pistons inherit NBA rules, salary cap, schedule structure
- Gibraltar inherits UK security umbrella, low baseline conflict rate
- Key insight: container properties are often MORE predictive than entity-specific properties

### Competitive/Zero-Sum (A ↔ B within C)
Within a container, entities compete for finite outcomes.
- NBA division: exactly one winner. Other teams' strength REDUCES your probability.
- Election: exactly one winner. Other candidates' polling DIRECTLY couples.
- Market share: growth of one reduces others within the sector.

### Temporal/Autoregressive (X(t) → X(t+1))
Past state predicts future state. This is the base rate / momentum signal.
- Current W-L record → division winner probability
- Current polling → election outcome
- Historical event counts → future event probability
- This coupling type is what LLMs are WORST at without explicit data

### Structural/Rule-Based (hidden)
Question mechanics, definitional thresholds, resolution criteria.
- "10x baseline" threshold: if baseline is 0, ANY occurrence resolves YES
- "By end of 2026" deadline: probability increases as deadline approaches without resolution
- "According to Wikipedia" source: resolution depends on Wikipedia editorial process, not ground truth

## The Temporal Data Problem

LLMs are trained on text, not time series. They can reason about entities mentioned in language but cannot:
- Track a running event count over 30-day windows
- Compute a W-L record from game-by-game results  
- Estimate base rates from historical frequency data
- Detect momentum shifts from sequential observations

The temporal signal must come from the DATA we provide, not the model's training. This means:

1. **For sports questions**: We need current standings, recent results, historical base rates
2. **For ACLED questions**: We need actual event counts in the baseline and current periods
3. **For economic questions (FRED, dbnomics)**: We need the actual time series values
4. **For market questions (yfinance)**: We need current prices and recent trends

Without this data, the LLM is guessing from question phrasing. The 60-70% accuracy we see is mostly "unlikely things sound unlikely in text."

## What the Entity Registry Should Actually Contain

### Per Entity
```
{
  id, canonical_name, aliases, type, domain,
  
  # Hierarchy
  containers: ["nba_central", "nba", "us_sports"],  # what this entity is inside
  contains: ["player_1", "player_2", ...],            # what this entity contains
  competes_with: ["bucks", "cavaliers", ...],         # zero-sum peers in same container
  
  # State (the temporal signal we must provide)
  state: {
    current_value: 0.35,          # quantitative state if available (win %, poll %, price)
    trajectory: "improving",       # qualitative direction
    base_rate: 0.12,              # historical frequency of the outcome type
    recent_data: [...],           # last N observations (game results, event counts, prices)
    summary: "text description",
  },
  
  # Hidden factors
  hidden_factors: [
    {"name": "injury_report", "impact": "negative", "detail": "star player out 2 weeks"},
    {"name": "schedule_difficulty", "impact": "favorable", "detail": "5 of next 8 home games"},
  ],
}
```

### Per Coupling
```
{
  source, target,
  type: "direct|hierarchical|competitive|temporal|structural",
  strength, asymmetry,
  
  # For competitive couplings: the container and the constraint
  container: "nba_central",
  constraint: "exactly_one_winner",
  
  # For structural couplings: the rule
  rule: "10x_threshold_with_zero_baseline",
}
```

## Practical Approach Given Constraints

We can't train temporal models. We CAN:

1. **Question-guided entity identification**: Parse the question to identify visible entities, then infer containers and competitive peers.

2. **Question-type classification**: Classify each question (sports/politics/conflict/economic/meta) and apply type-specific extraction logic:
   - Sports → need standings, W-L, base rates for this type of outcome
   - ACLED → need baseline event counts, threshold mechanics
   - Economic → need current indicator values, recent trend
   - Political → need polling, institutional dynamics

3. **Hidden entity surfacing**: For each question type, prompt the LLM to identify what HIDDEN factors matter most, given the visible and container entities.

4. **Base rate injection**: For question types where we can estimate base rates (how often does a 15-win team win its division? how often does 10x violence spike occur in stable countries?), inject this as a HIDDEN ENTITY with high coupling to the outcome.

5. **News as state update, not context**: Instead of dumping raw news articles into the prompt, use news to UPDATE entity state values (standings changed, new event occurred, poll shifted), then inject the updated state.

## Temporal Integrity: No Future Information Leakage

The knowledge graph must be built ONLY from information available before the prediction time. This is the most critical constraint.

### The Leakage Modes

1. **Cross-question leakage**: Analyzing question 50 adds entities to the KG that inform prediction of question 1. The SELECTION of which questions exist is itself information (being asked about implies relevance).

2. **LLM knowledge leakage**: The LLM's training data contains information up to ~early 2025. For questions about events in 2026, this is ~1 year stale — acceptable for base rate estimation, but not for current state.

3. **Future tranche leakage**: In multi-tranche prediction, information from future tranches must not inform earlier predictions. Entity state at time T must derive from data before T.

4. **Wikidata leakage**: Wikidata is live (current state). Hierarchy (Pistons ⊂ NBA) is timeless and safe. Current rosters, standings, or recent events would leak.

### The Correct Architecture

**Separate WHAT you build from WHAT you look up.**

```
TEMPORAL WALL
─────────────────────────────────────────────
BEFORE PREDICTION (KG construction — news-driven):

  For each time tranche T:
    1. Retrieve news articles from [T-14d, T]
    2. Extract entities + states + couplings from news ONLY
    3. Add to KG (entities accumulate over tranches)
    4. Update entity states from temporal data (standings, prices, counts)
    
  The KG at time T contains only information available at time T.
  Wikidata provides HIERARCHY ONLY (timeless containment facts).

─────────────────────────────────────────────
AT PREDICTION TIME (question-guided lookup):

  For each question at time T:
    1. Parse question → identify visible entity names
    2. LOOK UP those entities in the KG (don't add new ones)
    3. Surface hidden entities via LLM reasoning about the question
       (base rates, structural rules — these use the LLM's prior
        knowledge, which is ~1yr stale and acknowledged as such)
    4. Predict using: KG state at T + hidden entities + base rates
    
  The question guides what you LOOK AT, not what you BUILD.
```

### What the LLM is allowed to contribute

The LLM's training knowledge is a PRIOR — it knows base rates, structural rules, and historical patterns. This is analogous to a human forecaster's background knowledge. It's acceptable to use this prior AS LONG AS:

- It's acknowledged as stale (training cutoff noted)
- It's updated by temporal data when available (news, standings, prices)
- It doesn't contain the specific outcome being predicted (post-training questions)

The LLM should NOT be treated as an oracle of current state. It should be treated as a knowledgeable analyst who hasn't read the news in a year and needs to be briefed.

## What This Means for Implementation

**The question-guided approach is correct but the execution order matters:**

```
CORRECT (build from data, lookup from questions):
1. BUILD KG from news articles in time window
2. ENRICH KG with Wikidata hierarchy (timeless facts only)
3. For each question:
   a. PARSE question → identify entity names
   b. LOOKUP matching entities in KG → get their current state
   c. SURFACE hidden entities (base rates, structural rules) via LLM
   d. PREDICT using KG state + hidden + base rates + question-specific news

INCORRECT (build from questions):
1. ANALYZE all questions → extract entities   ← leaks selection info
2. BUILD KG from question analysis             ← KG is question-derived
3. PREDICT using KG                            ← circular
```

Step 2 (temporal data) is the bottleneck. For some question types (sports standings, stock prices), the data is structured and available via APIs. For others (political dynamics, conflict patterns), we need news as a proxy for temporal state. The key is that news retrieval must be TARGETED at the entities in the question, not generic — but the KG itself must be built from news, not from questions.
