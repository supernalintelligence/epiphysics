"""
Prompt templates for entity prediction experiments.

Each prompt is a function that takes a question dict and returns a string.
Prompts are versioned and tracked — every experiment logs which prompt was used.
"""

BASELINE_V1 = {
    "name": "baseline_v1",
    "description": "Simple direct question answering with no structural guidance",
    "template": """You are a forecasting system. Answer the following prediction question.

Question: {question}

Background information:
{background}

{choices_section}

Provide your answer as JSON:
{{
  "prediction": <your predicted probability 0.0-1.0, or "yes"/"no" for binary>,
  "confidence": <0-100>,
  "reasoning": "<brief reasoning in 1-2 sentences>"
}}"""
}

ENTITY_AWARE_V1 = {
    "name": "entity_aware_v1",
    "description": "Prompt that identifies key entities and their coupling before predicting",
    "template": """You are a forecasting system that reasons about entities and their influence.

Question: {question}

Background information:
{background}

{choices_section}

Before answering, identify:
1. KEY ENTITIES: Who are the main actors/forces that will determine the outcome?
2. EFFECTIVE MASS: Which entity has the most influence over this outcome? (highest coupling)
3. CURRENT STATE: What is each key entity's current trajectory?
4. COUPLINGS: How do these entities influence each other?

Respond with ONLY a JSON object (no markdown, no headers, no explanation outside the JSON):
{{
  "entities": ["<entity1>", "<entity2>"],
  "highest_influence": "<which entity matters most>",
  "prediction": <number 0.0-1.0>,
  "confidence": <0-100>,
  "reasoning": "<1-2 sentence reasoning>"
}}"""
}

STRUCTURAL_V1 = {
    "name": "structural_v1",
    "description": "Prompt that asks for basin analysis and regime identification",
    "template": """You are a forecasting system that identifies structural dynamics.

Question: {question}

Background information:
{background}

{choices_section}

Analyze this as a dynamical system:
1. REGIME: What regime is this system currently in? (stable/transitioning/chaotic)
2. BASINS: What are the likely stable outcomes (basins of attraction)?
3. BARRIERS: What would it take to transition between basins?
4. TIMESCALE: Is the question timescale shorter or longer than the system's natural timescale?
5. KEY FORCES: What forces are pushing toward each basin?

Respond with ONLY a JSON object (no markdown, no headers, no explanation outside the JSON):
{{
  "regime": "<stable/transitioning/chaotic>",
  "basins": ["<outcome1>", "<outcome2>"],
  "prediction": <number 0.0-1.0>,
  "confidence": <0-100>,
  "reasoning": "<1-2 sentence reasoning>"
}}"""
}

# ── Persistent System Prompts ────────────────────────────────

EXTRACTION_PROMPT = """You are a representation extraction system. Given recent news articles and a list of currently tracked entities, extract structured updates.

=== CURRENTLY TRACKED ENTITIES ===
{entity_context}

=== NEWS ARTICLES ===
{news_articles}

=== YOUR FOCUS ===
{focus}

Extract the following as a JSON object. Be precise and factual — only extract what the articles support:
{{
  "entity_updates": [
    {{
      "id": "<entity_slug (lowercase, underscores)>",
      "canonical_name": "<Full Name>",
      "trajectory": "<stable|escalating|de_escalating|volatile>",
      "activity_level": <0.0-1.0>,
      "key_attributes": {{"<attr>": "<value>"}},
      "summary": "<1 sentence current state>"
    }}
  ],
  "new_entities": [
    {{
      "canonical_name": "<Full Name>",
      "type": "<person|org|country|market|indicator|event_class|concept>",
      "domain": "<domain.subdomain>",
      "aliases": ["<alias1>"],
      "initial_state": {{
        "trajectory": "<trajectory>",
        "activity_level": <0.0-1.0>,
        "key_attributes": {{}},
        "summary": "<1 sentence>"
      }}
    }}
  ],
  "coupling_evidence": [
    {{
      "source": "<entity_slug>",
      "target": "<entity_slug>",
      "strength": <0.0-1.0>,
      "asymmetry": <-1.0 to 1.0, positive = source dominates>,
      "type": "<influence|co_occurrence|causal|reactive>",
      "domains": ["<domain>"],
      "evidence": "<1 sentence describing the coupling>"
    }}
  ]
}}

Only include entities and couplings supported by the articles. Limit to the 10 most important updates."""

PERSISTENT_PREDICTION_PROMPT = """You are a forecasting system with access to tracked entity states and recent news.

Question: {question}

Background: {background}

=== TRACKED ENTITY STATES (persistent knowledge) ===
{entity_context}

=== RECENT NEWS ===
{news_context}

=== YOUR FOCUS ===
{focus}

Using the entity states, couplings, and news above, predict the outcome.

Important:
- Use entity trajectories and coupling strengths to inform your prediction
- Consider base rates: for rare-event questions, check if the baseline is near zero (making any occurrence resolve YES)
- Calibrate your probability carefully — avoid defaulting to low probabilities

Respond with ONLY a JSON object:
{{
  "prediction": <number 0.0-1.0>,
  "confidence": <0-100>,
  "relevant_entities": ["<entity_id1>", "<entity_id2>"],
  "key_coupling": "<most important coupling for this prediction>",
  "reasoning": "<1-2 sentence reasoning citing entity states>"
}}"""

EXTRACTION_FOCUSES = {
    "political": "Focus on political actors, policy changes, government actions, diplomatic events, and elections.",
    "economic": "Focus on economic indicators, market movements, trade policies, central bank actions, and business entities.",
    "conflict": "Focus on conflict dynamics, violence events, security situations, armed groups, protests, and humanitarian conditions.",
}

PREDICTION_FOCUSES = {
    "base_rate": "Focus on calibration: what is the base rate for this type of question? Avoid being too confident or too conservative. For rare-event questions, consider whether a near-zero baseline means any occurrence resolves YES.",
    "entity_dynamics": "Focus on entity trajectories: which tracked entities are relevant, what direction are they moving, and how do their couplings affect the likely outcome?",
    "structural": "Focus on structural analysis: what regime is the system in (stable/transitioning/chaotic), what are the basins of attraction, and what forces push toward each outcome?",
}

ALL_PROMPTS = {
    "baseline_v1": BASELINE_V1,
    "entity_aware_v1": ENTITY_AWARE_V1,
    "structural_v1": STRUCTURAL_V1,
}


def format_prompt(prompt_config: dict, question: dict, news_context: str = None) -> str:
    """Format a prompt template with a question and optional news context."""
    choices = question.get("choices")
    if choices:
        choices_section = f"Possible answers: {', '.join(str(c) for c in choices)}"
    else:
        choices_section = "Answer with a probability between 0.0 and 1.0."

    background = question.get("background", "No additional background.")
    if news_context:
        background = background + "\n\n" + news_context

    return prompt_config["template"].format(
        question=question["question"],
        background=background,
        choices_section=choices_section,
    )
