import re

with open("a.js", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'`[\s\S]*?`'

matches = re.findall(pattern, content)

for match in matches:
    print(match)
    print("===================")