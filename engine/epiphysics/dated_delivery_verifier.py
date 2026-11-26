"""Independent, fixed byte-grammar checker for one retained link inventory.

Pure APIs perform no I/O. The caller proves Git ancestry, capture timing and
authority; this module checks a declared immutable manifest and submitted bytes.
It neither produces an inventory nor shares a parser with its future producer.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

IMPLEMENTATION_CODE = sys._getframe().f_code
_SOURCE_PATH = Path(__file__)
with _SOURCE_PATH.open('rb') as _stream:
    IMPLEMENTATION_SOURCE = _stream.read(131073)
if len(IMPLEMENTATION_SOURCE) > 131072:
    raise ValueError('Verifier source exceeds byte bound')
IMPLEMENTATION_DEPENDENCIES = ()

MAX_SOURCE_BYTES = 262144
MAX_MANIFEST_BYTES = 1048576
MAX_DELIVERY_BYTES = 1048576
MAX_RESULT_BYTES = 1048576
MAX_CANDIDATES = 1024
MAX_COUNTEREXAMPLES = 32
STATUSES = ('regular_file', 'missing', 'not_regular', 'outside_scope')
REASONS = ('fenced_code', 'inline_code', 'image', 'reference_style',
           'unterminated_syntax', 'nested_syntax', 'escaped_syntax',
           'template_destination', 'url_destination', 'absolute_destination',
           'unsupported_destination')
BINDINGS = ('schema_version', 'task_id', 'registration_id', 'protocol_sha256',
            'criteria_sha256', 'source_commit', 'source_path', 'source_sha256',
            'tree_manifest_sha256')
INVENTORY_FIELDS = BINDINGS[:-1] + ('links', 'unsupported', 'summary')
TOKEN_FIELDS = ('token_id', 'start', 'end', 'destination', 'fragment')
LINK_FIELDS = TOKEN_FIELDS + ('target', 'target_status')
RESULT_TOKEN_FIELDS = ('start', 'end', 'shared_source_directory_parts', 'target_suffix', 'target_status')
CHECKS = ('exact_task_binding', 'complete_scoped_inventory',
          'directed_target_resolution', 'exact_retained_evidence', 'truthful_summary')
CRITERIA = {
    'schema_version': 1, 'criteria_id': 'dated-link-inventory-v1',
    'encoding': 'strict UTF-8; original byte offsets [start,end), including CRLF; no Unicode normalization',
    'candidates': 'At [, include an immediately preceding !. Consume a balanced [] label and immediate balanced (...) destination or [...] reference suffix on one physical line. Backslash escapes suppress delimiter matching. Consume nested groups as one candidate. Bare [label] is reference_style. Unterminated groups stop before CR/LF or EOF. Advance to the end; candidates do not overlap.',
    'fences': 'Line start after zero to three spaces, at least three backticks or tildes. Close with the same marker, length at least the opening run, and only spaces/tabs afterward. An unclosed fence extends to EOF.',
    'inline_code': 'Outside fences, maximal backtick runs close at the next equal-length maximal run, possibly across lines. An unmatched run is literal.',
    'code_candidates': 'Link-shaped candidates intersecting code regions remain unsupported; fenced_code takes precedence over inline_code.',
    'reason_priority': list(REASONS),
    'destination': 'Relative POSIX path ending literal .md, optionally first # and its raw fragment (empty allowed). Reject ASCII whitespace/control, backslash, brackets, parentheses, angle brackets, quotes, backticks, braces, colon, percent or question mark anywhere. Braces denote template_destination; URI scheme or // prefix denotes url_destination; leading / denotes absolute_destination. Unicode labels, paths and fragments are permitted. No percent decoding.',
    'normalization': 'Resolve . and .. lexically against source directory; any root escape gives null target/outside_scope. Exact Git mode 100644/100755 is regular_file; directory/symlink/submodule or non-directory ancestor is not_regular; otherwise absent is missing. Never access live paths.',
    'fragment_validity': None,
    'manifest_codec': 'UTF-8 canonical JSON: sorted keys, separators comma/colon, ensure_ascii false, finite values, no trailing newline',
    'registration_binding_fields': list(BINDINGS),
    'inventory_fields': list(INVENTORY_FIELDS),
    'link_fields': list(LINK_FIELDS),
    'unsupported_fields': ['start', 'end', 'reason'],
    'summary_fields': ['eligible', 'unsupported', 'target_status_counts'],
    'target_statuses': list(STATUSES),
    'result_token_fields': list(RESULT_TOKEN_FIELDS),
    'result_tokens': 'Every eligible token has one compact row in source order. Token identity is source_sha256:start:end; destination and fragment come from that retained source span under this grammar. Reconstruct target by joining the first shared_source_directory_parts components of the retained registration source_path directory with target_suffix; both are null for outside_scope. No token coverage is truncated.',
    'result_bindings': 'The raw result retains fixed-size registration binding fields except source_path, binds that path as SHA-256 of its UTF-8 bytes, and also binds all nine original fields by their canonical JSON digest. The complete path remains in the retained registration, avoiding unbounded repeated path text.',
    'criteria': list(CHECKS),
    'limits': {'source_bytes': MAX_SOURCE_BYTES, 'manifest_bytes': MAX_MANIFEST_BYTES,
               'delivery_bytes': MAX_DELIVERY_BYTES, 'result_bytes': MAX_RESULT_BYTES,
               'candidates': MAX_CANDIDATES, 'counterexamples': MAX_COUNTEREXAMPLES},
    'failure_boundary': 'Malformed trusted registration/source/tree raises ValueError. Within-limit malformed delivered bytes produce a criterion-negative result; unavailable dependent criteria are null. Oversized submissions are handled by the caller retained-prefix rejection path, not this API.',
    'ancestry_scope': 'Caller independently proves complete Git commit/tree/blob ancestry; checker verifies manifest shape, canonical digest and selected source blob binding.'}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('Invalid canonical JSON') from error


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _keys(value, names):
    return type(value) is dict and set(value) == set(names)


def _hex(value, length):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def _path(value):
    return (type(value) is str and bool(value) and not value.startswith('/')
            and '\\' not in value and all(ord(c) >= 32 and ord(c) != 127 for c in value)
            and all(part not in ('', '.', '..') for part in value.split('/')))


def _source(raw):
    _require(type(raw) is bytes and len(raw) <= MAX_SOURCE_BYTES, 'Source byte bound/type')
    try:
        raw.decode('utf-8')
    except UnicodeError as error:
        raise ValueError('Source must be strict UTF-8') from error


def _code_regions(raw):
    fences, offset, opened = [], 0, None
    for line in raw.splitlines(keepends=True):
        # Only CR/LF are physical line ends in the frozen byte grammar.
        body = line.rstrip(b'\r\n')
        match = re.match(rb' {0,3}(`{3,}|~{3,})(.*)\Z', body)
        if opened is None and match:
            marker = match[1]
            opened = (offset, marker[:1], len(marker))
        elif opened is not None and match:
            marker = match[1]
            if marker[:1] == opened[1] and len(marker) >= opened[2] and not match[2].strip(b' \t'):
                fences.append((opened[0], offset + len(line), 'fenced_code'))
                opened = None
        offset += len(line)
    if opened is not None:
        fences.append((opened[0], len(raw), 'fenced_code'))
    regions, begin = list(fences), 0
    for start, end, _ in fences + [(len(raw), len(raw), '')]:
        runs = [(m.start() + begin, m.end() + begin) for m in re.finditer(rb'`+', raw[begin:start])]
        following, last = {}, {}
        for i in range(len(runs) - 1, -1, -1):
            size = runs[i][1] - runs[i][0]
            following[i] = last.get(size)
            last[size] = i
        i = 0
        while i < len(runs):
            close = following[i]
            if close is None:
                i += 1
            else:
                regions.append((runs[i][0], runs[close][1], 'inline_code'))
                i = close + 1
        begin = end
    return sorted(regions)


def _group(raw, start, opening, closing):
    depth, nested, escaped, i = 1, False, False, start + 1
    while i < len(raw) and raw[i] not in (10, 13):
        char = raw[i]
        if char == 92:
            escaped = True
            i += 1
            if i < len(raw) and raw[i] not in (10, 13):
                i += 1
            continue
        if char == opening:
            depth += 1
            nested = True
        elif char == closing:
            depth -= 1
            if depth == 0:
                return i + 1, True, nested, escaped
        i += 1
    return i, False, nested, escaped


def inspect_source(source_bytes):
    """Describe only eligible/source-excluded tokens; no target lookup or delivery."""
    _source(source_bytes)
    raw, regions, source_hash = source_bytes, _code_regions(source_bytes), _sha(source_bytes)
    expected, unsupported, cursor, region_cursor, count = [], [], 0, 0, 0
    while (opening := raw.find(b'[', cursor)) >= 0:
        start = opening - 1 if opening > cursor and raw[opening - 1] == 33 else opening
        end, closed, nested, escaped = _group(raw, opening, 91, 93)
        slash, back = 0, start - 1
        while back >= 0 and raw[back] == 92:
            slash += 1
            back -= 1
        escaped = escaped or slash % 2 == 1
        kind, destination = 'reference_style', None
        if closed and end < len(raw) and raw[end] in (40, 91):
            destination_start, delimiter = end, raw[end]
            end, tail_closed, tail_nested, tail_escaped = _group(raw, end, delimiter, 41 if delimiter == 40 else 93)
            nested, escaped = nested or tail_nested, escaped or tail_escaped
            closed = tail_closed
            if delimiter == 40:
                kind = 'inline'
                if closed:
                    destination = raw[destination_start + 1:end - 1].decode('utf-8')
        while region_cursor < len(regions) and regions[region_cursor][1] <= start:
            region_cursor += 1
        overlaps = []
        i = region_cursor
        while i < len(regions) and regions[i][0] < end:
            overlaps.append(regions[i][2])
            i += 1
        reason = ('fenced_code' if 'fenced_code' in overlaps else
                  'inline_code' if 'inline_code' in overlaps else
                  'image' if start < opening else
                  'reference_style' if kind == 'reference_style' and closed else
                  'unterminated_syntax' if not closed else
                  'nested_syntax' if nested else
                  'escaped_syntax' if escaped else None)
        if reason is None:
            if '{' in destination or '}' in destination:
                reason = 'template_destination'
            elif re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', destination) or destination.startswith('//'):
                reason = 'url_destination'
            elif destination.startswith('/'):
                reason = 'absolute_destination'
            elif (not destination.split('#', 1)[0].endswith('.md') or
                  any(ord(c) <= 32 or ord(c) == 127 or c in '\\[]()<>\"\'`{}:%?' for c in destination)):
                reason = 'unsupported_destination'
        count += 1
        _require(count <= MAX_CANDIDATES, 'Source candidate count exceeds bound')
        if reason is not None:
            unsupported.append({'start': start, 'end': end, 'reason': reason})
        else:
            fragment = destination.split('#', 1)[1] if '#' in destination else None
            expected.append({'token_id': f'{source_hash}:{start}:{end}', 'start': start,
                             'end': end, 'destination': destination, 'fragment': fragment})
        cursor = end
    return {'expected_tokens': expected, 'unsupported_tokens': unsupported}


def _trusted(registration, source_bytes, manifest):
    _require(type(registration) is dict and all(k in registration for k in BINDINGS), 'Registration bindings missing')
    _require(type(registration['schema_version']) is int and registration['schema_version'] == 1, 'Registration version')
    for key in ('task_id', 'registration_id'):
        _require(type(registration[key]) is str and 0 < len(registration[key]) <= 200, 'Registration identity')
    for key in ('protocol_sha256', 'criteria_sha256', 'source_sha256', 'tree_manifest_sha256'):
        _require(_hex(registration[key], 64), 'Registration digest')
    _require(_hex(registration['source_commit'], 40) and _path(registration['source_path']), 'Registration source identity')
    _source(source_bytes)
    _require(_sha(source_bytes) == registration['source_sha256'], 'Source digest differs')
    _require(_keys(manifest, ('schema_version', 'source_commit', 'entries'))
             and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
             and manifest['source_commit'] == registration['source_commit']
             and type(manifest['entries']) is list, 'Tree manifest shape')
    encoded = canonical(manifest)
    _require(len(encoded) <= MAX_MANIFEST_BYTES and _sha(encoded) == registration['tree_manifest_sha256'], 'Tree manifest digest/bound')
    by_path, previous = {}, None
    for entry in manifest['entries']:
        _require(_keys(entry, ('path', 'mode', 'object_id')) and _path(entry['path'])
                 and entry['mode'] in ('100644', '100755', '120000', '160000', '040000')
                 and _hex(entry['object_id'], 40), 'Tree manifest entry')
        path = entry['path']
        _require(previous is None or previous < path, 'Tree paths must be unique and sorted')
        for i in range(1, len(path.split('/'))):
            parent = '/'.join(path.split('/')[:i])
            _require(parent in by_path and by_path[parent]['mode'] == '040000', 'Tree parent is not a declared directory')
        by_path[path], previous = entry, path
    source = by_path.get(registration['source_path'])
    blob_id = hashlib.sha1(b'blob ' + str(len(source_bytes)).encode() + b'\0' + source_bytes).hexdigest()
    _require(source is not None and source['mode'] in ('100644', '100755')
             and source['object_id'] == blob_id, 'Source Git blob binding differs')
    return by_path


def _target(source_path, destination, entries):
    parts = source_path.split('/')[:-1]
    for part in destination.split('#', 1)[0].split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts:
                return None, 'outside_scope'
            parts.pop()
        else:
            parts.append(part)
    target = '/'.join(parts)
    for i in range(1, len(parts)):
        ancestor = entries.get('/'.join(parts[:i]))
        if ancestor is not None and ancestor['mode'] != '040000':
            return target, 'not_regular'
    entry = entries.get(target)
    return target, ('missing' if entry is None else 'regular_file'
                    if entry['mode'] in ('100644', '100755') else 'not_regular')


def _summary(links, unsupported):
    return {'eligible': len(links), 'unsupported': len(unsupported),
            'target_status_counts': {status: sum(row['target_status'] == status for row in links) for status in STATUSES}}


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite_json_number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def _inventory_shape(value, source_size):
    if not _keys(value, INVENTORY_FIELDS) or type(value['schema_version']) is not int or value['schema_version'] != 1:
        return False
    if any(type(value[k]) is not str for k in BINDINGS[1:-1]):
        return False
    if type(value['links']) is not list or type(value['unsupported']) is not list or len(value['links']) + len(value['unsupported']) > MAX_CANDIDATES:
        return False
    for row in value['links'] + value['unsupported']:
        fields = LINK_FIELDS if 'token_id' in row else ('start', 'end', 'reason')
        if not _keys(row, fields) or not all(type(row[k]) is int for k in ('start', 'end')) or not 0 <= row['start'] < row['end'] <= source_size:
            return False
    for row in value['links']:
        if not _keys(row, LINK_FIELDS) or not all(type(row[k]) is str for k in ('token_id', 'destination', 'target_status')) or row['target_status'] not in STATUSES:
            return False
        if row['target'] is not None and not _path(row['target']):
            return False
        if row['fragment'] is not None and type(row['fragment']) is not str:
            return False
    for row in value['unsupported']:
        if not _keys(row, ('start', 'end', 'reason')) or row['reason'] not in REASONS:
            return False
    summary = value['summary']
    return (_keys(summary, ('eligible', 'unsupported', 'target_status_counts'))
            and all(type(summary[k]) is int and summary[k] >= 0 for k in ('eligible', 'unsupported'))
            and _keys(summary['target_status_counts'], STATUSES)
            and all(type(n) is int and n >= 0 for n in summary['target_status_counts'].values()))


def verify_inventory(registration, source_bytes, tree_manifest, delivered_bytes):
    """Check first submitted bytes. Bad deliveries are results, not retry errors."""
    entries = _trusted(registration, source_bytes, tree_manifest)
    _require(type(delivered_bytes) is bytes and len(delivered_bytes) <= MAX_DELIVERY_BYTES,
             'Delivery transport byte bound/type; use retained-prefix rejection for overflow')
    scan = inspect_source(source_bytes)
    expected, packed_tokens = [], []
    source_directory = registration['source_path'].split('/')[:-1]
    for token in scan['expected_tokens']:
        target, status = _target(registration['source_path'], token['destination'], entries)
        shared, suffix = None, None
        if target is not None:
            target_parts, shared = target.split('/'), 0
            while shared < min(len(source_directory), len(target_parts)) and source_directory[shared] == target_parts[shared]:
                shared += 1
            suffix = '/'.join(target_parts[shared:])
        packed_tokens.append([token['start'], token['end'], shared, suffix, status])
        # Do not retain one expanded copy of a long source directory per token.
        expected.append({**token, 'target_status': status})
    result = {'schema_version': 1, 'verdict': 'fail',
              'bindings': {k: registration[k] for k in BINDINGS if k != 'source_path'},
              'source_path_sha256': _sha(registration['source_path'].encode('utf-8')),
              'registration_bindings_sha256': _sha(canonical({k: registration[k] for k in BINDINGS})),
              'artifact_sha256': _sha(delivered_bytes),
              'criteria': {key: None for key in CHECKS}, 'counterexamples': [],
              'expected_token_fields': list(RESULT_TOKEN_FIELDS),
              'expected_tokens': packed_tokens, 'unsupported_tokens': scan['unsupported_tokens'],
              'expected_summary': _summary(expected, scan['unsupported_tokens']), 'reported_summary': None,
              'limits': {'fragment_validity': None, 'git_ancestry': 'caller-verified; not independently rechecked here',
                         'semantic_suitability': None, 'scientific_truth': None, 'rendered_navigation': None}}
    result['criteria']['exact_retained_evidence'] = True
    def fail(criterion, reason, row=None):
        if len(result['counterexamples']) < MAX_COUNTEREXAMPLES:
            result['counterexamples'].append({'criterion': criterion, 'reason': reason,
                'start': None if row is None else row['start'], 'end': None if row is None else row['end']})
    value, parse_error = None, None
    try:
        value = _json(delivered_bytes)
        canonical(value)  # Reject lone Unicode surrogates and overflow-to-infinity numbers.
        if not _inventory_shape(value, len(source_bytes)):
            parse_error = 'invalid_inventory_schema'
    except UnicodeError:
        parse_error = 'invalid_utf8'
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        parse_error = 'invalid_json'
    if parse_error is not None:
        result['criteria']['exact_task_binding'] = False
        fail('exact_task_binding', parse_error)
    else:
        binding = all(type(value[k]) is type(registration[k]) and value[k] == registration[k] for k in BINDINGS[:-1])
        result['criteria']['exact_task_binding'] = binding
        if not binding:
            fail('exact_task_binding', 'registration_binding_differs')
        identities = lambda rows: [{k: row[k] for k in TOKEN_FIELDS} for row in rows]
        complete = identities(value['links']) == identities(expected) and value['unsupported'] == scan['unsupported_tokens']
        result['criteria']['complete_scoped_inventory'] = complete
        if not complete:
            fail('complete_scoped_inventory', 'tokens_order_spans_or_exclusions_differ')
        expected_by_id = {row['token_id']: (row, packed) for row, packed in zip(expected, packed_tokens)}
        target_checks = []
        for row in value['links']:
            matched = expected_by_id.get(row['token_id'])
            valid = False
            if matched is not None:
                original, packed = matched
                target = None if packed[2] is None else '/'.join(source_directory[:packed[2]] + ([packed[3]] if packed[3] else []))
                valid = all(row[key] == original[key] for key in TOKEN_FIELDS + ('target_status',)) and row['target'] == target
            target_checks.append(valid)
            if not valid:
                fail('directed_target_resolution', 'token_or_target_differs', row)
        result['criteria']['directed_target_resolution'] = all(target_checks)
        result['reported_summary'] = value['summary']
        result['criteria']['truthful_summary'] = value['summary'] == _summary(value['links'], value['unsupported'])
        if not result['criteria']['truthful_summary']:
            fail('truthful_summary', 'summary_does_not_reconcile')
        if all(result['criteria'].values()):
            result['verdict'] = 'pass'
    _require(len(canonical(result)) <= MAX_RESULT_BYTES, 'Raw verification result exceeds output bound')
    return result


def runtime_sources():
    """Separate source receipt helper; pure checker APIs never access files."""
    path, source, code = _SOURCE_IDENTITY
    _require(IMPLEMENTATION_SOURCE == source and IMPLEMENTATION_CODE is code, 'Verifier implementation reloaded')
    _require(not path.is_symlink() and path.is_file() and path.stat().st_size == len(source), 'Verifier source changed')
    with path.open('rb') as stream:
        _require(stream.read(len(source) + 1) == source, 'Verifier source changed')
    _require(compile(source, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == code, 'Verifier executing code differs')
    for name, function, expected in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is expected, 'Verifier callable changed: ' + name)
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals().get(name) == value, 'Verifier constant changed: ' + name)
    return {__name__: source}


_SOURCE_IDENTITY = (_SOURCE_PATH, IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in (
    'MAX_SOURCE_BYTES', 'MAX_MANIFEST_BYTES', 'MAX_DELIVERY_BYTES', 'MAX_RESULT_BYTES',
    'MAX_CANDIDATES', 'MAX_COUNTEREXAMPLES', 'STATUSES', 'REASONS', 'BINDINGS',
    'INVENTORY_FIELDS', 'TOKEN_FIELDS', 'LINK_FIELDS', 'RESULT_TOKEN_FIELDS', 'CHECKS', 'CRITERIA'))
