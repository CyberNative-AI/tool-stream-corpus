import unittest
from streamcheck import SSE, probe, reference_events


class SSETests(unittest.TestCase):
    def test_utf8_bom_crlf_multidata(self):
        blob = '\ufeff: heartbeat\r\ndata: α\r\ndata: β\r\n\r\n'.encode()
        decoder = SSE()
        for b in blob:
            decoder.feed(bytes([b]))
        self.assertEqual(decoder.finish(), ['α\nβ'])
        self.assertEqual(reference_events(blob), ['α\nβ'])

    def test_eof_cannot_finish_event(self):
        decoder = SSE()
        decoder.feed(b'data: partial\n')
        self.assertEqual(decoder.finish(), [])

    def test_invalid_utf8_refuses(self):
        self.assertEqual(probe([b'data: \xff\n\n'])['error'], 'UnicodeDecodeError')

    def test_bare_cr(self):
        decoder = SSE()
        decoder.feed(b'data: first\r\rdata: second\r\r')
        self.assertEqual(decoder.finish(), ['first', 'second'])


if __name__ == '__main__':
    unittest.main()
