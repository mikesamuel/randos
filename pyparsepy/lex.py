"""
A lexer for Python.
"""

import re

## Lexical definitions
## per https://docs.python.org/3/reference/lexical_analysis.html

DQ3_STRING = r'\"\"\"(?:[^\\\"]|\\.|\"(?!\"\"))*\"{0,3}'
SQ3_STRING = r"\'\'\'(?:[^\\\']|\\.|\'(?!\'\'))*\'{0,3}"
DQ1_STRING = r'\"(?!\"\")(?:[^\\\"\r\n]|\\.)*\"?'
SQ1_STRING = r"\'(?!\'\')(?:[^\\\'\r\n]|\\.)*\'?"
STRING_PREFIX = r'(?i:[bf]r?|r[bf]?|u)?'

STRING = r'%s(?:%s)' % (
    STRING_PREFIX,
    '|'.join((DQ3_STRING, SQ3_STRING, DQ1_STRING, SQ1_STRING))
)
COMMENT = r'#(?:[^\\\n\r]|\\.)*'

ID_START = r'[A-Za-z_]'  # TODO \p{xid_start}
ID_CONTINUE = r'[A-Za-z_0-9]'  # TODO \p{xid_continue}
# Words = Identifiers + keywords
WORD = r'%s%s*' % (ID_START, ID_CONTINUE)

# Lexer should never find a word adjacent to a number as in '123i',
# so define numbers as something that starts like a number followed
# by soup.
NUMBER = '(?:%s)' % '|'.join((
    # 'e' in hex does not start exponent
    # ID_CONTINUE covers '_' as myriad separator
    r'0[BOXbox]%s*' % ID_CONTINUE,
    (
        # integer optional-Fraction | dot mandatory-fraction
        r'(?:[0-9]%(no_e)s*(?:[.]%(no_e)s*)|[.][0-9]%(no_e)s*)'
        # optional exponent with sign, identifier soup
        r'(?:[eE][+\-]%(any)s*)?%(any)s'
    ) % {
        'no_e': r'(?![eE])%s' % ID_CONTINUE,
        'any': ID_CONTINUE
    }
    # Soup also covers imaginary numbers.
))

PUNCTUATORS = [
    '+', '-', '*', '**', '/', '//', '%', '@',
    '<<', '>>', '&', '|', '^', '~',
    '<', '>', '<=', '>=', '==', '!=',
    '(', ')', '[', ']', '{', '}',
    ',', ':', '.', ';', '@', '=', '->',
    '+=', '-=', '*=', '/=', '//=', '%=', '@=',
    '&=', '|=', '^=', '>>=', '<<=', '**=',
]
PUNCTUATORS.sort(key=len, reverse=True)
PUNCTUATION = r'(?:%s)' % '|'.join(
    [re.escape(x) for x in PUNCTUATORS]
)

BREAKING_WHITESPACE = r'(?:\n|\r\n?)'
NON_BREAKING_WHITESPACE = r'(?:[\t\x0c\x20]|\\%s)+' % (BREAKING_WHITESPACE,)

BREAKS = ('\n', '\r', '\r\n')

EXPLICIT_LINE_PATTERN = re.compile(
    r'(?:%s)+%s?|%s' % (
        '|'.join((
            r'[^\"\'#\r\n\\]',
            STRING,
            COMMENT,
            r'[\\]%s?' % BREAKING_WHITESPACE,
        )),
        BREAKING_WHITESPACE,
        BREAKING_WHITESPACE,
    ),
    re.DOTALL
)

INDENTING_WHITESPACE_PATTERN = re.compile(r'^[\t\x20]+')

TOKEN_PATTERN = re.compile(
    '(?:%s)' % '|'.join((
        NON_BREAKING_WHITESPACE,
        BREAKING_WHITESPACE,
        COMMENT,
        STRING,
        WORD,
        NUMBER,
        PUNCTUATION,
        # Ensure that tokenization is a true partition of input.
        # TODO: what does '.' do for orphaned surrogates?
        r'.',
    )),
    re.DOTALL
)

def logical_lines(source_text):
    """
    A series of logical lines for a Python source text.

    source_text:
      Assumes bytes already decoded per any encoding declaration.

    Logical lines are already partitioned into tokens.
    """

    open_bracket_count = 0
    logical_line = []
    for match in EXPLICIT_LINE_PATTERN.finditer(source_text):
        phys_line = match.group(0)
        tokens = TOKEN_PATTERN.findall(phys_line)

        # DIFFERENCE FROM SPEC
        if open_bracket_count:
            # For error recovery, reset bracket count
            # on keywords that can't appear in parentheses.
            for tok in tokens:
                if tok in ('if', 'def', 'class', 'import', 'else', 'elif'):
                    open_bracket_count = 0
                    if logical_line:
                        yield logical_line
                        logical_line = []
                    break
                elif tok[0] not in (' ', '\t'):
                    break

        for tok in tokens:
            if tok in ('(', '[', '{'):
                open_bracket_count += 1
            elif tok in ('}', ']', ')'):
                open_bracket_count = max(
                    0,
                    open_bracket_count - 1)

        logical_line.extend(tokens)
        if not open_bracket_count:
            if logical_line:
                yield logical_line
                logical_line = []

    if logical_line:
        yield logical_line

class Token:
    """
    A source text token and metadata
    """

    INDENT_TEXT = '>>>'
    DEDENT_TEXT = '<<<'

    def __init__(self, tok, left, right, special=False):
        assert isinstance(tok, str)
        assert isinstance(left, int) and isinstance(right, int)
        assert left <= right
        assert isinstance(special, bool)

        self.tok = tok
        self.left = left
        self.right = right
        self.special = special

    def __str__(self):
        return self.tok

    def __repr__(self):
        return (
            'Token(%r, %d, %d, True)' if self.special else
            'Token(%r, %d, %d)'
        ) % (self.tok, self.left, self.right)

def indentation_value(spaces):
    """
    Given an indentation string of spaces and tabs,
    returns the equivalent number of spaces per Python
    indentation rule.
    """
    value = 0
    for char in spaces:
        value += (8 - (value % 8)) if char == '\t' else 1
    return value

def is_code_token(text):
    """
    True for non-comment, non-whitespace token text.
    """
    char0 = text[0]
    return char0 != '#' and char0 > ' ' and char0 != '\\'

def lex(source_text):
    """
    Tokenizes a Python source text.

    source_text:
      Assumes bytes already decoded per any encoding declaration.
    """

    indent_stack = [('', 0)]  # text, value
    char_pos = 0

    for logical_line in logical_lines(source_text):
        num_tokens = len(logical_line)
        assert num_tokens
        bracket_depth = 0

        # If there are no code tokens, we don't push indent/dedent tokens.
        has_code_token = False
        for i in range(num_tokens - 1, -1, -1):
            if is_code_token(logical_line[i]):
                has_code_token = True
                break

        # Indent/dedent as appropriate
        if has_code_token:
            indentation = INDENTING_WHITESPACE_PATTERN.search(logical_line[0])
            indentation = indentation.group(0) if indentation else ''
            value = indentation_value(indentation)
            (_, top_value) = indent_stack[-1]
            if top_value < value:
                indent_stack.append((indentation, value))
                yield Token(Token.INDENT_TEXT, char_pos, char_pos, True)
            else:
                # TODO: if same, check whether IndentError needed
                while top_value > value:
                    indent_stack[-1:] = []
                    yield Token(Token.DEDENT_TEXT, char_pos, char_pos, True)
                    (_, top_value) = indent_stack[-1]

        # Wrap string as tokens
        for i in range(0, num_tokens):
            text = logical_line[i]
            if not is_code_token(text):
                continue
            right = char_pos + len(text)
            yield Token(text, char_pos, right)
            char_pos = right
            # but in keyword
            if text in ('(', '[', '{'):
                bracket_depth += 1
            elif text in ('}', ']', ')'):
                bracket_depth = max(0, bracket_depth - 1)

        # Emit line breaks that separate logical lines.
        # This allows interpreting '\n' as a statement separator.
        if has_code_token:
            left = char_pos
            if text in BREAKS:
                left = char_pos - len(text)
            yield Token('\n', left, char_pos)

    for (_, indent_value) in indent_stack:
        if indent_value:
            yield Token(Token.DEDENT_TEXT, char_pos, char_pos, True)


# Merge multi-word operators `is not` and `not in`.
TOKEN_MERGE_TRIE = {
    'is': {
        'not': True,
    },
    'not': {
        'in': True,
    },
}

def preparse(tokens):
    """
    Given a stream of Tokens, produces a stream of Tokens ready for parse.
    """
    last_token = None
    delayed = []
    trie = TOKEN_MERGE_TRIE
    for token in tokens:
        if token.tok == '\n' and last_token in (None, '\n', Token.INDENT_TEXT, ':'):
            # Ignore newlines that can't separate statements because they
            # follow a ':' terminated flow control construct, are at the
            # start of a block ('>>>'), at the start of input (None), or
            # are part of a reundant blank line ('\n').
            continue

        if token.tok in trie:
            trie = trie[token.tok]
            delayed.append(token)
            if isinstance(trie, bool) and trie:
                token = Token(
                    ' '.join(x.tok for x in delayed),
                    min(x.left     for x in delayed),
                    max(x.right    for x in delayed))
                delayed.clear()
                trie = TOKEN_MERGE_TRIE
            else:
                continue
        elif delayed:
            for delayed_token in delayed:
                yield delayed_token
            delayed.clear()
            trie = TOKEN_MERGE_TRIE

        yield token
        last_token = token.tok

    for delayed_token in delayed:
        yield delayed_token
