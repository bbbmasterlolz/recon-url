import sys
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_javascript
try:
    from analyse import Tester
except ImportError:
    import Tester

# Tree-sitter setup
JS_LANGUAGE = Language(tree_sitter_javascript.language())
parser = Parser(JS_LANGUAGE)

def text(node, source_text):
    """Extract node text from pre-decoded source string."""
    return source_text[node.start_byte:node.end_byte]

def parse_js(path):

    path = Path(path)

    with path.open("rb") as f:
        source_bytes = f.read()

    tree = parser.parse(source_bytes)
    source_text = source_bytes.decode("utf-8", errors="replace")

    return tree, source_text

def is_valid_endpoint(value):
    if not value:
        return False

    if not value.startswith(("http://", "https://", "{base_url}")):
        return False

    # Reject values with whitespace or newlines
    if any(c in value for c in " \n\r"):
        return False

    return True

def vessel(root, source_text):
    PLACEHOLDER = "{?}"

    const = {}
    strings = set()

    def resolve(node, seen=None):
        if seen is None:
            seen = set()

        ntype = node.type

        # ── String literal  "hello"  'hello' ──
        if ntype == "string":
            value = text(node, source_text).strip("\"'`")
            strings.add(value)
            return value

        # ── Template string  `${base}/users/${name}` ──
        if ntype == "template_string":
            parts = []

            for child in node.named_children:
                if child.type in ("template_chars", "string_fragment"):
                    parts.append(text(child, source_text))

                elif child.type == "template_substitution":
                    expressions = child.named_children
                    if expressions:
                        parts.append(resolve(expressions[0], seen))

            result = "".join(parts)
            strings.add(result)
            return result

        # ── Identifier ──
        if ntype == "identifier":
            name = text(node, source_text)

            # Circular reference guard
            if name in seen:
                return PLACEHOLDER

            seen.add(name)
            return const.get(name, PLACEHOLDER)

        # ── Member expression  O.baseUrl, config.api.url ──
        if ntype == "member_expression":
            key = _member_key(node)
            if key:
                return const.get(key, PLACEHOLDER)
            return PLACEHOLDER

        # ── Binary expression  a + b  (only + ) ──
        if ntype == "binary_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")

            if not left or not right:
                return PLACEHOLDER

            # Only handle string concatenation (+)
            if not any(c.type == "+" for c in node.children):
                return PLACEHOLDER

            left_value = resolve(left, seen)
            right_value = resolve(right, seen)

            value = left_value + right_value
            strings.add(value)
            return value

        # ── Parenthesized expression  (a + b) ──
        if ntype == "parenthesized_expression":
            children = node.named_children
            if len(children) == 1:
                return resolve(children[0], seen)

        # ── Anything else → placeholder ──
        return PLACEHOLDER

    def _member_key(node):
        """Build a dotted key from a member_expression, e.g. O.baseUrl."""
        if node.type == "identifier":
            return text(node, source_text)
        if node.type == "member_expression":
            obj = node.child_by_field_name("object")
            prop = node.child_by_field_name("property")
            if obj and prop:
                obj_key = _member_key(obj)
                if obj_key:
                    return obj_key + "." + text(prop, source_text)
        return None

    def _extract_object_props(obj_node, prefix):
        """Walk an object literal, store leaf values with dotted keys."""
        for child in obj_node.named_children:
            if child.type == "pair":
                key_node = child.child_by_field_name("key")
                value_node = child.child_by_field_name("value")
                if key_node and value_node:
                    key = text(key_node, source_text)
                    full_key = prefix + "." + key

                    if value_node.type == "object":
                        _extract_object_props(value_node, full_key)
                    else:
                        value = resolve(value_node)
                        if value is not None:
                            const[full_key] = value

    def visit(node):
        ntype = node.type

        # Variable declaration — resolve + store constant
        if ntype == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")

            if name_node and value_node:
                name = text(name_node, source_text)

                # Object literal → extract properties with dotted keys
                if value_node.type == "object":
                    _extract_object_props(value_node, name)

                # Resolve FIRST, then store
                value = resolve(value_node)
                if value is not None:
                    const[name] = value

        # Resolve strings, templates, and concatenations directly
        # (no pre-check needed — resolve() handles all node types)
        elif ntype in ("string", "template_string", "binary_expression"):
            resolve(node)

        # Visit children
        for child in node.named_children:
            visit(child)

    visit(root)

    return const, strings


def _is_path(value):
    """Check if a string looks like an API path."""
    if not value or not value.startswith("/"):
        return False

    if any(c in value for c in " \n\r"):
        return False

    return True


def parse_and_extract(path):
    """Parse a JS file and return (results set, const dict, strings set).
    
    Importable entry point — avoids subprocess overhead.
    """
    tree, source_text = parse_js(path)
    const, strings = vessel(tree.root_node, source_text)

    results = set()
    for string in strings:
        if is_valid_endpoint(string):
            results.add(string)
        elif _is_path(string):
            candidate = "{base_url}" + string
            if is_valid_endpoint(candidate):
                results.add(candidate)

    return results, const, strings


def main():

    if len(sys.argv) >= 2:
        path = sys.argv[1]
    else:
        print(
            "Usage: python tree.py <file.js>",
            file=sys.stderr,
        )
        sys.exit(1)

    tree, source_text = parse_js(path)

    const, strings = vessel(tree.root_node, source_text)

    # ── Collect results ──
    results = set()

    for string in strings:
        # Direct full URLs
        if is_valid_endpoint(string):
            results.add(string)

        # Path-like strings → prefix with {base_url}
        elif _is_path(string):
            candidate = "{base_url}" + string
            if is_valid_endpoint(candidate):
                results.add(candidate)

    print("String extraction DONE")

    tested = Tester.test_urls(sorted(results))

    for url in tested:
         print(url)

    print("url found: ", len(tested))


if __name__ == "__main__":
    main()
