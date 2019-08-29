"""
Defines operators for python, and an operator precedence function.
"""

from lex import Token

BRACKET_PAIRS = {
    '(':   ')',
    '[':   ']',
    '{':   '}',
    '>>>': '<<<',
}

OPEN_BRACKETS = tuple(BRACKET_PAIRS.keys())
CLOSE_BRACKETS = tuple(BRACKET_PAIRS.values())


INFIX = 'INFIX'
POSTFIX = 'POSTFIX'
PREFIX = 'PREFIX'
TOKEN = 'TOKEN'

LEFT = 'LEFT'
RIGHT = 'RIGHT'

class Operator:
    """
    Information about a programming language operator.
    """
    def __init__(self, tok, kind, prec, assoc=None, followers=()):
        self.tok = tok
        self.kind = kind
        self.prec = prec
        self.assoc = kind == INFIX and (assoc or LEFT) or None
        self.followers = tuple(followers)

    def __str__(self):
        return 'Operator(%r, %s)' % (self.tok, self.kind)

    def __repr__(self):
        return 'Operator(%r, %r)' % (self.tok, self.kind)

class OperatorStackElement:
    """
    A parse tree node in the process of being built.
    See parse.py.
    """

    def __init__(self, op):
        self.op = op
        self.node = []
        self.left = None
        self.right = None

    def __str__(self):
        return 'OSE(%r)' % self.node

    def __repr__(self):
        return 'OSE(op=%r, node=%r)' % (self.op, self.node)

OPERATORS = (
    Operator('else', INFIX, -4, assoc=RIGHT),
    Operator('elif', INFIX, -4, assoc=RIGHT),
    Operator('except', INFIX, -4, assoc=RIGHT),
    Operator('finally', INFIX, -4, assoc=RIGHT),

    Operator('>>>', INFIX, -3, assoc=RIGHT),

    Operator('def', PREFIX, -2),
    Operator('for', PREFIX, -2),
    Operator('if', PREFIX, -2),
    Operator('assert', PREFIX, -2),
    Operator('return', PREFIX, -2),
    Operator('while', PREFIX, -2),
    Operator('yield', PREFIX, -2),
    Operator('\n', POSTFIX, -2),

    Operator(':', INFIX, -1, assoc=RIGHT),
    Operator(':', PREFIX, -1),

    Operator(',', INFIX, 0, assoc=RIGHT),

    Operator('for', INFIX, 1, followers=('in',)),
    Operator('=', INFIX, 1, assoc=RIGHT),
    Operator('+=', INFIX, 1, assoc=RIGHT),
    Operator('-=', INFIX, 1, assoc=RIGHT),
    Operator('*=', INFIX, 1, assoc=RIGHT),
    Operator('/=', INFIX, 1, assoc=RIGHT),
    Operator('//=', INFIX, 1, assoc=RIGHT),
    Operator('%=', INFIX, 1, assoc=RIGHT),
    Operator('@=', INFIX, 1, assoc=RIGHT),
    Operator('&=', INFIX, 1, assoc=RIGHT),
    Operator('|=', INFIX, 1, assoc=RIGHT),
    Operator('^=', INFIX, 1, assoc=RIGHT),
    Operator('>>=', INFIX, 1, assoc=RIGHT),
    Operator('<<=', INFIX, 1, assoc=RIGHT),
    Operator('**=', INFIX, 1, assoc=RIGHT),

    # Special cased below since lambda can contain commas to separate formals.
    Operator('lambda', PREFIX, 2, followers=(':',)),

    Operator('if', INFIX, 3, followers=('else',)),
    Operator('or', INFIX, 4),
    Operator('and', INFIX, 5),
    Operator('not', PREFIX, 6),

    Operator('in', INFIX, 7),
    Operator('is', INFIX, 7),
    Operator('not in', INFIX, 7),
    Operator('is not', INFIX, 7),
    Operator('<', INFIX, 7),
    Operator('<=', INFIX, 7),
    Operator('>', INFIX, 7),
    Operator('>=', INFIX, 7),
    Operator('==', INFIX, 7),
    Operator('!=', INFIX, 7),

    Operator('|', INFIX, 8),

    Operator('^', INFIX, 9),

    Operator('&', INFIX, 10),

    Operator('<<', INFIX, 11),
    Operator('>>', INFIX, 11),

    Operator('+', INFIX, 12),
    Operator('-', INFIX, 12),

    Operator('*', INFIX, 13),
    Operator('@', INFIX, 13),
    Operator('/', INFIX, 13),
    Operator('//', INFIX, 13),
    Operator('%', INFIX, 13),

    Operator('+', PREFIX, 14),
    Operator('-', PREFIX, 14),
    Operator('~', PREFIX, 14),

    Operator('**', INFIX, 15),

    Operator('await', PREFIX, 16),

    Operator('[', INFIX, 17),
    Operator('(', INFIX, 17),
    Operator('.', INFIX, 17),

    Operator('[', PREFIX, 18),
    Operator('(', PREFIX, 18),
    Operator('{', PREFIX, 18),
)

ROOT_OPERATOR = Operator('', PREFIX, -100)
NOT_AN_OPERATOR = Operator(None, TOKEN, 100)

def is_nullary(stack_el):
    """
    True for stack elements that consist solely of a zero argument operator.
    """
    return False

def open_bracket_count(stack_el, result_if_negative=None):
    """
    The count of open brackets minus the count of close brackets.

    If any prefix of the stack_el's nodes contains more close brackets
    than open, and result_if_negative is not None, returns that.
    """
    if stack_el.op.tok == 'lambda':
        # Not closeable until ':' seen.
        count = 1
        for child in stack_el.node:
            if isinstance(child, Token) and child.tok == ':':
                count = 0
                break
        return count
    if stack_el.op.tok not in OPEN_BRACKETS:
        return 0
    count = 0
    for child in stack_el.node:
        if isinstance(child, Token):
            tok = child.tok
            if tok in CLOSE_BRACKETS:
                count -= 1
                if count < 0 and result_if_negative is not None:
                    return result_if_negative
            elif tok in OPEN_BRACKETS:
                count += 1
    return count

def needs_close_bracket(stack_el):
    """
    A node "needs" a close bracket if it has an open bracket like '('
    without a corresponding ')'.

    This tests whether the count of open brackets exceeds the count
    of close brackets without worrying about whether open parenthesis ('(')
    pairs properly close square (']').

    For example, these need a close
      foo(x   // An incomplete application of an infix bracket operator
      [       // An incomplete prefix bracket operation
      { stmt  // Another incomplete prefix bracket operation with one operand.
    but these do not
      foo(x)
      []
      { stmt }
      [ 0 , 1 )
      ( ) )   // Extra closed does not need a close
    """
    return open_bracket_count(stack_el) > 0

def init():
    """
    Defines a scope for side-tables for operator functions.
    """
    grouped_operators = {}
    follower_map = {}
    for operator in OPERATORS:
        key = (operator.tok, operator.kind)
        if key not in grouped_operators:
            grouped_operators[key] = []
        grouped_operators[key].append(operator)
        for follower in operator.followers:
            if follower not in follower_map:
                follower_map[follower] = set()
            follower_map[follower].add(operator)

    for key in grouped_operators:
        grouped_operators[key] = tuple(grouped_operators[key])

    def can_nest(outer, inner):
        """
        True iff the operator stack element, inner, can nest in
        the operator stack element, outer.
        """

        # Special case lambda to allow commas between formal parameters
        if (outer.op.tok == 'lambda' and open_bracket_count(outer) > 0
                and inner.op.tok == ','):
            return True

        if inner.op is ROOT_OPERATOR:
            return False
        if outer.op.tok in OPEN_BRACKETS and outer.node:
            return needs_close_bracket(outer)
        if outer.op.prec < inner.op.prec:
            return True
        if (outer.op.prec == inner.op.prec
                and (outer.op.assoc != RIGHT
                     or inner.op.kind == INFIX and not inner.node)):
            return True
        return False

    def lookup_operators(tok, kind):
        """
        A list of operators with the given token text and kind.
        """
        return grouped_operators.get((tok, kind), ())

    def followed_by(tok):
        """
        A maximal set of operators, o, such that tok in o.followers.
        """
        return follower_map.get(tok, ())

    return can_nest, lookup_operators, followed_by

can_nest, lookup_operators, followed_by = init()
