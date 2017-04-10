"""
This module is not complete and none of its functions are currently
used elsewhere. Subject to major refactoring.
"""

from markdown import markdown
from html import escape
import re

#0,   1        2        3        4       5        6
colors = [
    "red", "yellow", "green", "blue", "cyan", "magenta"
]

markup = [
    "bold", "italic", "underline", "strike"
]

tokens = re.compile(r"\[(%s): (.+?)]" % "|".join(colors + markup),
                    flags=re.DOTALL)

quotes = re.compile(">>([0-9]+)")
linequotes = re.compile("^(>.+)$",
    flags=re.MULTILINE)


def apply_formatting(msg_obj, formatter):
    """
    Receives a messages object from a thread and returns it with
    all the message bodies passed through FORMATTER.
    """
    for x in range(len(msg_obj)):
        msg_obj[x]["body"] = formatter(msg_obj[x]["body"])
    return msg_obj


def raw(text):
    """
    Just return the message in the same state that it was submitted.
    """
    return text


def strip(text):
    """
    Returns the text with all formatting directives removed.
    Not to be confused with `raw`.
    """



def entities(text):
    """
    Returns a tuple where [0] is raw text
    """


def html(text):
    """
    Returns messages in html format, after being sent through markdown.
    Color directives are given as:
      <span color="{COLOR}" style="color: {COLOR};">content</span>

    Directives may be nested. If you don't have access to a fully featured
    and compliant html renderer in your client, you should use one of the
    simpler directives like strip, indice, or raw.
    """

    text = TOKENS.sub(map_html, escape(text))
    text = QUOTES.sub(r'<span post="\1" class="quote">\g<0></span>', text)
    return markdown(
        LINEQUOTES.sub(r'<span class="linequote">\1</span><br>', text))

# and this is the callback used by the sub statement
def map_html(match):
    directive, body = match.group(1).lower(), match.group(2)
    if directive in colors:
        return '<span color="{0}" style="color: {0};">{1}</span>'.format(directive, body)
    elif directive in markup:
        return '<{0}>{1}</{0}>'.format(directive[0], body)
    return body
