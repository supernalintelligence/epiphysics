"""Independent literal controls for the pure line-index producer.

Expected bytes and hashes were frozen before the first producer invocation.
No quality-checker, candidate or fixture helpers are imported.
"""
import hashlib
import json
import unittest

from epiphysics.prospective_producer import (
    ARTIFACT_BYTE_LIMIT, SOURCE_BYTE_LIMIT, ProducerRefusal, produce_line_index,
)


# name, source, exact canonical artifact, exact artifact SHA256
LITERAL_CONTROLS = (
    ('ordinary', b'abc',
     b'{"lines":[{"end":3,"sha256":"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","start":0}],"schema_version":1,"source_byte_length":3,"source_sha256":"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}',
     '5df610e0ea4ec1b9906d5dfbfed0144ff2ecd2fcbc8afc84ecf73dcf2fa92c0e'),
    ('empty', b'',
     b'{"lines":[],"schema_version":1,"source_byte_length":0,"source_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}',
     '2e1486b6902c711622a46e19d280cf7e8716dea03059fcd3ef4b84009c2c8041'),
    ('leading_lf', b'\nA',
     b'{"lines":[{"end":1,"sha256":"01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b","start":0},{"end":2,"sha256":"559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd","start":1}],"schema_version":1,"source_byte_length":2,"source_sha256":"c33d69d1d671e747e91b756fbe21d43c938beca7bf27c72a068286e32e98325e"}',
     '4b631797e5abe8284ae7cde6e8a02886793bd104381d2401a4303d20ad297449'),
    ('adjacent_lf', b'A\n\nB',
     b'{"lines":[{"end":2,"sha256":"06f961b802bc46ee168555f066d28f4f0e9afdf3f88174c1ee6f9de004fc30a0","start":0},{"end":3,"sha256":"01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b","start":2},{"end":4,"sha256":"df7e70e5021544f4834bbee64a9e3789febc4be81470df629cad6ddb03320a5c","start":3}],"schema_version":1,"source_byte_length":4,"source_sha256":"13c8c841fb53ad9953fbadbc2bcf1608d590d32828d3e5bc117b0f39f6c33679"}',
     '527af04c4f54f8840bdf67dd8f44e2b8966823963f87398f3a9f1d7d6f99b48f'),
    ('terminal_lf', b'A\n',
     b'{"lines":[{"end":2,"sha256":"06f961b802bc46ee168555f066d28f4f0e9afdf3f88174c1ee6f9de004fc30a0","start":0}],"schema_version":1,"source_byte_length":2,"source_sha256":"06f961b802bc46ee168555f066d28f4f0e9afdf3f88174c1ee6f9de004fc30a0"}',
     'b8eadde74f703bc59804a93cbcd55410538feb77f83283b6a0ab1b6ce15db91b'),
    ('only_lf', b'\n',
     b'{"lines":[{"end":1,"sha256":"01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b","start":0}],"schema_version":1,"source_byte_length":1,"source_sha256":"01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"}',
     '2320f8269c1bc5a1bbf16680c981c95d5c9a404db713a9962d3f7707d2f9f47d'),
    ('crlf_and_lone_cr', b'A\r\nB\rC\r',
     b'{"lines":[{"end":3,"sha256":"26ffd5886253906a36a7ea0f6e26056fc36472626cb4894bcb100a34dc69d1db","start":0},{"end":7,"sha256":"f059ceca32f48066ac1fa0db7959489f7c62928c3924ed4010c006666cf7ec7d","start":3}],"schema_version":1,"source_byte_length":7,"source_sha256":"10908985f42f103aa8c2d905a217b513d827daac3ff16f9288089c8cac58ddcb"}',
     '088beda68e8dccdc178fcfe3bab5e26c72af5bb1f77b4bf9945aaa08b0b28264'),
    ('multibyte', b'\xc3\xa9\n\xf0\x9f\x99\x82\r\nZ',
     b'{"lines":[{"end":3,"sha256":"edd3a863872a04239eb29ad4bc12fc892b3d4ae57cc7e786a3697816f8e141c2","start":0},{"end":9,"sha256":"f6a9d5888070c5e4ed7df32b38b59518898fd82800dad89bdf6e21be61771033","start":3},{"end":10,"sha256":"bbeebd879e1dff6918546dc0c179fdde505f2a21591c9a9c96e36b054ec5af83","start":9}],"schema_version":1,"source_byte_length":10,"source_sha256":"64adf4f2a2794d4e91dbf5ec5769d68726ce30f796a88dc78eb7e89532895812"}',
     '4d41192be1eee991027dabb71fe9263fba5e52de17240e950daca8fe84e6a73f'),
    ('combined_lf', b'\nA\n\nB\n',
     b'{"lines":[{"end":1,"sha256":"01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b","start":0},{"end":3,"sha256":"06f961b802bc46ee168555f066d28f4f0e9afdf3f88174c1ee6f9de004fc30a0","start":1},{"end":4,"sha256":"01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b","start":3},{"end":6,"sha256":"c0cde77fa8fef97d476c10aad3d2d54fcc2f336140d073651c2dcccf1e379fd6","start":4}],"schema_version":1,"source_byte_length":6,"source_sha256":"43086c481c73084831d6cc8aa448792aecf4a74a5272134499eb01ef2240f37a"}',
     'fc0ec2676d5ddf9bc6168317880622a239ef60f0df54aef2cca1a5af9eeef819'),
    ('noneligible_raw_bytes', b'\xff\x00\r',
     b'{"lines":[{"end":3,"sha256":"eb5de5f7d01dd4a4e886385d2d3557d3da8b638330c5e85d65c43dd02876ee43","start":0}],"schema_version":1,"source_byte_length":3,"source_sha256":"eb5de5f7d01dd4a4e886385d2d3557d3da8b638330c5e85d65c43dd02876ee43"}',
     '5c567e5ce000d1e97b04ca55d036f3b9e2ce1207eb7f70bf76488fe707807484'),
)

# source, source SHA256, artifact bytes, artifact SHA256, physical line count
CAPACITY_CONTROLS = (
    ('max_source', b'x' * 8192,
     '18f8d2eb4a387bbc1e37ec099a7326805739bc9c99ecf0f14b808a5bcb65bf49', 238,
     '550fa95f5b616470562b45a5c283677d1b079f9eeef9dbdfdba8938b5b0bf39b', 1),
    ('selected_size_and_line_bound', b'a\n' * 128,
     'd2014ce4cd9816772e4b27433e58705b55d55c7f8773785762c19512381e30a5', 12830,
     '6704b136d694fb0eddede7b493266c0f16b0cc337903bceb653bb41e545ab6e8', 128),
    ('noneligible_129_lines', b'a\n' * 129,
     'e9a7c314fc84d41af76b1b02192903d46e4123add0d99ef95466dfaee21cf2d1', 12930,
     'cc63f313954e14e38c1073a3d85951dd04f3817dae5adb025497b119f97411a0', 129),
    ('artifact_65532', b'x' * 3 + b'\n' * 656,
     '9e4f86867987a8cf64afd376b7e97da15edb649f463cf5cd2e871b9011cabf7f', 65532,
     '1d9451662ac2aab800b69966e6fa0a7aa5c98393d9795408f94402a2cda45840', 656),
    ('artifact_65536', b'x' * 4 + b'\n' * 656,
     '37a9578da288064e5fd5a74ddce03f52fd94ae8d56fcc6ceff7cf853638742b6', 65536,
     '14be988cf777dabdc75261e81eacedd6d147941097bcdb42e5d3dc55781bfa9b', 656),
    ('artifact_65540', b'x' * 5 + b'\n' * 656,
     'd699a32c00bbb0b38c893ad574caef3614b34ebc35f2a0a611f02d71dc30815b', 65540,
     '118c7543f8aa044df25d795379500301adec323cd1977f1f8e8b0addc2056dde', 656),
)


class ProducerTests(unittest.TestCase):
    def test_literal_bytes_and_artifact_identities(self):
        for name, source, expected, artifact_hash in LITERAL_CONTROLS:
            with self.subTest(name=name):
                actual = produce_line_index(source)
                self.assertIs(type(actual), bytes)
                self.assertEqual(actual, expected)
                self.assertEqual(hashlib.sha256(actual).hexdigest(), artifact_hash)

    def test_exact_fields_types_and_canonical_form(self):
        for name, source, expected, _ in LITERAL_CONTROLS:
            with self.subTest(name=name):
                artifact = produce_line_index(source)
                fields = json.loads(artifact)
                self.assertEqual(set(fields), {'schema_version', 'source_sha256', 'source_byte_length', 'lines'})
                self.assertIs(type(fields['schema_version']), int)
                self.assertEqual(fields['schema_version'], 1)
                self.assertIs(type(fields['source_byte_length']), int)
                self.assertEqual(fields['source_byte_length'], len(source))
                self.assertEqual(fields['source_sha256'], hashlib.sha256(source).hexdigest())
                self.assertIs(type(fields['lines']), list)
                for row in fields['lines']:
                    self.assertEqual(set(row), {'start', 'end', 'sha256'})
                    self.assertIs(type(row['start']), int)
                    self.assertIs(type(row['end']), int)
                    self.assertIs(type(row['sha256']), str)
                self.assertFalse(artifact.startswith(b'\xef\xbb\xbf'))
                self.assertFalse(artifact.endswith(b'\n'))
                self.assertEqual(artifact, json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8'))

    def test_deterministic_repeated_calls(self):
        for _, source, expected, _ in reversed(LITERAL_CONTROLS):
            self.assertEqual(produce_line_index(source), expected)
            self.assertEqual(produce_line_index(source), expected)

    def test_capacity_exact_source_and_artifact_boundaries(self):
        self.assertEqual(SOURCE_BYTE_LIMIT, 8192)
        self.assertEqual(ARTIFACT_BYTE_LIMIT, 65536)
        for name, source, source_hash, expected_size, artifact_hash, count in CAPACITY_CONTROLS:
            with self.subTest(name=name):
                if expected_size > 65536:
                    with self.assertRaisesRegex(ProducerRefusal, '^artifact byte limit exceeded$'):
                        produce_line_index(source)
                    continue
                artifact = produce_line_index(source)
                self.assertEqual(len(artifact), expected_size)
                self.assertEqual(hashlib.sha256(artifact).hexdigest(), artifact_hash)
                fields = json.loads(artifact)
                self.assertEqual(fields['source_sha256'], source_hash)
                self.assertEqual(fields['source_byte_length'], len(source))
                self.assertEqual(len(fields['lines']), count)

    def test_refusals_leave_no_returned_partial_artifact(self):
        for source, reason in [(b'x'*8193, 'source byte limit exceeded'),
                               (b'\n'*8192, 'artifact byte limit exceeded')]:
            result = None
            with self.subTest(reason=reason):
                with self.assertRaises(ProducerRefusal) as caught:
                    result = produce_line_index(source)
                self.assertIsNone(result)
                self.assertEqual(str(caught.exception), reason)
                self.assertLess(len(str(caught.exception)), 64)
        self.assertEqual(produce_line_index(b''), LITERAL_CONTROLS[1][2])

    def test_wrong_types_and_bytes_subclass_are_rejected(self):
        class BytesSubclass(bytes):
            def __len__(self):
                raise AssertionError('user method must not be called')
        class Unknown:
            def __repr__(self):
                raise AssertionError('user repr must not be called')
        for value in [None, '', 'abc', 0, True, bytearray(b'abc'), memoryview(b'abc'),
                      [], {}, BytesSubclass(b'abc'), Unknown()]:
            with self.subTest(type=type(value).__name__):
                with self.assertRaisesRegex(TypeError, '^source must be built-in bytes$'):
                    produce_line_index(value)

    def test_processing_does_not_establish_selection_eligibility(self):
        # Empty, short, malformed UTF-8/NUL and >128-line sources are processable
        # boundary controls. None is an eligible selected public repository blob.
        for index in (0,1,9):
            _, source, expected, _ = LITERAL_CONTROLS[index]
            self.assertEqual(produce_line_index(source), expected)
        source = b'a\n' * 129
        self.assertEqual(len(json.loads(produce_line_index(source))['lines']), 129)


if __name__ == '__main__':
    unittest.main()
