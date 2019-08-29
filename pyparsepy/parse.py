"""
An operator precedence parser.
"""

from lex import Token
from ops import can_nest, lookup_operators, followed_by, \
    needs_close_bracket, is_nullary, \
    OperatorStackElement, Operator, \
    BRACKET_PAIRS, CLOSE_BRACKETS, ROOT_OPERATOR, NOT_AN_OPERATOR, \
    POSTFIX, INFIX, PREFIX

class InnerNode:
    """
    An inner parse tree node.
    Leaves must be tokens
    """

    def __init__(self, children, op, left, right):
        self.children = tuple(children)
        self.op = op
        self.left = left
        self.right = right

        assert isinstance(self.op, Operator)
        assert isinstance(self.left, int)
        assert isinstance(self.right, int)
        for child in self.children:
            assert isinstance(child, (InnerNode, Token))

    def __repr__(self):
        return repr(self.children)


def parse(tokens):
    """
    Given tokens, returns a parse tree such that the leaves in a prefix
    traversal produce the same sequence of tokens.
    """
    stack = [
        OperatorStackElement(ROOT_OPERATOR),
    ]

    def commit_to(depth):
        n = len(stack)
        while n > depth:
            add_node_to(stack[n - 1], stack[n - 2])
            n -= 1
        stack[depth:] = []

    def add_node_to(el, parent):
        update_position_metadata(parent, el.left, el.right)
        parent.node.append(InnerNode(
            el.node,
            op=el.op,
            left=el.left,
            right=el.right
        ))

    def add_token_to(token, el):
        el.node.append(token)
        update_position_metadata(el, token.left, token.right)

    def update_position_metadata(el, left, right):
        if el.left is None:
            el.left = left
        else:
            el.left = min(el.left, left)
        if el.right is None:
            el.right = right
        else:
            el.right = max(el.right, right)

    for token in tokens:
        tok = token.tok
        used_token = False

        follows = followed_by(tok)
        if follows:
            for i in range(len(stack) - 1, -1, -1):
                el = stack[i]
                op = el.op
                node = el.node
                if op in follows:
                    tok_index = index_of_token(node, op.tok)
                    max_follower_seen = -1
                    for fi in range(0, len(op.followers)):
                        follower = op.followers[fi]
                        ti = index_of_token(node, follower, tok_index + 1)
                        if ti >= 0:
                            max_follower_seen = fi
                            tok_index = ti
                    fip = (
                        op.followers.index(tok, max_follower_seen + 1)
                        if tok in op.followers[max_follower_seen+1:] else None)
                    if fip is not None:
                        commit_to(i + 1)
                        add_token_to(token, el)
                        used_token = True
                        break
                if needs_close_bracket(el):
                    break
        if used_token: continue

        if tok in CLOSE_BRACKETS:
            for i in range(len(stack) - 1, -1, -1):
                el = stack[i]
                partner = BRACKET_PAIRS.get(el.op.tok)
                if tok == partner and needs_close_bracket(el):
                    commit_to(i + 1)
                    add_token_to(token, el)
                    used_token = True
                    break
        if used_token: continue

        for op_kind in (POSTFIX, INFIX):
            if used_token: break
            for op in lookup_operators(tok, op_kind):
                left_depth = None
                candidate = OperatorStackElement(op)
                for i in range(len(stack) - 1, -1, -1):
                    el = stack[i]
                    if needs_close_bracket(el): break
                    if (can_nest(candidate, el)
                            and i
                            and can_nest(
                                stack[i - 1],
                                candidate)):
                        left_depth = i
                if left_depth is not None:
                    el = stack[left_depth]
                    commit_to(left_depth + 1)
                    add_node_to(el, candidate)
                    add_token_to(token, candidate)
                    stack[left_depth] = candidate
                    used_token = True
                    break
        if used_token: continue

        for op in lookup_operators(tok, PREFIX):
            if used_token: break
            candidate = OperatorStackElement(op)
            add_token_to(token, candidate)
            for i in range(len(stack) - 1, -1, -1):
                el = stack[i]
                node = el.node
                stackop = el.op
                if stackop.kind != POSTFIX and can_nest(el, candidate):
                    commit_to(i + 1)
                    stack.append(candidate)
                    used_token = True
                    break
        if used_token: continue

        candidate = OperatorStackElement(NOT_AN_OPERATOR)
        add_token_to(token, candidate)
        close_to = None
        for i in range(len(stack) - 1, -1, -1):
            el = stack[i]
            if el.op.kind != POSTFIX and can_nest(el, candidate):
                break
            close_to = i
        if close_to is not None:
            commit_to(close_to)

        top = stack[-1]
        if top.op is NOT_AN_OPERATOR and not is_nullary(top):
            add_token_to(token, top)
        else:
            stack.append(candidate)

    commit_to(1)
    if len(stack[0].node) == 1 and isinstance(stack[0].node[0], InnerNode):
        return stack[0].node[0]
    return InnerNode(
        stack[0].node,
        ROOT_OPERATOR,
        stack[0].left or 0,
        stack[0].right or 0)

def index_of_token(children, tok, start=0):
    for i in range(start, len(children)):
        child = children[i]
        if isinstance(child, Token) and tok == child.tok:
            return i
    return -1


if __name__ == '__main__':
    import json
    import sys
    from lex import lex, preparse

    def main():
        source_text = sys.stdin.read()

        tokens = preparse(lex(source_text))

        parse_tree = parse(tokens)

        class ParseTreeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, InnerNode):
                    return o.children
                if isinstance(o, Token):
                    return o.tok
                return json.JSONEncoder.default(self, o)
        print(json.dumps(parse_tree, cls=ParseTreeEncoder, indent=2))
    main()
