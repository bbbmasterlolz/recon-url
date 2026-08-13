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

    if not value.startswith(("http://", "https://")):
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

def get_all_usage(node, source):
    cursor = node.parent.walk()

    origin = node.parent
    print("origin:", origin.type, text(origin, source))

    origin_name_node = origin.child_by_field_name("name")

    if origin_name_node is None:
        return

    origin_name = text(origin_name_node, source)

    def visit(cursor):
        current = cursor.node

        if current == origin:
            return

        name_node = current.child_by_field_name("name")

        if name_node:
            if text(name_node, source) == origin_name:
                print(current.type, text(current, source))

        if cursor.goto_first_child():
            while True:
                visit(cursor)

                if not cursor.goto_next_sibling():
                    break

            cursor.goto_parent()

    visit(cursor)

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

    nodes = extract_strings(tree.root_node, source)

    for node in nodes:
        # string = text(node, source)
        # string = strip_quotes(string)
        # if is_valid_endpoint(string):
        #     print(f"{get_string_context(node):<25}{text(node.parent, source):<25}")
        # parent = get_parent_type(node)
        # if parent == "variable_declarator":
        #     print(f"{text(node.parent.child_by_field_name("name"), source):<10}{text(node, source)}")
        get_all_usage(node, source)

if __name__ == "__main__":
    main()

