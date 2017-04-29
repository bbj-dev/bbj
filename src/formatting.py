"""
A B A N D O N                               ,:
   A L L  H O P E                         ,' |
                                         /   :
                                      --'   /
       F O R  Y E  W H O              \/ /:/
           E N T E R  H E R E         / ://_\
                                   __/   /
                                   )'-. /
 Crude hacks lie beneath us.      ./  :\
                                    /.' '
This module includes a couple     '/'
of custom (GROAN) formatting    +
specifications and parsers      '
for them. Why did i do this?  `.
      I have no idea!      .-"-
                          (    |
                       . .-'  '.
                      ( (.   )8:
                  .'    / (_  )
                   _. :(.   )8P  `
               .  (  `-' (  `.   .
                .  :  (   .a8a)
               /_`( "a `a. )"'
           (  (/  .  ' )=='
          (   (    )  .8"   +
            (`'8a.( _(   (
         ..-. `8P    ) `  )  +
       -'   (      -ab:  )
     '    _  `    (8P"Ya
   _(    (    )b  -`.  ) +
  ( 8)  ( _.aP" _a   \( \   *
+  )/    (8P   (88    )  )
   (a:f   "     `"`


The internal representation of formatted text is much like an s-expression.

They are specified as follows:
            [directive: this is the body of text to apply it to]

The colon and the space following are important! The first space is not part
of the body, but any trailing spaces after it or at the end of the body are
included in the output.

Escaping via backslash is supported. Nesting is supported as well, but escaping
the delimiters is a bit tricky when nesting (both ends need to be escaped).
See the following examples:

[bold: this here \] is totally valid, and so is [<-TOTALLY OK this]
[bold: \[red: but both]<-CHOKE delimiters within a nest must be escaped.]

Directives are only parsed whenever the directive name is defined, and the
colon/space follow it. Thus, including [brackets like this] in a post body
will NOT require you to escape it! Even [brackets: like this] is safe, because
brackets is not a defined formatting parameter. So, any amount of unescaped brackets
may exist within the body unless they mimic a directive. To escape a valid directive,
escaping only the opening is suffiecient: \[bold: like this]. The literal body of
text outputted by that will be [bold: like this], with the backslash removed.

Just like the brackets themselves, backslashes may occur freely within bodies,
they are only removed when they occur before a valid expression.
"""

from string import punctuation
import re

colors = [
#0,   1        2        3        4       5        6       dim is not used in color api
    "red", "yellow", "green", "blue", "cyan", "magenta", "dim"
]

markup = [
    "bold", "underline", "linequote", "quote", "rainbow"
]


# quotes being references to other post_ids, like >>34 or >>0 for OP
quotes = re.compile(">>([0-9]+)")
bold = re.compile(r"(?<!\\)\*{2}(.+?)(?<!\\)\*{2}")
underline = re.compile(r"(?<!\\)_{2}(.+?)(?<!\\)_{2}")
escapes = re.compile(r"\\([*_]{2})")


def apply_directives(text):
    # is there a better way to do this? smh....
    text = quotes.sub(lambda m: "[quote: %s]" % m.group(1), text)
    text = bold.sub(lambda m: "[bold: %s]" % m.group(1), text)
    text = underline.sub(lambda m: "[underline: %s]" % m.group(1), text)
    return escapes.sub(lambda m: m.group(1), text)


def linequote_p(line):
    if not line.startswith(">"):
        return False
    _fp = line.find(" ")
    return not quotes.search(line[:_fp] if _fp != -1 else line)


def parse_segments(text, sanitize_linequotes=True):
    """
    Parse linequotes, quotes, and paragraphs into their appropriate
    representations. Paragraphs are represented as separate strings
    in the returned list, and quote-types are compiled to their
    [bracketed] representations.
    """
    result = list()
    hard_quote = False
    for paragraph in re.split("\n{2,}", text):
        pg = str()
        for line in paragraph.split("\n"):
            if line == "```":
                # because of this lazy way of handling it,
                # its not actually necessary to close a
                # hard quote segment. i guess thats a positive
                # just because i dont have to throw syntax
                # errors at the users for it. feels dirty
                # but its easier for all of us.
                if hard_quote:
                    pg += "\n"
                hard_quote = not hard_quote
                continue

            elif hard_quote:
                pg += "\n" + line
                continue

            elif not line:
                continue

            if linequote_p(line):
                if sanitize_linequotes:
                    inner = line.replace("]", "\\]")

                else:
                    inner = apply_directives(line)

                pg += "[linequote: %s]" % inner.strip()

            else:
                sep = "\n" if line[0] in punctuation else " "
                pg += apply_directives(line.rstrip()) + sep

        result.append(pg.rstrip())
    return result


def sequential_expressions(string):
    """
    Takes a string, sexpifies it, and returns a list of lists
    who contain tuples. Each list of tuples represents a paragraph.
    Within each paragraph, [0] is either None or a markup directive,
    and [1] is the body of text to which it applies. This representation
    is very easy to handle for a client. It semi-supports nesting:
    eg, the expression [red: this [blue: is [green: mixed]]] will
    return [("red", "this "), ("blue", "is "), ("green", "mixed")],
    but this cannot effectively express an input like
    [bold: [red: bolded colors.]], in which case the innermost
    expression will take precedence. For the input:
        "[bold: [red: this] is some shit [green: it cant handle]]"
    you get:
    [('red', 'this'), ('bold', ' is some shit '), ('green', 'it cant handle')]
    """
    # abandon all hope ye who enter here
    directives = colors + markup
    result = list()
    for paragraph in parse_segments(string):
        stack = [[None, str()]]
        skip_iters = 0
        nest = [None]
        escaped = False
        for index, char in enumerate(paragraph):
            if skip_iters:
                skip_iters -= 1
                continue

            if not escaped and char == "[":
                directive = paragraph[index+1:paragraph.find(": ", index+1)]
                open_p = directive in directives
            else:
                open_p = False
            clsd_p = not escaped and nest[-1] != None and char == "]"

            # dont splice other directives into linequotes: that is far
            # too confusing for the client to determine where to put line
            # breaks
            if open_p and nest[-1] != "linequote":
                stack.append([directive, str()])
                nest.append(directive)
                skip_iters += len(directive) + 2

            elif clsd_p:
                nest.pop()
                stack.append([nest[-1], str()])

            else:
                escaped = char == "\\"
                try:
                    n = paragraph[index + 1]
                except IndexError:
                    n = " "
                if not (escaped and n in "[]"):
                    stack[-1][1] += char
        # filter out unused bodies, eg ["red", ""]
        result.append([(directive, body) for directive, body in stack if body])
    return result


def apply_formatting(msg_obj, formatter):
    """
    Receives a messages object from a thread and returns it with
    all the message bodies passed through FORMATTER. Not all
    formatting functions have to return a string. Refer to the
    documentation for each formatter.
    """
    for x, obj in enumerate(msg_obj):
        if not msg_obj[x].get("send_raw"):
            msg_obj[x]["body"] = formatter(obj["body"])
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
    pass # me the bong im boutta smash tha bish



def entities(text):
    """
    Returns a tuple where [0] is raw text and [1] is documentation
    """
    # once someone asked me if i wanted a life
    # and i said
    pass



def html(text):
    """
    Returns messages in html format, after being sent through markdown.
    Color directives are given as:
      <span color="{COLOR}" style="color: {COLOR};">content</span>

    Directives may be nested. If you don't have access to a fully featured
    and compliant html renderer in your client, you should use one of the
    simpler directives like strip, indice, or raw.
    """
    return "where is your god now"


# and this is drunk too
def map_html(match):
    return """
    If there is a place you got to go
    I am the one you need to know
    I'm the Map!
    I'm the Map!
    I'm the Map!

    If there is a place you got to get
    I can get you there I bet
    I'm the Map!
    I'm the Map!
    I'm the Map!

    I'm the Map!

    I'm the Map!
    I'm the Map!

    I'm the Map!
    I'm the Map!
    I'm the Map!

    I'm the Map!
    I'm the Map!
    I'm the Map!
    """
