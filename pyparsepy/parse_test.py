import unittest
import json

from lex import Token, lex, preparse
from parse import InnerNode, parse

class ParseTreeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, InnerNode):
            return o.children
        if isinstance(o, Token):
            return o.tok
        return json.JSONEncoder.default(self, o)


class ParseTest(unittest.TestCase):
    def assert_tree(self, source_text, want):
        tokens = preparse(lex(source_text))
        parse_tree = parse(tokens)
        got = json.loads(json.dumps(parse_tree, cls=ParseTreeEncoder))
        self.assertEqual(got, want)

    def test_none(self):
        self.assert_tree('', [])
        self.assert_tree(' ', [])

    def test_pass(self):
        self.assert_tree('pass', [['pass'], '\n'])

    def test_if(self):
        self.assert_tree(
            'if x:\n\tpass',
            [
                [
                    'if',
                    [
                        ['x'],
                        ':'
                    ],
                ],
                '>>>',
                [['pass'], '\n'],
                '<<<',
            ],
        )

    def test_if_one_line(self):
        self.assert_tree(
            'if x: pass',
            [
                [
                    'if',
                    [
                        ['x'],
                        ':',
                        ['pass'],
                    ],
                ],
                '\n',
            ]
        )

    def test_if_else(self):
        self.assert_tree(
            '''
if x:
    f()
else:
    g()
''',
            [
                [
                    [
                        'if',
                        [
                            ['x'],
                            ':',
                        ],
                    ],
                    '>>>',
                    [
                        [['f'], '(', ')'],
                        '\n',
                    ],
                    '<<<',
                ],
                'else',
                [
                    [':'],
                    '>>>',
                    [
                        [['g'], '(', ')'],
                        '\n',
                    ],
                    '<<<',
                ],
            ]
        )

    def test_if_elif(self):
        self.assert_tree(
            '''
if not x:

    f()

elif y():

    z = g()

    # Comment
    z += 1

''',
            [
                [
                    [
                        'if',
                        [
                            ['not', ['x']],
                            ':',
                        ],
                    ],
                    '>>>',
                    [
                        [['f'], '(', ')'],
                        '\n',
                    ],
                    '<<<',
                ],
                'elif',
                [
                    [[['y'], '(', ')'], ':'],
                    '>>>',
                    [[['z'], '=', [['g'], '(', ')']], '\n'],
                    [[['z'], '+=', ['1']], '\n'],
                    '<<<',
                ],
            ]
        )

    def test_lambda_in_actuals_list(self):
        self.assert_tree(
            'f(a, lambda b, c: b+c, d)',
            [
                [
                    ['f'],
                    '(',
                    [
                        ['a'],
                        ',',
                        [
                            [
                                'lambda',
                                [
                                    ['b'],
                                    ',',
                                    ['c'],
                                ],
                                ':',
                                [
                                    ['b'],
                                    '+',
                                    ['c'],
                                ],
                            ],
                            ',',
                            ['d'],
                        ],
                    ],
                    ')',
                ],
                '\n',
            ],
        )

    def test_multi_word_operators(self):
        self.assert_tree(
            'x not in y and w is not z',
            [
                [
                    [
                        ['x'],
                        'not in',
                        ['y'],
                    ],
                    'and',
                    [
                        ['w'],
                        'is not',
                        ['z'],
                    ],
                ],
                '\n',
            ]
        )
        self.assert_tree(
            '''(
  x not # at all
    in y
  and
  w is # really
    not z
)''',
            [
                [
                    '(',
                    [
                        [
                            ['x'],
                            'not in',
                            ['y'],
                        ],
                        'and',
                        [
                            ['w'],
                            'is not',
                            ['z'],
                        ],
                    ],
                    ')',
                ],
                '\n',
            ]
        )

if __name__ == '__main__':
    unittest.main()
