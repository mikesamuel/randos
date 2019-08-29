import unittest

from lex import lex, logical_lines, preparse

class LogicalLinesTest(unittest.TestCase):
    def test_none(self):
        self.assertEqual(
            [],
            list(logical_lines('')))

    def test_some(self):
        source_text = r'''

# comment

foo \
bar
a = """
  multiline string
"""%()
b(
  c)
d e

'''
        got = list(logical_lines(source_text))
        self.assertEqual(
            got,
            [
                ['\n'],
                ['\n'],
                ['# comment', '\n'],
                ['\n'],
                ['foo', ' \\\n', 'bar', '\n'],
                ['a', ' ', '=', ' ', '"""\n  multiline string\n"""',
                 '%', '(', ')', '\n'],
                ['b', '(', '\n', '  ', 'c', ')', '\n'],
                ['d', ' ', 'e', '\n'],
                ['\n'],
            ])

    def test_bracket_recovery(self):
        self.assertEqual(
            [
                ['f', '(', '\n', '\n'],
                ['def', ' ', 'f', '(', ')', ':', '\n'],
                [' ', 'pass'],
            ],
            list(logical_lines('f(\n\ndef f():\n pass')))


class LexTest(unittest.TestCase):
    def assert_tokens(self, inp, want):
        got = [x.tok for x in preparse(lex(inp))]
        self.assertEqual(got, want)

    def test_none(self):
        self.assert_tokens('', [])

    def test_one_line(self):
        self.assert_tokens(
            'foo()',
            ['foo', '(', ')', '\n'])

    def test_dedent_on_unterminated_line(self):
        self.assert_tokens(
            'def f():\n\tpass',
            ['def', 'f', '(', ')', ':',
             '>>>', 'pass', '\n', '<<<']
        )
    def test_dedent_before_following_line(self):
        self.assert_tokens(
            'def f():\n\tif True:\n\t\tpass\nf()',
            ['def', 'f', '(', ')', ':',
             '>>>', 'if', 'True', ':',
             '>>>', 'pass', '\n', '<<<', '<<<',
             'f', '(', ')', '\n']
        )

if __name__ == '__main__':
    unittest.main()
