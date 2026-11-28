"""Fixed leaf worker: bounded raw source stdin, line-index artifact stdout."""
import hashlib
import importlib.util
from pathlib import Path
import sys


PRODUCER_SHA256 = 'b75e28b42c0dab8b90275da511848ea49e865c11891414d3c180a51b25fecf4a'
SCHEMA_SHA256 = '7fca7514f1012274e51583cad46b6b0d66ee1f813cb6b760fab4cf78f8441413'


def main():
    # The parent binds the opaque obligation name in its retained command.
    if len(sys.argv) != 3 or sys.argv[2] != SCHEMA_SHA256:
        raise ValueError('worker binding differs')
    path = Path(__file__).with_name('producer.py')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRODUCER_SHA256:
        raise ValueError('producer bytes differ')
    source = sys.stdin.buffer.read(8193)
    spec = importlib.util.spec_from_file_location('fixed_line_index_producer', path)
    producer = importlib.util.module_from_spec(spec)
    # Execute the already-read pinned bytes, rather than rereading that path.
    exec(compile(raw, str(path), 'exec'), producer.__dict__)
    artifact = producer.produce_line_index(source)
    sys.stdout.buffer.write(artifact)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError):
        sys.stderr.write('fixed producer refused input or binding\n')
        raise SystemExit(2)
