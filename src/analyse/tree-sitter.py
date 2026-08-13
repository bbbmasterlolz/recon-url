import sys
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_javascript

# Tree-sitter setup
JS_LANGUAGE = Language(tree_sitter_javascript.language())
parser = Parser(JS_LANGUAGE)


# ============================================================
# Helpers
# ============================================================

def text(node, source):
    return source[node.start_byte:node.end_byte].decode(
        "utf-8",
        errors="replace",
    )


def strip_quotes(value):
    if len(value) >= 2:
        if value[0] == value[-1] and value[0] in ("'", '"', "`"):
            return value[1:-1]

    return value


# Placeholder for any expression we cannot statically resolve.
PLACEHOLDER = "{var}"


# ============================================================
# Resolve JavaScript expression
# ============================================================

def resolve(node, source, constants, seen=None):
    """
    Recursively resolve a JavaScript expression into a string.

    1. Replace identifiers with their constant values (recursive).
    2. Statically concatenate via binary `+`.
    3. Expand template literals with ${...} substitutions.

    Anything that cannot be resolved is replaced with {var}.
    """

    if seen is None:
        seen = set()

    # --------------------------------------------------------
    # String literal        "hello"  'hello'
    # --------------------------------------------------------

    if node.type == "string":

        return strip_quotes(text(node, source))


    # --------------------------------------------------------
    # Template string       `${BASE}/users/${ID}`
    # --------------------------------------------------------

    if node.type == "template_string":

        result = ""

        for child in node.named_children:

            if child.type in ("template_chars", "string_fragment"):

                result += text(child, source)

            elif child.type == "template_substitution":

                expressions = child.named_children

                if expressions:

                    result += resolve(
                        expressions[0],
                        source,
                        constants,
                        seen,
                    )

        return result


    # --------------------------------------------------------
    # Identifier            BASE -> resolve(constants["BASE"])
    # --------------------------------------------------------

    if node.type == "identifier":

        name = text(node, source)

        # Circular reference protection
        if name in seen:
            return PLACEHOLDER

        if name in constants:

            return resolve(
                constants[name],
                source,
                constants,
                seen | {name},
            )

        return PLACEHOLDER


    # --------------------------------------------------------
    # Binary expression     BASE + "/users"  (only `+`)
    # --------------------------------------------------------

    if node.type == "binary_expression":

        children = node.named_children

        if len(children) != 2:
            return PLACEHOLDER

        left_node = children[0]
        right_node = children[1]

        # Find operator
        operator = None

        for child in node.children:
            if child.type == "+":
                operator = "+"

        if operator == "+":

            left = resolve(
                left_node,
                source,
                constants,
                seen,
            )

            right = resolve(
                right_node,
                source,
                constants,
                seen,
            )

            return left + right

        return PLACEHOLDER


    # --------------------------------------------------------
    # Parenthesized expression      (BASE + "/users")
    # --------------------------------------------------------

    if node.type == "parenthesized_expression":

        children = node.named_children

        if len(children) == 1:

            return resolve(
                children[0],
                source,
                constants,
                seen,
            )


    # --------------------------------------------------------
    # Anything else -> placeholder
    # --------------------------------------------------------

    return PLACEHOLDER


# ============================================================
# Collect constants
# ============================================================

# Only store values whose node type is a direct string literal.
# This prevents minified-code reuse of short names (e, t, n)
# from overwriting URL constants with non-string values like
# null, objects, arrays, or arrow functions.

_STORABLE_TYPES = frozenset({"string", "template_string"})


def find_constants(node, source, constants):
    """
    Walk the AST and collect  const/var/let NAME = <string>
    into *constants* as  {name: value_node}.

    Only stores values that are string or template_string
    nodes.  A later string declaration for the same name
    overwrites an earlier one, but non-string declarations
    (null, object, array, …) are silently ignored.
    """

    if node.type == "variable_declarator":

        children = node.named_children

        if len(children) >= 2:

            name_node = children[0]
            value_node = children[1]

            if (
                name_node.type == "identifier"
                and value_node.type in _STORABLE_TYPES
            ):

                name = text(name_node, source)
                constants[name] = value_node

    for child in node.named_children:

        find_constants(
            child,
            source,
            constants,
        )


# ============================================================
# Endpoint filter
# ============================================================

def is_valid_endpoint(value):
    """
    Keep only non-empty, single-line, absolute HTTP(S) URLs
    without spaces.
    """

    if not value:
        return False

    if "\n" in value or "\r" in value:
        return False

    if " " in value:
        return False

    if not value.startswith(("http://", "https://")):
        return False

    return True


# ============================================================
# Normalize resolved URL
# ============================================================

def normalize(url):
    """
    Collapse consecutive {var} placeholders and any
    non-URL-path junk between them into a single {var}.

    Example:
        https://x.y/api/unit/{var}junk{var}more
        -> https://x.y/api/unit/{var}
    """

    ph = PLACEHOLDER
    out = []
    i = 0

    while i < len(url):

        # Check for placeholder
        if url[i:i + len(ph)] == ph:

            # Only add if previous token wasn't already {var}
            if not out or out[-1] != ph:
                out.append(ph)

            i += len(ph)

            # Skip any characters until next `/`, `?`, `#`,
            # or another placeholder.  This drops garbage
            # text that got concatenated between placeholders.
            while i < len(url):

                if url[i] in "/\\" or url[i:i + len(ph)] == ph:
                    break

                # Another {var} starts — skip chars between
                if url[i] == "{":
                    break

                i += 1

        else:
            out.append(url[i])
            i += 1

    return "".join(out)


# ============================================================
# Find URLs (general AST walk)
# ============================================================

CANDIDATE_TYPES = frozenset({"string", "template_string"})


def _is_concat(node):

    if node.type != "binary_expression":
        return False

    for child in node.children:
        if child.type == "+":
            return True

    return False


def find_urls(node, source, constants, results, inside_candidate=False):
    """
    Walk the full AST.  Resolve every top-level string-
    producing expression and keep it if it passes the filter.
    """

    is_candidate = node.type in CANDIDATE_TYPES

    if node.type == "binary_expression":
        is_candidate = _is_concat(node)

    if is_candidate and not inside_candidate:

        value = resolve(
            node,
            source,
            constants,
        )

        value = normalize(value)

        if is_valid_endpoint(value):
            results.add(value)

        for child in node.named_children:

            find_urls(
                child,
                source,
                constants,
                results,
                inside_candidate=True,
            )

        return

    for child in node.named_children:

        find_urls(
            child,
            source,
            constants,
            results,
            inside_candidate=inside_candidate,
        )


# ============================================================
# Parse JavaScript source
# ============================================================

def parse_js(path):

    path = Path(path)

    with path.open("rb") as f:
        source = f.read()

    tree = parser.parse(source)

    return tree, source


# ============================================================
# Main
# ============================================================

def main():

    if len(sys.argv) >= 2:
        path = sys.argv[1]
    else:
        print(
            "Usage: python tree-sitter.py <file.js>",
            file=sys.stderr,
        )
        sys.exit(1)

    tree, source = parse_js(path)

    # 1. Build constant map
    constants = {}

    find_constants(
        tree.root_node,
        source,
        constants,
    )

    # 2. Walk AST, resolve expressions, collect URLs
    results = set()

    find_urls(
        tree.root_node,
        source,
        constants,
        results,
    )

    # 3. Print deduplicated, sorted results
    for url in sorted(results):
        print(url)


if __name__ == "__main__":
    main()