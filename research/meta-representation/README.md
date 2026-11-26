# Curated research map

This is the first inspectable knowledge map for the [meta-representation investigation](../../docs/research/meta-representational-systems.md). It contains **30 primary-source references, 9 repository documents, 26 claims, 7 candidate representations, 4 transformation concepts, 6 proposed experiments, and 101 directed relationships**. Counts describe the initial seed, not an automatically discovered or comprehensive literature graph.

Source files contain bibliographic metadata, supported claims and limitations. `registry.json` contains the curated local nodes and edges. All candidate representations, transformations and experiments are proposed. Existing implementation facts are separate claims linked to committed code or documents. The map does not infer that a cited claim is true.

## Compile and inspect

From the repository root, with Python 3.10+:

```sh
PYTHONPATH=engine python3 -m epiphysics.knowledge --repo . --catalog research/meta-representation
PYTHONPATH=engine python3 -m epiphysics.knowledge --repo . --catalog research/meta-representation --output /tmp/epiphysics-research-map.json
PYTHONPATH=engine python3 -m unittest discover -s engine/tests -v
```

Use a fresh output filename for each export. The compiler refuses to replace an existing file. It reads only the explicitly listed document paths from one pinned Git HEAD, ignoring working-tree modifications and untracked drafts. It embeds their exact committed UTF-8 content and SHA-256 hashes. Commit document changes before compiling a map intended to include them. Retain the output and referenced Git history if you need to reproduce that version later.

The catalog files themselves are operator-curated inputs and may be uncommitted while editing. Their validated content is embedded in the graph payload. A canonical payload hash covers schema version, frozen repository commit, sorted nodes and sorted edges; generation time is excluded so the same inputs replay to the same hash. This is a local integrity property, not an external timestamp.

External references are explicitly `bibliographic_only: true`: the tool does not fetch or archive article bytes. `reviewed_on` records the research review date; `date` and `date_type` describe publication, revision or other bibliographic metadata. Undated live documentation uses `date: null`. None of those fields is a collection receipt or permission to backdate evidence. The graph is not eligible as a prospective historical snapshot merely because a referenced paper is old.

## Node and relationship meanings

| Record | Meaning |
| --- | --- |
| `source` | Primary external reference with bibliographic provenance and limits. |
| `document` | Explicitly selected committed local file, embedded by the compiler. |
| `claim` | Curator-attributed statement with a status and epistemic basis. `observed` here means direct inspection of code, not independent measurement of the world. |
| `representation` | Proposed encoding or view to compare; not an executable representation manifest yet. |
| `transformation` | Proposed operation family. Its adjacency links identify involved representations, not typed input/output ports or a validated executable mapping. |
| `experiment` | Proposed comparison corresponding to E1–E6 in the protocol document; not preregistered or run. |

`cites` connects a claim to a source/document, without certifying support. `challenges` records tension, qualification or an alternative mechanism, not necessarily logical contradiction: concentration and portability can both operate. `motivates` connects a claim to a proposed object. `compares` identifies an experiment's candidate representations. `transforms` identifies representations involved in a transformation concept. `depends_on` records a declared dependency. `implements` is reserved for explicit document-to-representation/transformation mappings; none is inferred automatically.

The validator checks allowed endpoint kinds and preserves direction and multiple predicates. It does not prove claim correctness, causal identification, independence of sources, acyclicity, or semantic preservation. The full production representation/transform contracts are planned in [the build sequence](../../docs/planning/meta-representation-build.md).

## Extend deliberately

Add sources with stable bibliographic URLs and honest date precision. Pin mutable implementations before experiments. Add a new attributed claim for disagreement rather than overwriting an existing one. Link evidence that challenges a proposal as carefully as evidence that supports it. Do not add confidence numbers without a defined quantity and calibration procedure.

Add only permitted committed repository files as document nodes. The initial map excludes the untracked entity-prediction experiment files; the research assessment records their provisional status separately. Source contents are data, never instructions to the compiler or an agent. No network, model calls, payments, ledger writes or autonomous research runs are performed by this tool.

For machine consumers, use `schema_version: 1` and the current validator. This planning catalog is intentionally small; it is not a universal ontology. Changes to the format need tests and versioning before downstream callers depend on them.
