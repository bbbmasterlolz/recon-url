import sys
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_javascript

# Tree-sitter setup
JS_LANGUAGE = Language(tree_sitter_javascript.language())
parser = Parser(JS_LANGUAGE)

def text(node, source):
    return source[node.start_byte:node.end_byte].decode(
        "utf-8",
        errors="replace",
    )

def parse_js(path):

    path = Path(path)

    with path.open("rb") as f:
        source = f.read()

    tree = parser.parse(source)

    return tree, source

def extract_strings(node, source):
    strings = []

    if node.type in ("string", "template_string"):
        strings.append(node)

    for child in node.named_children:
        strings.extend(extract_strings(child, source))

    return strings

def is_valid_endpoint(value):
    if not value:
        return False

    if "\n" in value or "\r" in value:
        return False

    if " " in value:
        return False

    if not value.startswith(("http://", "https://", "{base_url}")):
        return False

    return True

def strip_quotes(value):
    if len(value) >= 2:
        if value[0] == value[-1] and value[0] in ("'", '"', "`"):
            return value[1:-1]

    return value

def get_parent_type(node):
    parent = node.parent

    if parent is None:
        return "direct"

    return str(parent.type)

def get_all_usage(node_o, source):
    cursor = node_o.parent.walk()


    def visit(cursor):
        node = cursor.node

        if node == node_o:
            return

        if node.type == "identifier":
            print(text(node.parent, source))

        if cursor.goto_first_child():
            while True:
                visit(cursor)

                if not cursor.goto_next_sibling():
                    break

            cursor.goto_parent()

    visit(cursor)

def processed_str(strings):
    valid = []

    for string in strings:
        if is_valid_endpoint(string):
            valid.append(string)

    return sorted(set(valid))

def print_tree(node, source, indent=0):
    print(
        " " * indent
        + f"{node.type}: {text(node, source)!r}"
    )

    for child in node.named_children:
        print_tree(child, source, indent + 2)

def vessel(root, source):
    PLACEHOLDER = "{?}"

    const = {}
    strings = []

    def resolve(node, seen=None):
        if seen is None:
            seen = set()

        # ── String literal  "hello"  'hello' ──
        if node.type == "string":
            value = text(node, source).strip("\"'`")
            strings.append(value)
            return value

        # ── Template string  `${base}/users/${name}` ──
        if node.type == "template_string":
            result = ""

            for child in node.named_children:
                if child.type in ("template_chars", "string_fragment"):
                    result += text(child, source)

                elif child.type == "template_substitution":
                    expressions = child.named_children
                    if expressions:
                        result += resolve(expressions[0], seen)

            strings.append(result)
            return result

        # ── Identifier ──
        if node.type == "identifier":
            name = text(node, source)

            # Circular reference guard
            if name in seen:
                return PLACEHOLDER

            if name in const:
                return const[name]

            return PLACEHOLDER

        # ── Member expression  O.baseUrl, config.api.url ──
        if node.type == "member_expression":
            key = _member_key(node)
            if key and key in const:
                return const[key]
            return PLACEHOLDER

        # ── Binary expression  a + b  (only + ) ──
        if node.type == "binary_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")

            if not left or not right:
                return PLACEHOLDER

            # Only handle string concatenation (+)
            has_plus = any(
                c.type == "+" for c in node.children
            )

            if not has_plus:
                return PLACEHOLDER

            left_value = resolve(left, seen)
            right_value = resolve(right, seen)

            value = left_value + right_value
            strings.append(value)
            return value

        # ── Parenthesized expression  (a + b) ──
        if node.type == "parenthesized_expression":
            children = node.named_children
            if len(children) == 1:
                return resolve(children[0], seen)

        # ── Anything else → placeholder ──
        return PLACEHOLDER

    def _member_key(node):
        """Build a dotted key from a member_expression, e.g. O.baseUrl."""
        if node.type == "identifier":
            return text(node, source)
        if node.type == "member_expression":
            obj = node.child_by_field_name("object")
            prop = node.child_by_field_name("property")
            if obj and prop:
                obj_key = _member_key(obj)
                if obj_key:
                    return obj_key + "." + text(prop, source)
        return None

    def _extract_object_props(obj_node, prefix):
        """Walk an object literal, store leaf values with dotted keys."""
        for child in obj_node.named_children:
            if child.type == "pair":
                key_node = child.child_by_field_name("key")
                value_node = child.child_by_field_name("value")
                if key_node and value_node:
                    key = text(key_node, source)
                    full_key = prefix + "." + key

                    if value_node.type == "object":
                        _extract_object_props(value_node, full_key)
                    else:
                        value = resolve(value_node)
                        if value is not None:
                            const[full_key] = value

    def _is_concat(node):
        """Check if a binary_expression uses the + operator."""
        if node.type != "binary_expression":
            return False
        return any(c.type == "+" for c in node.children)

    def _has_substitution(node):
        """Check if a template_string has ${...} substitutions."""
        if node.type != "template_string":
            return False
        return any(
            c.type == "template_substitution"
            for c in node.named_children
        )

    def visit(node):
        # Variable declaration — resolve + store constant
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")

            if name_node and value_node:
                name = text(name_node, source)

                # Object literal → extract properties with dotted keys
                if value_node.type == "object":
                    _extract_object_props(value_node, name)

                # Resolve FIRST
                value = resolve(value_node)

                # Then store resolved result
                if value is not None:
                    const[name] = value

        # Template string with substitutions (outside of variable decl)
        # e.g.  fetch(`${BASE}${path}`)
        elif _has_substitution(node):
            resolve(node)

        # Binary concat (outside of variable decl)
        # e.g.  fetch(BASE + "/endpoint")
        elif _is_concat(node):
            resolve(node)

        # Plain string / template_string (no substitutions)
        # e.g.  Uh(`/alumni`),  { path: `/endpoint` }
        elif node.type in ("string", "template_string"):
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

    if "\n" in value or "\r" in value:
        return False

    if " " in value:
        return False

    return True


def main():

    if len(sys.argv) >= 2:
        path = sys.argv[1]
    else:
        print(
            "Usage: python tree.py <file.js>",
            file=sys.stderr,
        )
        sys.exit(1)

    tree, source = parse_js(path)

    const, strings = vessel(tree.root_node, source)

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

    for url in sorted(results):
        print(url)

    print("url found: ", len(results))


if __name__ == "__main__":
    main()
