import re

COLORS = ["red", "green", "yellow", "blue", "magenta", "cyan"]
KEYWORDS = COLORS + [
    "bold", "italic", "underline"
]


TOKENS = re.compile(r"\[\[({}): (.+?)]]".format("|".join(KEYWORDS)), flags=re.DOTALL)
QUOTES = re.compile(">>([0-9]+)")
LINEQUOTES = re.compile("^>(.+)$", flags=re.MULTILINE)


def parse(text, doquotes=True):
    output = TOKENS.sub("\\2", text)
    objects = list()
    offset = 0
    for token in TOKENS.finditer(text):
        directive = token.group(1).lower()
        start = token.start() - offset
        end = start + len(token.group(2))
        offset += len(directive) + 6
        if directive in COLORS:
            objects.append(["color", start, end, directive])
        else:
            objects.append([directive, start, end])

    objects += [["linequote", m.start(), m.end()]
                  for m in LINEQUOTES.finditer(output)]

    if doquotes:
        objects += [["quote", m.start(), m.end(), int(m.group(1))]
                      for m in QUOTES.finditer(output)]

    return output, objects
