"""Standalone, deterministic literal reader for textual-evidence-navigation-v1.

Only the supplied JSON records are consulted. Inline scope uses conservative
English syntax patterns, not an interpretation of the explanatory prompt.
Valid requests emit one bounded JSON object. Invalid requests exit 2 with a
bounded stderr diagnostic and no stdout because their identity may be invalid.
"""

import hashlib
import json
import re
import sys


MAX_INPUT_BYTES = 320 * 1024
MAX_OUTPUT_BYTES = 16 * 1024
MAX_ITEMS = 32
CONTRACT_ID = "textual-evidence-navigation-v1"
REQUESTED_FIELDS = [
    "references", "relationships", "claim_labels", "target_labels", "interpretations"
]
OPERATORS = {
    "cite_sources": "source",
    "cite_documents": "source",
    "outgoing_qualification": "qualification",
    "inline_scope": "qualification",
    "motivated_followups": "proposal",
}
STATUSES = {
    "definition", "hypothesis", "reported_result", "implementation_finding", "contested"
}
BASES = {"reported", "inferred", "observed"}
COMMON_FIELDS = {"id", "kind", "title"}
NODE_FIELDS = {
    "claim": {"statement", "status", "basis"},
    "source": {
        "href", "date", "dateType", "reviewedOn", "bibliographicOnly", "limitations"
    },
    "document": {"href", "contentHash", "commit"},
    "representation": {"status"},
    "transformation": {"status"},
    "experiment": {"status"},
}
PROPOSALS = {"representation", "transformation", "experiment"}
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")

# Accept only complete, closed research-result assertion forms. Additional
# sentences, clauses, location tails, and explanatory extensions abstain.
# This intentionally small grammar is not a general language/discourse parser.
SCOPE_SUBJECT = (
    r"(?:(?:the|these|those|our|this|that)\s+)?"
    r"(?:results?|findings?|observations?|evidence|conclusions?|measurements?|"
    r"study|experiment|trial|test|analysis|assessment|evaluation)"
)
GENERALIZATION_OBJECT = (
    r"(?:the\s+|any\s+)?(?:generalizability|generalisability|generalization|generalisation|"
    r"(?:general|universal|broader|broad)\s+"
    r"(?:reliability|benefits?|effectiveness|efficacy|validity|applicability))"
)
SCOPE_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"(?:this|that|" + SCOPE_SUBJECT + r")\s+(?:does|do|did)\s+not\s+"
    r"(?:establish|demonstrate|prove|show|imply|guarantee|support)\s+"
    + GENERALIZATION_OBJECT,
    SCOPE_SUBJECT + r"\s+(?:cannot|can\s+not|must\s+not|should\s+not)\s+be\s+"
    r"(?:generalized|generalised|extrapolated)",
    SCOPE_SUBJECT + r"\s+(?:is|are|was|were)\s+not\s+(?:necessarily\s+)?"
    r"(?:generalizable|generalisable)",
))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_fields(value, fields, name):
    require(type(value) is dict and set(value) == set(fields), name + " fields invalid")


def string(value, limit, name, nullable=False):
    if nullable and value is None:
        return
    require(type(value) is str and bool(value.strip()), name + " must be a nonblank string")
    require(len(value.encode("utf-8")) <= limit, name + " too long")
    require(re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value) is None,
            name + " contains forbidden controls")


def identifier(value, name):
    require(type(value) is str and IDENTIFIER.fullmatch(value) is not None,
            name + " invalid")


def hex_string(value, length, name):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{%d}" % length, value)
            is not None, name + " invalid")


def string_array(value, name):
    require(type(value) is list, name + " must be an array")
    for item in value:
        string(item, 4096, name + " item")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON number")


def decode_request(raw):
    require(len(raw) <= MAX_INPUT_BYTES, "input exceeds byte limit")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def validate_request(request):
    exact_fields(request, {"schema_version", "contract_id", "map", "case"}, "request")
    require(type(request["schema_version"]) is int and request["schema_version"] == 1,
            "request schema version invalid")
    require(request["contract_id"] == CONTRACT_ID, "contract invalid")
    graph = request["map"]
    exact_fields(graph, {"schemaVersion", "sourceCommit", "catalogHash", "nodes",
                         "edges", "limits", "payloadHash"}, "map")
    require(type(graph["schemaVersion"]) is int and graph["schemaVersion"] == 1,
            "map schema version invalid")
    hex_string(graph["sourceCommit"], 40, "source commit")
    hex_string(graph["catalogHash"], 64, "catalog hash")
    hex_string(graph["payloadHash"], 64, "payload hash")
    string_array(graph["limits"], "map limits")
    require(type(graph["nodes"]) is list and len(graph["nodes"]) <= 128,
            "map node array invalid")
    nodes = {}
    for node in graph["nodes"]:
        require(type(node) is dict, "node must be an object")
        kind = node.get("kind")
        require(type(kind) is str and kind in NODE_FIELDS, "node kind unsupported")
        exact_fields(node, COMMON_FIELDS | NODE_FIELDS[kind], "node")
        identifier(node["id"], "node ID")
        require(node["id"] not in nodes, "duplicate node ID")
        string(node["title"], 512, "node title")
        if kind == "claim":
            string(node["statement"], 4096, "claim statement")
            require(type(node["status"]) is str and node["status"] in STATUSES,
                    "claim status invalid")
            require(type(node["basis"]) is str and node["basis"] in BASES,
                    "claim basis invalid")
        elif kind == "source":
            string(node["href"], 2048, "source href")
            for field in ("date", "dateType", "reviewedOn"):
                string(node[field], 100, "source date label", nullable=True)
            require(node["bibliographicOnly"] is True, "source must be bibliographic")
            string_array(node["limitations"], "source limitations")
        elif kind == "document":
            string(node["href"], 2048, "document href")
            hex_string(node["contentHash"], 64, "document hash")
            hex_string(node["commit"], 40, "document commit")
        else:
            require(node["status"] == "proposed", "proposal status invalid")
        nodes[node["id"]] = node
    require(type(graph["edges"]) is list and len(graph["edges"]) <= 512,
            "map edge array invalid")
    for edge in graph["edges"]:
        exact_fields(edge, {"source", "target", "type"}, "edge")
        identifier(edge["source"], "edge source")
        identifier(edge["target"], "edge target")
        require(edge["source"] in nodes and edge["target"] in nodes,
                "edge endpoint missing")
        string(edge["type"], 100, "edge type")
    payload = {key: value for key, value in graph.items() if key != "payloadHash"}
    require(hashlib.sha256(canonical(payload)).hexdigest() == graph["payloadHash"],
            "map payload hash mismatch")
    case = request["case"]
    exact_fields(case, {"case_id", "family", "prompt", "anchor_title", "operator",
                       "requested_fields"}, "case")
    identifier(case["case_id"], "case ID")
    string(case["prompt"], 4096, "prompt")
    string(case["anchor_title"], 512, "anchor title")
    require(type(case["operator"]) is str and case["operator"] in OPERATORS,
            "operator unsupported")
    require(case["family"] == OPERATORS[case["operator"]], "operator family mismatch")
    require(case["requested_fields"] == REQUESTED_FIELDS, "requested fields invalid")
    return nodes


def reference(node, field, quote=None):
    return {"node_id": node["id"], "pointer": "/" + field, "quote": quote}


def claim_references(node):
    return [reference(node, field) for field in ("title", "statement", "status", "basis")]


def blank_response(request):
    return {
        "schema_version": 1,
        "case_id": request["case"]["case_id"],
        "map_payload_hash": request["map"]["payloadHash"],
        "answer_status": "unresolved",
        "references": [],
        "relationships": [],
        "claim_labels": None,
        "target_labels": [],
        "interpretations": ["insufficient_support"],
        "unresolved_reason": "The supplied records do not support the requested operation.",
    }


def unresolved(response, reason):
    response["answer_status"] = "unresolved"
    response["unresolved_reason"] = reason
    if "insufficient_support" not in response["interpretations"]:
        response["interpretations"].append("insufficient_support")
    return response


def target_references(node):
    kind = node["kind"]
    if kind == "claim":
        return claim_references(node)
    if kind == "source":
        fields = ["title", "href", "date", "dateType", "reviewedOn", "bibliographicOnly"]
        fields.extend("limitations/" + str(index) for index in range(len(node["limitations"])))
    elif kind == "document":
        fields = ["title", "href", "contentHash", "commit"]
    else:
        fields = ["title", "status"]
    return [reference(node, field) for field in fields]


def scope_quote(statement):
    # There is no sentence extraction: all substantive input must match one
    # closed assertion form. Only outer whitespace and one terminal period may
    # be outside the quoted text. Interior spacing/capitalization stay exact.
    assertion = statement.strip().removesuffix(".")
    if any(pattern.fullmatch(assertion) for pattern in SCOPE_PATTERNS):
        return assertion
    return None


def unique_items(items):
    seen = set()
    result = []
    for item in items:
        key = canonical(item)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def bound_response(response, anchor):
    for field in ("references", "relationships", "target_labels", "interpretations"):
        response[field] = unique_items(response[field])
    too_many = any(len(response[field]) > MAX_ITEMS for field in (
        "references", "relationships", "target_labels", "interpretations"
    ))
    too_large = len(canonical(response)) + 1 > MAX_OUTPUT_BYTES
    if too_many or too_large:
        # Preserve just the anchor context; never present a truncated lookup as complete.
        response["references"] = claim_references(anchor) if anchor else []
        response["relationships"] = []
        response["target_labels"] = []
        response["interpretations"] = ["insufficient_support"]
        unresolved(response, "Relevant evidence exceeds the response item or byte budget.")
    require(len(canonical(response)) + 1 <= MAX_OUTPUT_BYTES, "response exceeds byte limit")
    return response


def answer(request, nodes):
    response = blank_response(request)
    case = request["case"]
    anchors = [node for node in nodes.values()
               if node["kind"] == "claim" and node["title"] == case["anchor_title"]]
    if len(anchors) != 1:
        return unresolved(response, "The anchor title does not identify exactly one claim.")
    anchor = anchors[0]
    response["claim_labels"] = {
        "node_id": anchor["id"], "status": anchor["status"], "basis": anchor["basis"]
    }
    response["references"] = claim_references(anchor)
    operator = case["operator"]
    if operator == "inline_scope":
        quote = scope_quote(anchor["statement"])
        if quote is None:
            return bound_response(unresolved(response,
                "No explicit scope restriction matched the conservative literal rules."), anchor)
        response["references"][1] = reference(anchor, "statement", quote)
        response["interpretations"] = ["explicit_scope_not_generalization"]
    else:
        edge_type, kinds, interpretation = {
            "cite_sources": ("cites", {"source"}, "bibliographic_reference_only"),
            "cite_documents": ("cites", {"document"}, "document_metadata_only"),
            "outgoing_qualification": ("challenges", {"claim"}, "qualification_not_refutation"),
            "motivated_followups": ("motivates", PROPOSALS, "proposed_not_completed"),
        }[operator]
        edges = [edge for edge in request["map"]["edges"]
                 if edge["source"] == anchor["id"] and edge["type"] == edge_type
                 and nodes[edge["target"]]["kind"] in kinds]
        edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["type"]))
        if not edges:
            return bound_response(unresolved(response,
                "No outgoing " + edge_type + " edge reaches a supported target kind."), anchor)
        for edge in edges:
            node = nodes[edge["target"]]
            response["relationships"].append(dict(edge))
            response["target_labels"].append({
                "node_id": node["id"], "kind": node["kind"],
                "status": node.get("status"), "basis": node.get("basis"),
            })
            response["references"].extend(target_references(node))
        response["interpretations"] = [interpretation]
    response["answer_status"] = "answered"
    response["unresolved_reason"] = None
    return bound_response(response, anchor)


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        request = decode_request(raw)
        nodes = validate_request(request)
        response = answer(request, nodes)
        sys.stdout.buffer.write(canonical(response) + b"\n")
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        # Never reflect untrusted input, stack traces, or potentially large data.
        sys.stderr.write("Rejected input: invalid JSON, public schema, integrity, or bounds.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
