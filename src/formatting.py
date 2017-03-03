from markdown import markdown
from html import escape
import re

# these parameters are utter nonsense...
COLORS = ["red", "green", "yellow", "blue", "magenta", "cyan"]
MARKUP = ["bold", "italic", "underline", "strike"]
TOKENS = re.compile(r"\[({}): (.+?)]".format("|".join(COLORS + MARKUP)), flags=re.DOTALL)
QUOTES = re.compile("&gt;&gt;([0-9]+)")
LINEQUOTES = re.compile("^(&gt;.+)$", flags=re.MULTILINE)


def map_html(match):
    directive, body = match.group(1).lower(), match.group(2)
    if directive in COLORS:
        return '<span color="{0}" style="color: {0};">{1}</span>'.format(directive, body)
    elif directive in MARKUP:
        return '<{0}>{1}</{0}>'.format(directive[0], body)
    return body


def parse(text, doquotes=True):
    text = TOKENS.sub(map_html, escape(text))
    if doquotes:
        text = QUOTES.sub(r'<span post="\1" class="quote">\g<0></span>', text)
    return markdown(
        LINEQUOTES.sub(r'<span class="linequote">\1</span>', text)
    )
