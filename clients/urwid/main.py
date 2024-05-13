# -*- fill-column: 72 -*-
"""
If you're looking for help on how to use the program, just press
? while its running. This mess will not help you.

Urwid aint my speed. Hell, making complex, UI-oriented programs
aint my speed. So some of this code is pretty messy. I stand by
it though, and it seems to be working rather well.

Most of the functionality is crammed in the App() class. Key
handling is found in the other subclasses for urwid widgets.
An instantiation of App() is casted as `app` globally and
the keypress methods will call into this global `app` object.

There are few additional functions that are defined outside
of the App class. They are delegated to the very bottom of
this file.

Please mail me (~desvox) for feedback and for any of your
"OH MY GOD WHY WOULD YOU DO THIS"'s or "PEP8 IS A THING"'s.
"""

from network import BBJ, URLError
from string import punctuation
from datetime import datetime
from sys import argv, version
from time import time, sleep
from getpass import getpass
from subprocess import call
from random import choice
from code import interact
from math import floor
import rlcompleter
import readline
import tempfile
import urwid
import json
import os
import re


def get_arg(key, default=None, get_value=True):
    try:
        spec = argv.index("--" + key)
        value = argv[spec + 1] if get_value else True
    except ValueError: # --key not specified
        value = default
    except IndexError: # flag given but no value
        exit("invalid format for --" + key)
    return value

help_text = """BBJ Urwid Client
Available options:
    --help: this message
    --https: enable use of https, requires host support
    --host <hostname>: the ip address/hostname/website/server to connect to
    --port <port>: the port to use when connecting to the host
    --user <username>: automatically connect with the given username
    --thread <thread_id>: specify a thread_id to open immediately
Available environment variables:
    BBJ_USER: set your username to log in automatically.
      If --user is passed, this is ignored.
    BBJ_PASSWORD: set your password to log in automatically.
      if the password is wrong, will prompt you as normal.
    NO_COLOR: disable all color output from the program.
Please note that these environment variables need to be exported, and are
visible to all other programs run from your shell.
"""

if get_arg("help", False, False):
    print(help_text)
    exit()
try:
    network = BBJ(get_arg("host", "127.0.0.1"),
                  get_arg("port", 7099),
                  get_arg("https", False, False))
except URLError as e:
    print(help_text)
    # print the connection error in red
    if os.getenv("NO_COLOR"):
        exit("%s" % repr(e))
    exit("\033[0;31m%s\033[0m" % repr(e))

obnoxious_logo = """
  %     _                 *              !            *
%   8 888888888o  % 8 888888888o   .           8 8888
    8 8888    `88.  8 8888    `88.      _   !  8 8888   &
  ^ 8 8888     `88  8 8888     `88   *         8 8888 _
    8 8888     ,88  8 8888     ,88             8 8888
*   8 8888.   ,88'  8 8888.   ,88'      !      8 8888    "
    8 8888888888    8 8888888888               8 8888 =
  ! 8 8888    `88.  8 8888    `88.  88.        8 8888
    8 8888      88  8 8888      88  `88.    |  8 888'   '
 >  8 8888.   ,88'  8 8888.   ,88'    `88o.   .8 88'  .
    8 888888888P    8 888888888P        `Y888888 '  .
 %                                                     %"""

welcome = """>>> Welcome to Bulletin Butter & Jelly! ------------------@
| BBJ is a persistent, chronologically ordered text       |
| discussion board for tildes. You may log in,            |
| register as a new user, or participate anonymously.     |
|---------------------------------------------------------|
| \033[1;31mTo go anon, just press enter. Otherwise, give me a name\033[0m |
|                 \033[1;31m(registered or not)\033[0m                     |
@_________________________________________________________@
"""

welcome_monochrome = """>>> Welcome to Bulletin Butter & Jelly! ------------------@
| BBJ is a persistent, chronologically ordered text       |
| discussion board for tildes. You may log in,            |
| register as a new user, or participate anonymously.     |
|---------------------------------------------------------|
| To go anon, just press enter. Otherwise, give me a name |
|                 (registered or not)                     |
@_________________________________________________________@
"""

anon_warn = """>>> \033[1;31mJust a reminder!\033[0m ----------------------------------@
| You are not logged into BBJ, and are posting this    |
| message anonymously. If you do not log in, you will  |
| not be able to edit or delete this message. This     |
| warning can be disabled in the settings.             |
|------------------------------------------------------|
"""

anon_warn_monochrome = """>>> Just a reminder! ----------------------------------@
| You are not logged into BBJ, and are posting this    |
| message anonymously. If you do not log in, you will  |
| not be able to edit or delete this message. This     |
| warning can be disabled in the settings.             |
|------------------------------------------------------|
"""

format_help = [
    r"Quick reminder: \[rainbow: expressions work like this]. You may scroll "
    "this message, or press Q or escape to close it.\n\n"

    "BBJ supports **bolding**, __underlining__, and [rainbow: coloring] text "
    "using markdown-style symbols as well as tag-like expressions. Markdown "
    "is **NOT** fully implemented, but several of the more obvious concepts "
    "have been brought over. Additionally, we have chan-style greentext and "
    "numeric post referencing, ala >>3 for the third reply.",

    "[red: Whitespace]",

    "When you're composing, it is desirable to not include your own linebreaks "
    "into paragraphs of your post, because clients handle text wrapping on their "
    "own. Adding them yourself can cause your posts to look very strange. You can "
    "always edit your posts after submitting them if you do this by accident, as "
    "long as you are not anonymous.",

    "In previous versions of BBJ, linebreaks were joined into sentences if they "
    "occured in the same paragraph, however this confused many users and has been "
    "reverted to just use whatever was submitted, as-is.",


    "[red: Colors, Bold, Underline & Expressions]",

    "You can use [rainbow: rainbow], [red: red], [yellow: yellow], [green: green], "
    "[blue: blue], [cyan: cyan], [magenta: and magenta], [dim: dim], **bold**, and __underline__ "
    r"inside of your posts. \**bold works like this\**, \__and underlines like this\__. "
    r"You can escape these expressions \\**like this\\**. They can span up to the full width "
    "of the same line. They are best used on shorter phrases. "
    "However, you can use a different syntax for it, which is also required to use "
    r"colors: these expressions \[bold: look like this] and have less restrictions.",

    "The colon and the space following it are important. When you use these "
    "expressions, the __first__ space is not part of the content, but any characters, "
    "including spaces, that follow it are included in the body. The formatting will "
    r"apply until the closing ]. You can escape such an expression \\[cyan: like this] "
    r"and can also \[blue: escape \\] other closing brackets] inside of it. Only "
    "closing brackets need to be escaped within an expression. Any backslashes used "
    "for escaping will not show in the body unless you use two slashes.",

    "This peculiar syntax eliminates false positives. You never have to escape [normal] "
    "brackets when using the board. Only expressions with **valid and defined** directives "
    "will be affected. [so: this is totally valid and requires no escapes] because 'so' is "
    "not a directive. [red this will pass too] because the colon is missing.",

    "The following directives may be used in this form: red, yellow, green, blue, cyan, "
    "magenta, bold, underline, dim, and rainbow. Nesting expressions into eachother will "
    "override the parent directives until the innermost expression closes. Thus, nesting "
    "is valid but doesn't produce layered results on the command line client.",

    "[red: Quotes & Greentext]",

    "You can refer to a post number using two angle brackets pointing into a number. >>432 "
    "like this. You can color a whole line green by proceeding it with a '>'. Note that "
    "this violates the sentence structure outlined in the **Whitespace** section above, "
    "so you may introduce >greentext without splicing into seperate paragraphs. The '>' "
    "must be the first character on the line with no whitespace before it.\n>it looks like this\n"
    "and the paragraph doesnt have to break on either side. The formatter is smart enough to "
    "differentiate between >>greentext with multiple arrows and numeric quotes (outlined below) "
    "given that the text doesn't start with any numbers.",

    "When using numeric quotes, they are highlighted and the author's name will show "
    "next to them in the thread. You can press enter when focused on a message to view "
    "the parent posts. You may insert these directives manually or use the <Reply> function "
    "on post menus.",

    "Quoting directives cannot be escaped."
]

general_help = [
    ("bold", "use the arrow keys, j/k, or n/p to scroll down this menu\n\n"),
    ("bold", "use q or escape to close dialogs and menus (including this one)\n\n"),
    ("10", "use q, escape, or a left directional key to go back at any point"
     " from just about anywhere.\n\n"),
    ("20", "use the o key to change your settings when this dialog is closed\n\n"),

    "You may use the arrow keys, or use ", ("button", "jk/np/Control-n|p"),
    " to move up and down by "
    "an element. If an element is overflowing the screen, it will scroll only one line. "
    "To make scrolling faster, ", ("button", "hold shift"), " when using a control: it "
    "will repeat 5 times by default, and you can change this number in your settings.\n\n"

    "In threads, The ", ("button", "<"), " or ", ("button", ","), " keys, and ", ("button", ">"),
    " or ", ("button", "."), " keys will jump by "
    "a chosen number of post headers. You can see the count inside of the footer line at "
    "the far right side: press ", ("button", "x"), " to cycle it upwards or ",
    ("button", "X"), " to cycle it downwards.\n\n"

    "In the thread index and any open thread, the ", ("button", "b"), " and ", ("button", "t "),
    "keys may be used to go to very top or bottom.\n\n"

    "To go back and forth between threads, you may also use the left/right arrow keys, "
    "or ", ("button", "h"), "/", ("button", "l"), " to do it vi-style.\n\n"

    "Aside from those, primary controls are shown on the very bottom of the screen "
    "in the footer line, or may be placed in window titles for other actions like "
    "dialogs or composers."
]

colors = [
    "\033[1;31m", "\033[1;33m", "\033[1;33m",
    "\033[1;32m", "\033[1;34m", "\033[1;35m"
]

colornames = ["none", "red", "yellow", "green", "blue", "cyan", "magenta"]
editors = ["nano", "vim", "emacs", "vim -u NONE", "emacs -Q", "micro", "ed", "joe"]

default_prefs = {
    # using default= is not completely reliable, sadly...
    "editor": os.getenv("EDITOR") or "nano",
    "mouse_integration": False,
    "jump_count": 1,
    "shift_multiplier": 5,
    "integrate_external_editor": True,
    "index_spacing": False,
    "dramatic_exit": True,
    "date": "%Y/%m/%d",
    "time": "%H:%M",
    "frame_theme": "tilde",
    "custom_divider_char": False,
    "frame_title": "BBJ",
    "use_custom_frame_title": False,
    "max_text_width": 80,
    "confirm_anon": True,
    "information_density": "default",
    "thread_divider": True,
    "monochrome": False,
    "enable_dim": True,
    "edit_escapes": {
        "abort": "f1",
        "focus": "f2",
        "fhelp": "f3"
    }
}

bars = {
    "index": "[RET]Open [/]Search [C]ompose [R]efresh [*]Bookmark [O]ptions [?]Help [Q]uit",
    "thread": "[Q]Back [RET]Menu [C]ompose [^R]eply [R]efresh [0-9]Goto [B/T]End [</>]Jump[X]%d [/]Search",
    "edit_window": "[{}]Abort [{}]Swap [{}]Formatting Help [save/quit to send] {}"
}

colormap = [
    ("default", "default", "default"),
    ("bar", "light magenta", "default"),
    ("button", "light red", "default"),
    ("quote", "brown", "default"),
    ("opt_prompt", "black", "light gray"),
    ("opt_header", "light cyan", "default"),
    ("hover", "light cyan", "default"),
    ("dim", "dark gray", "default"),
    ("bold", "default,bold", "default"),
    ("underline", "default,underline", "default"),

    # map the bbj api color values for display
    ("0", "default", "default"),
    ("1", "dark red", "default"),
    # sounds ugly but brown is as close as we can get to yellow without being bold
    ("2", "brown", "default"),
    ("3", "dark green", "default"),
    ("4", "dark blue", "default"),
    ("5", "dark cyan", "default"),
    ("6", "dark magenta", "default"),

    # and have the bolded colors use the same values times 10
    ("10", "light red", "default"),
    ("20", "yellow", "default"),
    ("30", "light green", "default"),
    ("40", "light blue", "default"),
    ("50", "light cyan", "default"),
    ("60", "light magenta", "default")
]

monochrome_map = [
    ("default", "default", "default"),
    ("bar", "default", "default"),
    ("button", "default", "default"),
    ("quote", "default", "default"),
    ("opt_prompt", "default", "light gray"),
    ("opt_header", "default", "default"),
    ("hover", "default", "default"),
    ("dim", "default", "default"),
    ("bold", "default,bold", "default"),
    ("underline", "default,underline", "default"),

    ("0", "default", "default"),
    ("1", "default", "default"),
    ("2", "default", "default"),
    ("3", "default", "default"),
    ("4", "default", "default"),
    ("5", "default", "default"),
    ("6", "default", "default"),

    ("10", "default", "default"),
    ("20", "default", "default"),
    ("30", "default", "default"),
    ("40", "default", "default"),
    ("50", "default", "default"),
    ("60", "default", "default")
]

escape_map = {
    key: urwid.vterm.ESC + sequence
      for sequence, key in urwid.escape.input_sequences
      if len(key) > 1
}

themes = {
    "tilde": {
        "divider": "-",
        "frame": {
            "tlcorner": "@",
            "trcorner": "@",
            "blcorner": "@",
            "brcorner": "@",
            "tline":    "=",
            "bline":    "=",
            "lline":    "|",
            "rline":    "|",
        }
    },

    "urwid": {
        "divider": "─",
        "frame": {
            "tlcorner": "┌",
            "trcorner": "┐",
            "blcorner": "└",
            "brcorner": "┘",
            "tline":    "─",
            "bline":    "─",
            "lline":    "│",
            "rline":    "│",
        }
    },

    "none": {
        "divider": " ",
        "frame": {
            "tlcorner": "",
            "trcorner": "",
            "blcorner": "",
            "brcorner": "",
            "tline":    "",
            "bline":    "",
            "lline":    "",
            "rline":    "",
        }
    }
}

rcpath = os.path.join(os.getenv("HOME"), ".bbjrc")
markpath = os.path.join(os.getenv("HOME"), ".bbjmarks")
pinpath = os.path.join(os.getenv("HOME"), ".bbjpins")

class App(object):
    def __init__(self):
        self.prefs = bbjrc("load")
        self.client_pinned_threads = load_client_pins()
        self.immediate_thread_load = []
        self.usermap = {}
        self.match_data = {
            "query": "",
            "matches": [],
            "position": 0,
        }

        try:
            self.theme = themes[self.prefs["frame_theme"]].copy()
            if isinstance(self.prefs["custom_divider_char"], str):
                self.theme["divider"] = self.prefs["custom_divider_char"]
        except KeyError:
            exit("Selected theme does not exist. Please check "
                 "the `frame_theme` value in ~/.bbjrc")

        self.mode = None
        self.thread = None
        self.window_split = False
        self.last_index_pos = None
        self.last_alarm = None

        if self.prefs["use_custom_frame_title"]:
            self.frame_title = self.prefs["frame_title"]
        else:
            self.frame_title = network.instance_info["instance_name"]

        self.walker = urwid.SimpleFocusListWalker([])
        self.box = ActionBox(self.walker)
        self.body = urwid.AttrMap(
            urwid.LineBox(self.box, **self.frame_theme(self.frame_title)),
            "default"
        )
        self.loop = urwid.MainLoop(
            urwid.Frame(self.body),
            palette=monochrome_map if os.getenv("NO_COLOR") or self.prefs["monochrome"] else colormap,
            handle_mouse=self.prefs["mouse_integration"])


    def frame_theme(self, title=""):
        """
        Return the kwargs for a frame theme.
        """
        # TITLE
        theme = self.theme["frame"].copy()
        if theme["tline"] != "":
            theme.update({"title": title})
        return theme


    def set_header(self, text, *format_specs):
        """
        Update the header line with the logged in user, a seperator,
        then concat text with format_specs applied to it. Applies
        bar formatting to it.
        """
        header = ("{}@bbj | " + text).format(
            (network.user_name or "anonymous"),
            *format_specs
        )
        self.loop.widget.header = urwid.AttrMap(urwid.Text(header), "bar")


    def set_footer(self, string):
        """
        Sets the footer to display `string`, applying bar formatting.
        Other than setting the color, `string` is shown verbatim.
        """
        widget = urwid.AttrMap(urwid.Text(string), "bar")
        self.loop.widget.footer = widget
        # TODO: make this set the title line when the window is split
        # if self.window_split:
        #     self.loop.widget.footer[0].set_text(widget)
        # else:


    def set_default_header(self):
        """
        Sets the header to the default for the current screen.
        """
        if self.mode == "thread":
            name = self.usermap[self.thread["author"]]["user_name"]
            self.set_header("~{}: {}", name, self.thread["title"])
        else:
            self.set_header("{} threads", len(self.walker))


    def set_default_footer(self, clobber_composer=False):
        """
        Sets the footer to the default for the current screen.
        """
        if self.window_split and not clobber_composer:
            return

        elif self.mode == "thread":
            footer = bars["thread"] % self.prefs["jump_count"]
            if self.match_data["matches"]:
                footer += " [@#] Search Control"

        else:
            footer = bars["index"]

        self.set_footer(footer)


    def set_bars(self, clobber_composer=False):
        """
        Sets both the footer and header to their default values
        for the current mode.
        """
        self.set_default_header()
        self.set_default_footer(clobber_composer)


    def close_editor(self):
        """
        Close whatever editing widget is open and restore proper
        state back the walker.
        """
        if self.window_split:
            self.window_split = False
            self.loop.widget.focus_position = "body"
            self.set_footer(bars["thread"])
        else:
            self.loop.widget = self.loop.widget[0]
        self.set_default_header()


    def overlay_p(self):
        """
        Return True or False if the current widget is an overlay.
        """
        return isinstance(self.loop.widget, urwid.Overlay)


    def remove_overlays(self, *_):
        """
        Remove ALL urwid.Overlay objects which are currently covering the base
        widget.
        """
        while True:
            try:
                self.loop.widget = self.loop.widget[0]
            except:
                break


    def switch_editor(self):
        """
        Switch focus between the thread viewer and the open editor
        """
        pos = self.loop.widget.focus_position
        attr = ["bar" if pos == "body" else "30", "dim"]

        if not self.window_split:
            return

        elif pos == "body":
            self.loop.widget.focus_position = "footer"
            focus = "[focused on editor]"

        else:
            self.loop.widget.focus_position = "body"
            focus = "[focused on thread]"
            attr.reverse()

        self.loop.widget.footer[0].set_text(
            bars["edit_window"].format(
                self.prefs["edit_escapes"]["abort"].upper(),
                self.prefs["edit_escapes"]["focus"].upper(),
                self.prefs["edit_escapes"]["fhelp"].upper(),
                focus)
        )

        # HACK WHY WHY WHY WHYW HWY
        # this sets the focus color for the editor frame
        self.loop.widget.footer.contents[1][0].original_widget.attr_map = \
            self.loop.widget.footer.contents[0][0].attr_map = {None: attr[0]}
        self.loop.widget.header.attr_map = {None: attr[1]}
        self.body.attr_map = {None: attr[1]}


    def readable_delta(self, timestamp, compact=False):
        """
        Return a human-readable string representing the difference
        between a given epoch time and the current time.
        """
        # "New BBJ Features Thread by ~deltarae in 2024; ~dzwdz replied 15h ago; 4 total"
        # "<1m ago", "Xm ago", "Xh Ym ago", "Xd ago", "Xw ago" "Xm ago" "<datestamp>"
        delta = time() - timestamp
        hours, remainder = divmod(delta, 3600)
        if hours > 840: # 5 weeks
            return self.timestring(timestamp)
        elif hours > 336: # 2 weeks:
            return "%d%s ago" % (floor(hours / 168), "w" if compact else " weeks")
        elif hours > 168: # one week
            return "%d%s ago" % (floor(hours / 168), "w" if compact else " week")
        elif hours > 48:
            return "%d%s ago" % (floor(hours / 24), "d" if compact else " days")
        elif hours > 1:
            return "%d%s ago" % (hours, "h" if compact else " hours")
        elif hours == 1:
            return "1h ago" if compact else "about an hour ago"
        minutes, remainder = divmod(remainder, 60)
        if minutes > 1:
            return "%d%s ago" % (minutes, "m" if compact else " minutes")
        if minutes == 1:
            return "1m ago" if compact else "1 minute ago"
        return "<1m ago" if compact else "less than a minute ago"


    def quote_view_action(self, button, message):
        """
        Callback function to view a quote from the message object menu.
        """
        widget = OptionsMenu(
            ActionBox(urwid.SimpleFocusListWalker(self.make_message_body(message))),
            **self.frame_theme(">>%d" % message["post_id"])
        )

        self.loop.widget = urwid.Overlay(
            widget, self.loop.widget,
            align=("relative", 50),
            valign=("relative", 50),
            width=("relative", 98),
            height=("relative", 60)
        )


    def quote_view_menu(self, button, post_ids):
        """
        Receives a list of quote ids and makes a frilly menu to pick one to view.
        It retrieves messages objects from the thread and attaches them to a
        callback to `quote_view_action`
        """
        buttons = []
        for pid in post_ids:
            try:
                message = self.thread["messages"][pid]
                if len(post_ids) == 1:
                    return self.quote_view_action(button, message)
                author = self.usermap[message["author"]]
                label = [
                    ("button", ">>%d " % pid),
                    "(",
                    (str(author["color"]),
                     author["user_name"]),
                    ")"
                ]
                buttons.append(cute_button(label, self.quote_view_action, message))
            except IndexError:
                continue # users can submit >>29384234 garbage references

        widget = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker(buttons)),
            **self.frame_theme("View a Quote")
        )

        self.loop.widget = urwid.Overlay(
            widget, self.loop.widget,
            align=("relative", 50),
            valign=("relative", 50),
            height=len(buttons) + 3,
            width=30
        )


    def edit_post(self, button, message):
        post_id = message["post_id"]
        thread_id = message["thread_id"]
        # first we need to get the server's version of the message
        # instead of our formatted one
        try:
            message = network.edit_query(thread_id, post_id)
        except UserWarning as e:
            self.remove_overlays()
            return self.temp_footer_message(e.description)
        self.remove_overlays()
        self.compose(init_body=message["body"], edit=message)


    def reply(self, button, message):
        self.remove_overlays()
        self.compose(init_body=">>%d\n\n" % message["post_id"])


    def deletion_dialog(self, button, message):
        """
        Prompts the user to confirm deletion of an item.
        This can delete either a thread or a post.
        """
        op = message["post_id"] == 0
        buttons = [
            urwid.Text(("bold", "Delete this %s?" % ("whole thread" if op else "post"))),
            urwid.Divider(),
            cute_button(("10" , ">> Yes"), lambda _: [
                network.message_delete(message["thread_id"], message["post_id"]),
                self.remove_overlays(),
                self.index() if op else self.refresh()
            ]),
            cute_button(("30", "<< No"), self.remove_overlays)
        ]

        # TODO: create a central routine for creating popups. this is getting really ridiculous
        popup = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker(buttons)),
            **self.frame_theme())

        self.loop.widget = urwid.Overlay(
            popup, self.loop.widget,
            align=("relative", 50),
            valign=("relative", 50),
            width=30, height=6)


    def toggle_formatting(self, button, message):
        self.remove_overlays()
        raw = not message["send_raw"]
        network.set_post_raw(message["thread_id"], message["post_id"], raw)
        return self.refresh()


    def on_post(self, button, message):
        quotes = self.get_quotes(message)
        author = self.usermap[message["author"]]
        buttons = []

        if not self.window_split:
            buttons.append(urwid.Button("Reply", self.reply, message))

        if quotes and message["post_id"] != 0:
            buttons.append(urwid.Button(
                "View %sQuote" % ("a " if len(quotes) != 1 else ""),
                self.quote_view_menu, quotes))

        if network.can_edit(message["thread_id"], message["post_id"]) \
               and not self.window_split:

            if message["post_id"] == 0:
                msg = "Thread"
            else: msg = "Post"

            raw = message["send_raw"]
            buttons.insert(0, urwid.Button("Delete %s" % msg, self.deletion_dialog, message))
            buttons.insert(0, urwid.Button(
                "Enable Formatting" if raw else "Disable Formatting",
                self.toggle_formatting, message))
            buttons.insert(0, urwid.Button("Edit Post", self.edit_post, message))
            if network.user["is_admin"]:
                buttons.insert(0, urwid.Text(("20", "Reminder: You're an admin!")))

        if not buttons:
            return

        widget = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker(buttons)),
            **self.frame_theme(">>%d (%s)" % (message["post_id"], author["user_name"]))
        )
        size = self.loop.screen_size

        self.loop.widget = urwid.Overlay(
            urwid.AttrMap(widget, str(author["color"]*10)),
            self.loop.widget,
            align=("relative", 50),
            valign=("relative", 50),
            width=30,
            height=len(buttons) + 2
        )


    def get_quotes(self, msg_object, value_type=int):
        """
        Returns the post_ids that msg_object is quoting.
        Is a list, may be empty. ids are ints by default
        but can be passed `str` for strings.
        """
        quotes = []
        if msg_object["send_raw"]:
            return quotes
        for paragraph in msg_object["body"]:
            # yes python is lisp
            [quotes.append(cdr) for car, cdr in paragraph if car == "quote"]
        return [value_type(q) for q in quotes]


    def make_thread_body(self, thread, pinned=False):
        """
        Returns the pile widget that comprises a thread in the index.
        """
        button = cute_button(">>", self.thread_load, thread["thread_id"])
        if pinned == "server":
            title = urwid.AttrWrap(urwid.Text("[STICKY] " + thread["title"]), "20")
        elif pinned == "client":
            title = urwid.AttrWrap(urwid.Text("[*] " + thread["title"]), "50")
        else:
            title = urwid.Text(thread["title"])
        user = self.usermap[thread["author"]]
        last_author = self.usermap[thread["last_author"]]

        if self.prefs["information_density"] == "default":
            dateline = [
                ("default", "by "),
                (str(user["color"]), "~%s " % user["user_name"]),
                ("dim", "@ %s" % self.timestring(thread["created"]))
            ]

            infoline = "%d replies; active %s" % (
                thread["reply_count"],
                self.timestring(thread["last_mod"], "delta"))

            pile = [
                urwid.Columns([(3, urwid.AttrMap(button, "button", "hover")), title]),
                urwid.Text(dateline),
                urwid.Text(("dim", infoline)),
                urwid.Text([
                    ("dim", "last post by "),
                    (str(last_author["color"]), "~" + last_author["user_name"])
                ])
            ]

        elif self.prefs["information_density"] == "compact":
            firstline = urwid.Columns([
                (3, urwid.AttrMap(button, "button", "hover")),
                (len(title._text), title)
                ])
            secondline = urwid.Text([
                ("default", "by "),
                (str(user["color"]), "~%s " % user["user_name"]),
                ("dim", "@ %s; " % self.timestring(thread["created"])),
                "%d replies; active %s" % (
                    thread["reply_count"],
                    self.timestring(thread["last_mod"], "delta"),
                    )
            ])
            pile = [
                firstline,
                urwid.AttrMap(secondline, "dim"),
            ]

        elif self.prefs["information_density"] == "ultra":
            # for some reason, text overflowing to the right side of terminal
            # are deleted instead of being properly wrapped. but this is preferable
            # behviour to what it was doing IMHO
            info = urwid.Text([
                ("dim", "; "),
                (str(user["color"]), "~%s" % user["user_name"]),
                ("dim", " replied %s; " % self.timestring(thread["last_mod"], "delta", compact=True)),
                ("dim", "%d total" % thread["reply_count"])
                ])
            line = urwid.Columns([
                (3, urwid.AttrMap(button, "button", "hover")),
                (len(title.text), title),
                (len(info.text), info)])
            pile = [line]

        if self.prefs["information_density"] != "ultra" and self.prefs["thread_divider"]:
                pile.append(urwid.AttrMap(urwid.Divider(self.theme["divider"]), "dim"))

        if self.prefs["index_spacing"]:
            pile.insert(4, urwid.Divider())

        pile = urwid.Pile(pile)
        pile.thread = thread
        return pile


    def make_message_body(self, message, no_action=False):
        """
        Returns the widgets that comprise a message in a thread, including the
        text body, author info and the action button. Unlike the thread objects
        used in the index, this is not a pile widget, because using a pile
        causes line-by-line text scrolling to be unusable.
        """
        info = self.readable_delta(message["created"])
        if message["edited"]:
            info += " [edited]"

        if no_action:
            callback = ignore
            name = urwid_rainbows("~SYSTEM", True)
            color = "0"
        else:
            callback = self.on_post
            name = urwid.Text("~{}".format(self.usermap[message["author"]]["user_name"]))
            color = str(self.usermap[message["author"]]["color"])

        post = str(message["post_id"])
        head = urwid.Columns([
                (2 + len(post), urwid.AttrMap(
                    cute_button(">" + post, callback, message), "button", "hover")),
                (len(name._text) + 1, urwid.AttrMap(name, color)),
                urwid.AttrMap(urwid.Text(info), "dim")
            ])

        head.message = message
        return [
            head,
            urwid.Divider(),
            urwid.Padding(
                MessageBody(message),
                width=self.prefs["max_text_width"]),
            urwid.Divider(),
            urwid.AttrMap(urwid.Divider(self.theme["divider"]), "dim")
        ]


    def timestring(self, epoch, mode="both", compact=False):
        """
        Returns a string of time representing a given epoch and mode.
        """
        if mode == "delta":
            return self.readable_delta(epoch, compact)

        date = datetime.fromtimestamp(epoch)
        if mode == "time":
            directive = self.prefs["time"]
        elif mode == "date":
            directive = self.prefs["date"]
        else:
            directive = "%s %s" % ( self.prefs["time"], self.prefs["date"])
        return date.strftime(directive)


    def index(self, *_, threads=None):
        """
        Browse or return to the index.
        """
        if self.mode == "thread":
            # mark the current position in this thread before going back to the index
            mark()

        self.body.attr_map = {None: "default"}
        self.mode = "index"
        self.thread = None
        self.window_split = False
        if threads:
            # passing in an argument for threads implies that we are showing a
            # narrowed selection of content, so we dont want to resume last_index_pos
            self.last_index_pos = False
        else:
            threads, usermap = network.thread_index()
            self.usermap.update(usermap)
        self.walker.clear()

        server_pins = []
        client_pin_counter = 0

        for thread in threads:
            if thread["pinned"]:
                server_pins.append(thread)
            elif thread["thread_id"] in self.client_pinned_threads:
                self.walker.insert(client_pin_counter, self.make_thread_body(thread, pinned="client"))
                client_pin_counter += 1
            else:
                self.walker.append(self.make_thread_body(thread))

        # make sure these are always up top
        for index, thread in enumerate(server_pins):
            self.walker.insert(index, self.make_thread_body(thread, pinned="server"))

        self.set_bars(True)

        if self.last_index_pos:
            thread_ids = [widget.thread["thread_id"] for widget in self.walker]
            if self.last_index_pos in thread_ids:
                self.box.change_focus(self.loop.screen_size, thread_ids.index(self.last_index_pos))
                self.box.set_focus_valign("middle")
        elif self.walker:
            # checks to make sure there are any posts to focus
            self.box.set_focus(0)

        if self.immediate_thread_load :
            thread_id = self.immediate_thread_load.pop()
            self.last_index_pos = thread_id
            self.thread_load(None, thread_id, set_index=False)



    def thread_load(self, button, thread_id, set_index=True):
        """
        Open a thread.
        """
        if set_index and app.mode == "index":
            # make sure the index goes back to this selected thread
            pos = self.get_focus_post(return_widget=True)
            self.last_index_pos = pos.thread["thread_id"]

        if not self.window_split:
            self.body.attr_map = {None: "default"}

        self.mode = "thread"
        thread, usermap = network.thread_load(thread_id, format="sequential")
        self.usermap.update(usermap)
        self.thread = thread
        self.match_data["matches"].clear()
        self.walker.clear()
        for message in thread["messages"]:
            self.walker += self.make_message_body(message)
        self.set_default_header()
        self.set_default_footer()
        self.goto_post(mark(thread_id))


    def toggle_client_pin(self):
        if self.mode != "index":
            return
        thread_id = self.walker.get_focus()[0].thread["thread_id"]
        self.client_pinned_threads = toggle_client_pin(thread_id)
        self.index()


    def toggle_server_pin(self):
        if self.mode != "index" or not network.user["is_admin"]:
            return
        thread = self.walker.get_focus()[0].thread
        network.thread_set_pin(thread["thread_id"], not thread["pinned"])
        self.index()


    def search_index_callback(self, query):
        simple_query = query.lower().strip()
        threads, usermap = network.thread_index()
        self.usermap.update(usermap)
        results = [
            thread for thread in threads
                if simple_query in thread["title"].lower().strip()
        ]
        if results:
            self.index(threads=results)
            if query:
                self.set_header("Searching for '{}'", query)
        else:
            self.temp_footer_message("No results for '{}'".format(query))


    def search_thread_callback(self, query):
        # normally i would just use self.thread["messages"] but I need the visbile text post-formatted
        query = query.lower().strip()
        self.match_data["matches"] = [
            self.thread["messages"][widget.base_widget.post_id] for widget in self.walker
                if isinstance(widget.base_widget, MessageBody)
                and query in widget.base_widget.text.lower().strip()
        ]
        if self.match_data["matches"]:
            self.match_data["query"] = query
            self.match_data["position"] = -1
            # self.highlight_query()
            self.do_search_result()
        else:
            self.temp_footer_message("No results for '{}'".format(query))


    def do_search_result(self, forward=True):
        if not self.match_data["matches"]:
            return
        self.match_data["position"] += 1 if forward else -1
        length = len(self.match_data["matches"])
        if forward:
            if self.match_data["position"] == length:
                self.match_data["position"] = 0
        else:
            if self.match_data["position"] == -1:
                self.match_data["position"] = length - 1
        self.goto_post(self.match_data["matches"][self.match_data["position"]]["post_id"])
        self.temp_footer_message(
            "({}/{}) Searching for {} [#]Next [@]Previous".format(
                self.match_data["position"] + 1, length, self.match_data["query"]
            ), 5)


    # XXX: Try to find a way to overlay properties onto an existing widget instead of this trainwreck.
    # def highlight_query(self):
    #     # pass
    #     query = self.match_data["query"]
    #     for match in self.match_data["matches"]:
    #         widget = self.walker[match["post_id"] * 5 + 2].base_widget
    #         # (">>OP\n\nThat's a nice initiative x)", [('50', 4), (None, 2), ('default', 27)])
    #         text, attrs = widget.get_text()
    #         spans = [m.span() for m in re.finditer(query, text)]
    #         start, end = spans.pop(0)
    #         new_attrs = []
    #         index = 0
    #         for prop, length in attrs:
    #             if index and index > start:
    #                 index = end
    #                 new_attrs.append(("20", end - start))
    #                 start, end = spans.pop(0)
    #             else:
    #                 index += length
    #                 new_attrs.append((prop, length))


    def search_prompt(self):
        if self.mode == "index":
            callback = self.search_index_callback
        elif self.mode == "thread":
            callback = self.search_thread_callback
        else:
            return

        popup = OptionsMenu(
            urwid.ListBox(
                urwid.SimpleFocusListWalker([
                    urwid.Text(("button", "Enter a query:")),
                    urwid.AttrMap(StringPrompt(callback), "opt_prompt"),
                    urwid.Text("Use a blank query to reset the {}.".format(self.mode))
                ])),
            **self.frame_theme())

        self.loop.widget = urwid.Overlay(
            popup, self.loop.widget,
            align=("relative", 50),
            valign=("relative", 25 if self.window_split else 50),
            width=("relative", 40), height=6)


    def refresh(self):
        self.remove_overlays()
        if self.mode == "index":
            # check to make sure there are any posts
            if self.walker:
                self.last_index_pos = self.get_focus_post(True).thread["thread_id"]
            self.index()
        else:
            mark()
            thread = self.thread["thread_id"]
            self.thread_load(None, thread)
            self.goto_post(mark(thread))
        self.temp_footer_message("Refreshed content!", 1)


    def back(self, terminate=False):
        if app.mode == "index" and terminate:
            frilly_exit()

        elif self.overlay_p():
            self.loop.widget = self.loop.widget[0]

        elif self.window_split:
            # display a confirmation dialog before killing off an in-progress post
            buttons = [
                urwid.Text(("bold", "Discard current post?")),
                urwid.Divider(),
                cute_button(("10" , ">> Yes"), lambda _: [
                    self.remove_overlays(),
                    self.index()
                ]),
                cute_button(("30", "<< No"), self.remove_overlays)
            ]

            # TODO: create a central routine for creating popups. this is getting really ridiculous
            popup = OptionsMenu(
                urwid.ListBox(urwid.SimpleFocusListWalker(buttons)),
                **self.frame_theme())

            self.loop.widget = urwid.Overlay(
                popup, self.loop.widget,
                align=("relative", 50),
                valign=("relative", 25),
                width=30, height=6)

        else:
            mark()
            self.index()


    def get_focus_post(self, return_widget=False):
        pos = self.box.get_focus_path()[0]
        if self.mode == "thread":
            return (pos - (pos % 5)) // 5
        return pos if not return_widget else self.walker[pos]


    def header_jump_next(self):
        if self.mode == "index":
            return self.box.keypress(self.loop.screen_size, "down")
        for x in range(self.prefs["jump_count"]):
            post = self.get_focus_post()
            if post != self.thread["reply_count"]:
                self.goto_post(post + 1)
            else: break


    def header_jump_previous(self):
        if self.mode == "index":
            return self.box.keypress(self.loop.screen_size, "up")
        for x in range(self.prefs["jump_count"]):
            post = self.get_focus_post()
            if post != 0:
                self.goto_post(post - 1)
            else: break


    def goto_post(self, number, size=(0, 0)):
        if self.mode != "thread":
            return

        size = size if size else self.loop.screen_size
        new_pos = number * 5
        cur_pos = self.box.get_focus_path()[0]

        try:
            self.box.change_focus(
                size, new_pos, coming_from=
                "below" if (cur_pos < new_pos) else "above")
        except IndexError:
            self.temp_footer_message("OUT OF BOUNDS")


    def goto_post_prompt(self, init):
        if self.mode != "thread":
            return

        count = self.thread["reply_count"]
        live_display = urwid.Text("")
        edit = JumpPrompt(count, lambda x: self.goto_post(x))
        items = [
            urwid.Text(("button", "   Jump to post")),
            urwid.AttrMap(edit, "opt_prompt"),
            urwid.Text(("bold", ("(max %d)" % count).center(18, " "))),
            live_display
        ]

        urwid.connect_signal(edit, "change", self.jump_peek, live_display)
        if init.isdigit():
            edit.keypress((self.loop.screen_size[0],), init)

        popup = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker(items)),
            **self.frame_theme())

        self.loop.widget = urwid.Overlay(
            popup, self.loop.widget,
            align=("relative", 50),
            valign=("relative", 25 if self.window_split else 50),
            width=20, height=6)


    def jump_peek(self, editor, value, display):
        if not value:
            return display.set_text("")
        msg = self.thread["messages"][int(value)]
        author = self.usermap[msg["author"]]
        display.set_text((str(author["color"]), ">>%s %s" % (value, author["user_name"])))


    def set_theme(self, button, new_state):
        """
        Callback for the theme radio buttons in the options.
        """
        if new_state == True:
            self.theme = themes[button.label].copy()
            if self.prefs["custom_divider_char"]:
                self.theme["divider"] = self.prefs["custom_divider_char"]
            self.prefs["frame_theme"] = button.label
            bbjrc("update", **self.prefs)


    def set_new_editor(self, button, value, arg):
        """
        Callback for the option radio buttons to set the the text editor.
        """
        if value == False:
            return
        elif isinstance(value, str):
            [button.set_state(False) for button in arg]
            self.prefs["editor"] = value
            bbjrc("update", **self.prefs)
            return

        key, widget = arg
        widget.set_edit_text(key)
        self.prefs.update({"editor": key})
        bbjrc("update", **self.prefs)


    def set_editor_mode(self, button, value):
        """
        Callback for the editor mode radio buttons in the options.
        """
        self.prefs["integrate_external_editor"] = value
        bbjrc("update", **self.prefs)


    def set_density(self, button, new_state):
        if new_state == True:
            self.prefs["information_density"] = button.label
            bbjrc("update", **self.prefs)


    def toggle_thread_pin(self, thread_id):
        pass


    def relog(self, *_, **__):
        """
        Options menu callback to log the user in again.
        Drops back to text mode because im too lazy to
        write a responsive urwid thing for this.
        """
        self.loop.widget = self.loop.widget[0]
        self.loop.stop()
        call("clear", shell=True)
        print(welcome_monochrome if self.prefs["monochrome"] or os.getenv("NO_COLOR") else welcome)
        try:
            log_in(relog=True)
        except (KeyboardInterrupt, InterruptedError):
            pass
        self.loop.start()
        self.set_default_header()
        self.options_menu()


    def unlog(self, *_, **__):
        """
        Options menu callback to anonymize the user and
        then redisplay the options menu.
        """
        network.user_name = network.user_auth = None
        network.user = network("get_me")["data"]
        self.loop.widget = self.loop.widget[0]
        self.set_default_header()
        self.options_menu()


    def general_help(self):
        """
        Show a general help dialog. In all honestly, its not
        very useful and will only help people who have never
        really used terminal software before =)
        """
        widget = OptionsMenu(
            urwid.ListBox(
                urwid.SimpleFocusListWalker([
                    urwid_rainbows(
                        "This is BBJ, a client/server textboard made for tildes!",
                        True),
                    # urwid.Text(("dim", "...by ~desvox")),
                    urwid.Divider(self.theme["divider"]),
                    urwid.Button("Post Formatting Help", self.formatting_help),
                    urwid.Divider(self.theme["divider"]),
                    urwid.Text(general_help)
                ])),
            **self.frame_theme("?????")
        )

        app.loop.widget = urwid.Overlay(
            widget, app.loop.widget,
            align=("relative", 50),
            valign=("relative", 50),
            width=30,
            height=("relative", 60)
        )


    def formatting_help(self, *_):
        """
        Pops a help window for formatting directives.
        """
        # we can "recycle" the server's formatting abilities to
        # use the same syntax for the help text itself
        message = network.fake_message(
            "\n\n".join(format_help), format="sequential")

        widget = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker(app.make_message_body(message, True))),
            **self.frame_theme("Formatting Help")
        )

        va = 5 if self.window_split else 50
        vh = 45 if self.window_split else 75
        app.loop.widget = urwid.Overlay(
            widget, app.loop.widget,
            align=("relative", 50),
            valign=("relative", va),
            width=self.prefs["max_text_width"],
            height=("relative", vh)
        )


    def set_color(self, button, value, color):
        if value == False:
            return
        network.user_update(color=color)


    def toggle_exit(self, button, value):
        self.prefs["dramatic_exit"] = value
        bbjrc("update", **self.prefs)


    def toggle_anon_warn(self, button, value):
        self.prefs["confirm_anon"] = value
        bbjrc("update", **self.prefs)


    def toggle_monochrome(self, button, value):
        self.prefs["monochrome"] = value
        self.loop.screen.register_palette(monochrome_map if value else colormap)
        self.loop.screen.clear()
        bbjrc("update", **self.prefs)


    def toggle_mouse(self, button, value):
        self.prefs["mouse_integration"] = value
        self.loop.handle_mouse = value
        self.loop.screen.set_mouse_tracking(value)
        bbjrc("update", **self.prefs)


    def toggle_spacing(self, button, value):
        self.prefs["index_spacing"] = value
        bbjrc("update", **self.prefs)

    def toggle_thread_divider(self, button, value):
        self.prefs["thread_divider"] = value
        bbjrc("update", **self.prefs)


    def change_username(self, *_):
        self.loop.stop()
        call("clear", shell=True)
        try:
            name = nameloop("Choose a new username", True)
            network.user_update(user_name=name)
            print_rainbows("~~hello there %s~~" % name)
            sleep(0.8)
            self.loop.start()
            self.loop.widget = self.loop.widget[0]
            self.index()
            self.options_menu()
        except (KeyboardInterrupt, InterruptedError):
            self.loop.start()


    def change_password(self, *_):
        self.loop.stop()
        call("clear", shell=True)
        try:
            password = password_loop("Choose a new password. Can be empty", True)
            network.user_update(auth_hash=network._hash(password))
            print_rainbows("SET NEW PASSWORD")
            sleep(0.8)
            self.loop.start()
            self.loop.widget = self.loop.widget[0]
            self.index()
            self.options_menu()
        except (KeyboardInterrupt, InterruptedError):
            self.loop.start()


    def live_time_render(self, editor, text, args):
        widget, key = args
        try:
            rendered = datetime.fromtimestamp(time()).strftime(text)
            self.prefs[key] = text
            bbjrc("update", **self.prefs)
        except:
            rendered = ("1", "Invalid Input")
        widget.set_text(rendered)


    def edit_width(self, editor, content):
        value = int(content) if content else 0
        if value < 10: value = 10
        self.prefs["max_text_width"] = value
        bbjrc("update", **self.prefs)


    def edit_shift(self, editor, content):
        self.prefs["shift_multiplier"] = \
            int(content) if content else 0
        bbjrc("update", **self.prefs)


    def save_escape_key(self, value, mode):
        self.prefs["edit_escapes"].update({mode[0]: value})
        bbjrc("update", **self.prefs)


    def set_escape_key(self, button, args):
        mode = args[0]
        widget = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker([
                urwid.Text("Press Enter when done"),
                urwid.AttrMap(KeyPrompt(
                    self.prefs["edit_escapes"][mode],
                    self.save_escape_key,
                    [mode]
                ), "opt_prompt")])),
            **self.frame_theme("Set key for " + mode)
        )

        app.loop.widget = urwid.Overlay(
            urwid.AttrMap(widget, "30"),
            app.loop.widget,
            align=("relative", 50),
            valign=("relative", 50),
            width=25, height=5
        )


    def incr_jump(self):
        if self.mode != "thread":
            return

        value = self.prefs["jump_count"] * 2
        if value > 64:
            value = 1

        self.prefs["jump_count"] = value
        self.set_default_footer()
        bbjrc("update", **self.prefs)


    def decr_jump(self):
        if self.mode != "thread":
            return

        value = self.prefs["jump_count"] // 2
        if value < 1:
            value = 64

        self.prefs["jump_count"] = value
        self.set_default_footer()
        bbjrc("update", **self.prefs)


    def options_menu(self):
        """
        Create a popup for the user to configure their account and
        display settings.
        """
        editor_buttons = []
        edit_mode = []

        if network.user_auth:
            account_message = "Logged in as %s." % network.user_name
            account_stuff = [
                urwid.Button("Relog", on_press=self.relog),
                urwid.Button("Go anonymous", on_press=self.unlog),
                urwid.Button("Change username", on_press=self.change_username),
                urwid.Button("Change password", on_press=self.change_password),
                urwid.Divider(),
                urwid.Text(("button", "Your color:")),
                urwid.Text(("default", "This color will show on your "
                            "post headers and when people quote you.")),
                urwid.Divider()
            ]

            user_colors = []
            for index, color in enumerate(colornames):
                urwid.RadioButton(
                    user_colors, color.title(),
                    network.user["color"] == index,
                    self.set_color, index)

            for item in user_colors:
                account_stuff.append(item)

        else:
            account_message = "You're browsing anonymously, and cannot set account preferences."
            account_stuff = [urwid.Button("Login/Register", on_press=self.relog)]

        density_buttons = []
        for value in ["default", "compact", "ultra"]:
            urwid.RadioButton(
                density_buttons, value,
                state=self.prefs["information_density"] == value,
                on_state_change=self.set_density
                # user_data=value
            )

        theme_buttons = []
        for name, theme in themes.items():
            urwid.RadioButton(
                theme_buttons, name,
                state=theme["frame"] == self.theme["frame"],
                on_state_change=self.set_theme
            )

        time_box = urwid.Text(self.timestring(time(), "time"))
        time_edit = Prompt(edit_text=self.prefs["time"])
        urwid.connect_signal(time_edit, "change", self.live_time_render, (time_box, "time"))

        date_box = urwid.Text(self.timestring(time(), "date"))
        date_edit = Prompt(edit_text=self.prefs["date"])
        urwid.connect_signal(date_edit, "change", self.live_time_render, (date_box, "date"))

        time_stuff = [
            urwid.Text(("button", "Time Format")),
            time_box, urwid.AttrMap(time_edit, "opt_prompt"),
            urwid.Divider(),
            urwid.Text(("button", "Date Format")),
            date_box, urwid.AttrMap(date_edit, "opt_prompt"),
        ]

        width_edit = urwid.IntEdit(default=self.prefs["max_text_width"])
        urwid.connect_signal(width_edit, "change", self.edit_width)

        shift_edit = urwid.IntEdit(default=self.prefs["shift_multiplier"])
        urwid.connect_signal(shift_edit, "change", self.edit_shift)

        editor_display = Prompt(edit_text=self.prefs["editor"])
        urwid.connect_signal(editor_display, "change", self.set_new_editor, editor_buttons)
        for editor in editors:
            urwid.RadioButton(
                editor_buttons, editor,
                state=self.prefs["editor"] == editor,
                on_state_change=self.set_new_editor,
                user_data=(editor, editor_display))

        urwid.RadioButton(
            edit_mode, "Integrate",
            state=self.prefs["integrate_external_editor"],
            on_state_change=self.set_editor_mode)

        urwid.RadioButton(
            edit_mode, "Overthrow",
            state=not self.prefs["integrate_external_editor"])

        content = []

        for item in [urwid.Text(("opt_header", "Account"), 'center'),
                     urwid.Text(account_message),
                     urwid.Divider()]:
            content.append(item)

        for item in account_stuff:
            content.append(item)

        for item in [urwid.Divider(self.theme["divider"]),
                     urwid.Text(("opt_header", "App"), 'center'),
                     urwid.Divider(),
                     urwid.CheckBox(
                         "Monochrome mode",
                         state=self.prefs["monochrome"],
                         on_state_change=self.toggle_monochrome
                     ),
                     urwid.CheckBox(
                         "Dump rainbows on exit",
                         state=self.prefs["dramatic_exit"],
                         on_state_change=self.toggle_exit
                     ),
                     urwid.CheckBox(
                         "Warn when posting anonymously",
                         state=self.prefs["confirm_anon"],
                         on_state_change=self.toggle_anon_warn
                     ),
                     urwid.CheckBox(
                         "Increase index padding",
                         state=self.prefs["index_spacing"],
                         on_state_change=self.toggle_spacing
                     ),
                     urwid.CheckBox(
                         "Use dividers in thread list",
                         state=self.prefs["thread_divider"],
                         on_state_change=self.toggle_thread_divider
                     ),
                     urwid.CheckBox(
                         "Handle mouse (disrupts URL clicking)",
                         state=self.prefs["mouse_integration"],
                         on_state_change=self.toggle_mouse
                     ),
                     urwid.Divider()]:
            content.append(item)

        for item in [urwid.Text(("button", "Border Theme")),
                     urwid.Text("Restart to fully apply.")]:
            content.append(item)


        for item in theme_buttons:
            content.append(item)

        content.append(urwid.Divider())

        content.append(urwid.Text(("button", "Information Density")))
        for item in density_buttons:
            content.append(item)

        content.append(urwid.Divider())

        for item in time_stuff:
            content.append(item)

        for item in [urwid.Divider(),
                     urwid.Text(("button", "Max message width:")),
                     urwid.AttrMap(width_edit, "opt_prompt"),
                     urwid.Divider(),
                     urwid.Text(("button", "Scroll multiplier when holding shift or scrolling with the mouse:")),
                     urwid.AttrMap(shift_edit, "opt_prompt"),
                     urwid.Divider(),
                     urwid.Text(("button", "Text editor:")),
                     urwid.Text("You can type in your own command or use one of these presets."),
                     urwid.Divider(),
                     urwid.AttrMap(editor_display, "opt_prompt")]:
            content.append(item)

        for item in editor_buttons:
            content.append(item)

        for item in [urwid.Divider(),
                     urwid.Text(("button", "Internal Editor Escape Keys:")),
                     urwid.Text("You can change these keybinds to whatever "
                                "you want. Just remember that these will "
                                "shadow over the text editor itself."),
                     urwid.Divider(),
                     urwid.Button("Abort", self.set_escape_key, ["abort"]),
                     urwid.Button("Change Focus", self.set_escape_key, ["focus"]),
                     urwid.Button("Formatting Help", self.set_escape_key, ["fhelp"])]:
            content.append(item)

        for item in [urwid.Divider(),
                     urwid.Text(("button", "External text editor mode:")),
                     urwid.Text("If you have problems using an external text editor, "
                                "set this to Overthrow."),
                     urwid.Divider()]:
            content.append(item)

        for item in edit_mode:
            content.append(item)

        content.append(urwid.Divider(self.theme["divider"]))

        widget = OptionsMenu(
            urwid.ListBox(urwid.SimpleFocusListWalker(content)),
            **self.frame_theme("Options"))

        self.loop.widget = urwid.Overlay(
            widget, self.loop.widget,
            align="center",
            valign="middle",
            width=30,
            height=("relative", 75)
        )


    def footer_prompt(self, text, callback, *callback_args, extra_text=None):
        text = "(%s)> " % text
        widget = urwid.Columns([
            (len(text), urwid.AttrMap(urwid.Text(text), "bar")),
            FootPrompt(callback, *callback_args)
        ])

        if extra_text:
            widget = urwid.Pile([
                urwid.AttrMap(urwid.Text(extra_text), "2"),
                widget
            ])

        self.loop.widget.footer = widget
        self.loop.widget.focus_position = "footer"


    def reset_footer(self, *_):
        if self.window_split:
            return
        self.set_default_footer()
        # try:
            # self.loop.widget.focus_position = "body"
        # except:
            # just keep trying until the focus widget can handle it
            # return self.loop.set_alarm_in(0.25, self.reset_footer)


    def temp_footer_message(self, string, duration=3):
        self.loop.remove_alarm(self.last_alarm)
        self.last_alarm = self.loop.set_alarm_in(duration, self.reset_footer)
        if self.window_split:
            pass
        else:
            self.set_footer(string)


    def overthrow_ext_edit(self, init_body=""):
        """
        Opens the external editor, but instead of integreating it into the app,
        stops the mainloop and blocks until the editor is killed. Returns the
        body of text the user composed.
        """
        self.loop.stop()
        descriptor, path = tempfile.mkstemp()
        with open(path, "w") as _:
            _.write(init_body)
        call("export LANG=en_US.UTF-8; %s %s" % (self.prefs["editor"], path), shell=True)
        with open(path) as _:
            body = _.read()
        os.remove(path)
        self.loop.start()
        return body.strip()


    def compose(self, title=None, init_body="", edit=False):
        """
        Dispatches the appropriate composure mode and widget based on application
        context and user preferences.
        """
        if self.mode == "index" and not title:
            return self.footer_prompt("Title", self.compose)

        elif title:
            try: network.validate("title", title)
            except AssertionError as e:
                return self.footer_prompt(
                    "Title", self.compose, extra_text=e.description)

        if not self.prefs["integrate_external_editor"]:
            body = self.overthrow_ext_edit(init_body)
            if not body or re.search("^>>[0-9]+$", body):
                return self.temp_footer_message("EMPTY POST DISCARDED")
            params = {"body": body}

            if self.mode == "thread" and not edit:
                endpoint = "thread_reply"
                params.update({"thread_id": self.thread["thread_id"]})

            elif edit:
                endpoint = "edit_post"
                params.update({
                    "thread_id": self.thread["thread_id"],
                    "post_id": edit["post_id"]
                })

            else:
                endpoint = "thread_create"
                params.update({"title": title})

            network.request(endpoint, **params)
            self.refresh()
            if edit:
                self.goto_post(edit["post_id"])

            elif self.mode == "thread":
                self.goto_post(self.thread["reply_count"])

            else:
                self.box.keypress(self.loop.screen_size, "t")
            return

        if self.mode == "index":
            self.set_header('Composing "{}"', title)
            self.set_footer("[{}]Abort [{}]Formatting Help [Save and quit to submit your thread]".format(
                self.prefs["edit_escapes"]["abort"].upper(), self.prefs["edit_escapes"]["fhelp"].upper()
            ))
            self.loop.widget = urwid.Overlay(
                urwid.LineBox(
                    ExternalEditor("thread_create", title=title),
                    **self.frame_theme(self.prefs["editor"] or "")),
                self.loop.widget,
                align="center",
                valign="middle",
                width=("relative", 90),
                height=("relative", 80))
            return

        params = {"thread_id": self.thread["thread_id"]}

        if edit:
            _id = edit["post_id"]
            params.update({"post_id": _id})
            header = ["Editing your post; >>{}", _id]
            endpoint = "edit_post"
        else:
            header = ['Replying to "{}"', self.thread["title"]]
            endpoint = "thread_reply"

        self.loop.widget.footer = urwid.Pile([
            urwid.AttrMap(urwid.Text(""), "bar"),
            urwid.BoxAdapter(
                urwid.AttrMap(
                    urwid.LineBox(
                        ExternalEditor(endpoint, init_body=init_body, **params),
                        **self.frame_theme()
                    ), "bar"),
                self.loop.screen_size[1] // 2)])

        self.set_header(*header)
        self.window_split=True
        self.switch_editor()


class MessageBody(urwid.Text):
    """
    An urwid.Text object that works with the BBJ formatting directives.
    """
    def __init__(self, message):
        if message["send_raw"]:
            return super(MessageBody, self).__init__(message["body"])

        self.post_id = message["post_id"]
        text_objects = message["body"]
        result = []
        last_directive = None
        for paragraph in text_objects:
            for directive, body in paragraph:

                if directive in colornames:
                    color = str(colornames.index(directive))
                    result.append((color, body))

                elif directive == "dim":
                    result.append((directive, body))

                elif directive in ["underline", "bold"]:
                    result.append((directive, body))

                elif directive == "linequote":
                    result.append(("3", "%s" % body.strip()))
                    # TEN MILLION YEARS DUNGEON NO TRIAL
                    # try:
                        # this /naughty/ hack is supposed to keep spacing consistent....needs tweaking
                        # if result[-1][-1][-1] != "\n":
                        #     result.append(("default", "\n"))
                    # except IndexError:
                    #     pass

                elif directive == "quote":
                    if message["post_id"] == 0:
                        # Quotes in OP have no meaning, just insert them plainly
                        result.append(("default", ">>%s" % body))
                        continue
                    elif body == "0":
                        # quoting the OP, lets make it stand out a little
                        result.append(("50", ">>OP"))
                        continue

                    color = "2"
                    try:
                        # we can get this quote by its index in the thread
                        message = app.thread["messages"][int(body)]
                        user = app.usermap[message["author"]]
                        # try to get the user's color, if its default use the normal one
                        _c = user["color"]
                        if _c != 0:
                            color = str(_c)

                        if user != "anonymous" and user["user_name"] == network.user_name:
                            display = "[You]"
                            # bold it
                            color += "0"
                        else:
                            display = "[%s]" % user["user_name"]
                    except: # the quote may be garbage and refer to a nonexistant post
                        display = ""
                    result.append((color, ">>%s%s" % (body, display)))

                elif directive == "rainbow":
                    color = 1
                    for char in body:
                        if color == 7:
                            color = 1
                        result.append((str(color), char))
                        color += 1

                else:
                    result.append(("default", body))
                last_directive = directive
            result.append("\n\n")
        result.pop() # lazily ensure \n\n between paragraphs but not at the end
        super(MessageBody, self).__init__(result)


class KeyPrompt(urwid.Edit):
    """
    Allows setting the value of the editor to any
    keybinding that is pressed. Is used to customize
    keybinds across the client.
    """
    def __init__(self, initkey, callback, *callback_args):
        super(KeyPrompt, self).__init__()
        self.set_edit_text(initkey)
        self.callback = callback
        self.args = callback_args

    def keypress(self, size, key):
        if key == "enter":
            self.callback(self.get_edit_text(), *self.args)
            app.loop.widget = app.loop.widget[0]
        else:
            self.set_edit_text(key)


class Prompt(urwid.Edit):
    """
    Supports basic bashmacs keybinds. Key casing is
    ignored and ctrl/alt are treated the same. Only
    character-wise (not word-wise) movements are
    implemented.
    """
    def keypress(self, size, key):
        if not super(Prompt, self).keypress(size, key):
            return

        elif key[0:4] not in ("meta", "ctrl"):
            return key

        column = self.get_cursor_coords((app.loop.screen_size[0],))[0]
        text = self.get_edit_text()
        key = key[-1].lower()

        if key == "u":
            self.set_edit_pos(0)
            self.set_edit_text(text[column:])

        elif key == "k":
            self.set_edit_text(text[:column])

        elif key == "f":
            self.keypress(size, "right")

        elif key == "b":
            self.keypress(size, "left")

        elif key == "a":
            self.set_edit_pos(0)

        elif key == "e":
            self.set_edit_pos(len(text))

        elif key == "d":
            self.set_edit_text(text[0:column] + text[column+1:])

        return key


class FootPrompt(Prompt):
    def __init__(self, callback, *callback_args):
        super(FootPrompt, self).__init__()
        self.callback = callback
        self.args = callback_args


    def keypress(self, size, key):
        super(FootPrompt, self).keypress(size, key)
        if key == "enter":
            app.loop.widget.focus_position = "body"
            app.set_default_footer()
            self.callback(self.get_edit_text(), *self.args)

        elif key.lower() in ("esc", "ctrl g", "ctrl c"):
            app.loop.widget.focus_position = "body"
            app.set_default_footer()


class StringPrompt(Prompt, urwid.Edit):
    def __init__(self, callback, *callback_args):
        super(StringPrompt, self).__init__()
        self.callback = callback
        self.args = callback_args


    def keypress(self, size, key):
        keyl = key.lower()
        if key == "enter":
            app.remove_overlays()
            self.callback(self.get_edit_text(), *self.args)

        elif keyl in ("esc", "ctrl g", "ctrl c"):
            app.remove_overlays()

        else:
            super(StringPrompt, self).keypress((size[0],), key)


class JumpPrompt(Prompt, urwid.IntEdit):
    def __init__(self, max_length, callback, *callback_args):
        super(JumpPrompt, self).__init__()
        self.max_length = max_length
        self.callback = callback
        self.args = callback_args


    def valid_char(self, char):
        if not (len(char) == 1 and char in "0123456789"):
            return False
        elif int(self.get_edit_text() + char) <= self.max_length:
            return True
        try:
            # flash the display text to indicate bad value
            text = app.loop.widget.top_w.original_widget.body[2]
            body = text.get_text()[0]
            for attr in ("button", "20", "button", "bold"):
                text.set_text((attr, body))
                app.loop.draw_screen()
                sleep(0.05)
        except: # fuck it who cares
            pass
        return False


    def incr(self, direction):
        value = self.value()
        if direction == "down" and value > 0:
            value = str(value - 1)
            self.set_edit_text(value)

        elif direction == "up" and value < self.max_length:
            value = str(value + 1)
            self.set_edit_text(value)

        else:
            return

        self.set_edit_pos(len(value))


    def keypress(self, size, key):
        keyl = key.lower()
        if key == "enter":
            app.remove_overlays()
            self.callback(self.value(), *self.args)

        elif keyl in ("q", "esc", "ctrl g", "ctrl c"):
            app.remove_overlays()

        elif keyl in ("down", "ctrl n", "n", "j"):
            self.incr("down")

        elif keyl in ("up", "ctrl p", "p", "k"):
            self.incr("up")

        else: # dont use super because we want to allow zeros in this box
            urwid.Edit.keypress(self, (size[0],), key)


class ExternalEditor(urwid.Terminal):
    def __init__(self, endpoint, **params):
        self.file_descriptor, self.path = tempfile.mkstemp()
        with open(self.path, "w") as _:
            if params.get("init_body"):
                init_body = params.pop("init_body")
            else:
                init_body = ""
            _.write(init_body)

        self.endpoint = endpoint
        self.params = params
        env = os.environ
        # OLD: barring this, programs will happily spit out unicode chars which
        # urwid+python3 seem to choke on. This seems to be a bug on urwid's
        # behalf. Users who take issue to programs trying to supress unicode
        # should use the options menu to switch to Overthrow mode.
        # OLD env.update({"LANG": "POSIX"})
        command = ["bash", "-c", "{} {}; echo Press any key to kill this window...".format(
            app.prefs["editor"], self.path)]
        super(ExternalEditor, self).__init__(command, env, app.loop, app.prefs["edit_escapes"]["abort"])
        urwid.connect_signal(self, "closed", self.exterminate)


    # def confirm_anon(self, button, value):
    #     app.loop.widget = app.loop.widget[0]
    #     if not value:
    #         app.loop.stop()
    #         call("clear", shell=True)
    #         print(welcome)
    #         log_in(True)
    #         app.loop.start()
    #     self.exterminate(anon_confirmed=True)


    def exterminate(self, *_, anon_confirmed=False):
        if app.prefs["confirm_anon"] \
           and not anon_confirmed    \
           and network.user["user_name"] == "anonymous":
            # TODO fixoverlay: urwid terminal widgets have been mucking
            # up overlay dialogs since the wee days of bbj, i really
            # need to find a real solution instead of dodging the issue
            # constantly
            # if app.window_split:
            #     buttons = [
            #         urwid.Text(("bold", "Post anonymously?")),
            #         urwid.Text("(settings can disable this warning)"),
            #         urwid.Divider(),
            #         cute_button(("20" , ">> Yes"), self.confirm_anon, True),
            #         cute_button(("20", "<< Log in"), self.confirm_anon, False)
            #     ]

            #     popup = OptionsMenu(
            #         urwid.ListBox(urwid.SimpleFocusListWalker(buttons)),
            #         **frame_theme())

            #     app.loop.widget = urwid.Overlay(
            #         popup, app.loop.widget,
            #         align=("relative", 50),
            #         valign=("relative", 20),
            #         width=20, height=6)

            #     return
            # else:
            app.loop.stop()
            call("clear", shell=True)
            print(anon_warn_monochrome if app.prefs["monochrome"] or os.getenv("NO_COLOR") else anon_warn)
            choice = paren_prompt(
                "Post anonymously?", default="yes", choices=["Yes", "no"]
            )
            if choice == "n":
                log_in(True)
            app.loop.start()

        app.close_editor()
        with open(self.path) as _:
            body = _.read().strip()
        os.remove(self.path)

        if body and not re.search("^>>[0-9]+$", body):
            self.params.update({"body": body})
            network.request(self.endpoint, **self.params)
            if self.endpoint == "edit_post":
                app.refresh()
                app.goto_post(self.params["post_id"])

            elif app.mode == "thread":
                app.refresh()
                app.goto_post(app.thread["reply_count"])

            else:
                app.last_pos = None
                app.index()
        else:
            app.temp_footer_message("EMPTY POST DISCARDED")


    def keypress(self, size, key):
        """
        The majority of the things the parent keypress method will do is
        either erroneous or disruptive to my own usage. I've plucked out
        the necessary bits and, most importantly, have changed from
        ASCII encoding to utf8 when writing to the child process.
        """
        if self.terminated:
            return

        self.term.scroll_buffer(reset=True)
        keyl = key.lower()

        if keyl == "ctrl l":
            # always do this, and also pass it to the terminal
            wipe_screen()

        elif key == app.prefs["edit_escapes"]["abort"]:
            self.terminate()
            app.close_editor()
            return app.refresh()

        elif key == app.prefs["edit_escapes"]["focus"]:
            return app.switch_editor()

        elif key == app.prefs["edit_escapes"]["fhelp"]:
            return app.formatting_help()

        elif keyl == "ctrl z":
            return os.killpg(os.getpgid(os.getpid()), 19)

        single_char = len(key) == 6
        if key.startswith("ctrl ") and single_char:
            if key[-1].islower():
                key = chr(ord(key[-1]) - ord("a") + 1)
            else:
                key = chr(ord(key[-1]) - ord("A") + 1)

        elif key.startswith("meta ") and single_char:
            key = urwid.vterm.ESC + key[-1]

        elif key in urwid.vterm.KEY_TRANSLATIONS:
            key = urwid.vterm.KEY_TRANSLATIONS[key]

        elif key in escape_map:
            key = escape_map[key]

        if self.term_modes.lfnl and key == "\x0d":
            key += "\x0a"

        os.write(self.master, key.encode("utf8"))


    def __del__(self):
        """
        Make damn sure we scoop up after ourselves here...
        """
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


class OptionsMenu(urwid.LineBox):
    def keypress(self, size, key):
        keyl = key.lower()
        if keyl in ("esc", "ctrl g"):
            app.loop.widget = app.loop.widget[0]
        # try to let the base class handle the key, if not, we'll take over
        elif not super(OptionsMenu, self).keypress(size, key):
            return

        elif key in ("shift down", "J", "N"):
            for x in range(app.prefs["shift_multiplier"]):
                self.keypress(size, "down")

        elif key in ("shift up", "K", "P"):
            for x in range(app.prefs["shift_multiplier"]):
                self.keypress(size, "up")

        elif key in ("ctrl n", "j", "n"):
            return self.keypress(size, "down")

        elif key in ("ctrl p", "k", "p"):
            return self.keypress(size, "up")

        elif keyl in ("left", "h", "q"):
            app.loop.widget = app.loop.widget[0]

        elif keyl in ("right", "l"):
            return self.keypress(size, "enter")

        elif keyl == "ctrl l":
            wipe_screen()


    def mouse_event(self, size, event, button, x, y, focus):
        if super(OptionsMenu, self).mouse_event(size, event, button, x, y, focus):
            return
        if button == 4:
            self.keypress(size, "up")

        elif button == 5:
            self.keypress(size, "down")


class ActionBox(urwid.ListBox):
    """
    The listwalker used by all the browsing pages. Most of the application
    takes place in an instance of this box. Handles many keybinds.
    """
    def keypress(self, size, key):
        super(ActionBox, self).keypress(size, key)
        overlay = app.overlay_p()
        keyl = key.lower()

        if key in ("j", "n", "ctrl n"):
            self._keypress_down(size)

        elif key in ("k", "p", "ctrl p"):
            self._keypress_up(size)

        elif key == "/":
            app.search_prompt()

        elif key in ("shift down", "J", "N"):
            for x in range(app.prefs["shift_multiplier"]):
                self._keypress_down(size)

        elif key in ("shift up", "K", "P"):
            for x in range(app.prefs["shift_multiplier"]):
                self._keypress_up(size)

        elif keyl in ("l", "right"):
            self.keypress(size, "enter")

        elif keyl in ("esc", "h", "left", "q"):
            app.back(keyl == "q")

        elif keyl == "b":
            if app.walker:
                offset = 5 if (app.mode == "thread") else 1
                self.change_focus(size, len(self.body) - offset)

        elif keyl == "t":
            if app.walker:
                self.change_focus(size, 0)

        elif key == "ctrl l":
            wipe_screen()

        elif keyl == "o":
            app.options_menu()

        elif key == "?":
            app.general_help()

        elif key == app.prefs["edit_escapes"]["focus"] and not overlay:
            app.switch_editor()

        elif key in ">." and not overlay:
            app.header_jump_next()

        elif key in "<," and not overlay:
            app.header_jump_previous()

        elif key in ("x", "meta >", "meta .") and not overlay:
            app.incr_jump()

        elif key in ("X", "meta <", "meta ,") and not overlay:
            app.decr_jump()

        elif keyl in "1234567890g" and not overlay:
            app.goto_post_prompt(keyl)

        elif keyl in "c+" and not overlay:
            app.compose()

        elif keyl in ("r", "f5") and not overlay:
            app.refresh()

        elif key == "#":
            app.do_search_result(True)

        elif key == "@":
            app.do_search_result(False)

        elif key == "*":
            app.toggle_client_pin()

        elif key == "\\":
            app.toggle_server_pin()

        elif key == "~":
            # sssssshhhhhhhh
            app.loop.stop()
            try: call("sl", shell=True)
            except: pass
            app.loop.start()

        elif keyl == "$":
            app.loop.stop()
            call("clear", shell=True)
            readline.set_completer(rlcompleter.Completer().complete)
            readline.parse_and_bind("tab: complete")
            interact(banner="Python " + version + "\nBBJ Interactive Console\nCtrl-D exits.", local=globals())
            app.loop.start()

        elif app.mode == "thread" and not app.window_split and not overlay:
            message = app.thread["messages"][app.get_focus_post()]

            if keyl == "ctrl e":
                app.edit_post(None, message)

            elif keyl == "ctrl r":
                app.reply(None, message)


    def mouse_event(self, size, event, button, x, y, focus):
        if super(ActionBox, self).mouse_event(size, event, button, x, y, focus):
            return
        if button == 4:
            for x in range(app.prefs["shift_multiplier"]):
                self._keypress_up(size)

        elif button == 5:
            for x in range(app.prefs["shift_multiplier"]):
                self._keypress_down(size)



def frilly_exit():
    """
    Exit with some flair. Will fill the screen with rainbows,
    or just say bye, depending on the user's bbjrc setting, `dramatic_exit`
    """
    # sometimes this gets called before the loop is set up properly
    try: app.loop.stop()
    except: pass
    if app.prefs["dramatic_exit"] and app.loop.screen_size:
        width, height = app.loop.screen_size
        for x in range(height - 1):
            print_rainbows(
                "".join([choice([" ", choice(punctuation)])
                        for x in range(width)]
                ))
        out = "  ~~CoMeE BaCkK SooOn~~  0000000"
        print_rainbows(out.zfill(width))
    else:
        call("clear", shell=True)
        print_rainbows("Come back soon! <3")
    exit()


def cute_button(label, callback=None, data=None):
    """
    Urwid's default buttons have ugly borders.
    This function returns buttons that are a bit easier to love.
    """
    button = urwid.Button("", callback, data)
    super(urwid.Button, button).__init__(
        urwid.SelectableIcon(label))
    return button


def urwid_rainbows(string, bold=False):
    """
    Same as below, but instead of printing rainbow text, returns
    a markup list suitable for urwid's Text contructor.
    """
    colors = [str(x) for x in range(1, 7)]
    if bold: colors = [(c + "0") for c in colors]
    return urwid.Text([(choice(colors), char) for char in string])


def print_rainbows(string, inputmode=False, end="\n"):
    """
    I cANtT FeELLE MyYE FACECsEE ANYrrMOROeeee
    """

    prefs = bbjrc("load")
    if prefs["monochrome"] or os.getenv("NO_COLOR"):
        if inputmode:
            return input("")
        print(string, end="")
        return print(end, end="")

    for character in string:
        print(choice(colors) + character, end="")
    print('\033[0m', end="")
    if inputmode:
        return input("")
    return print(end, end="")


def paren_prompt(text, positive=True, choices=[], function=input, default=None):
    """
    input(), but riced the fuck out. Changes color depending on
    the value of positive (blue/green for good stuff, red/yellow
    for bad stuff like invalid input), and has a multiple choice
    system capable of rejecting unavailable choices and highlighting
    their first characters.
    """
    end = text[-1]
    if end != "?" and end in punctuation:
        text = text[0:-1]

    monochrome = app.prefs["monochrome"] or os.getenv("NO_COLOR")

    if monochrome:
        mood = ("", "")
    else:
        mood = ("\033[1;36m", "\033[1;32m") if positive \
            else ("\033[1;31m", "\033[1;33m")

    if choices:
        prompt = "%s{" % mood[0]
        for choice in choices:
            prompt += "{0}[{1}{0}]{2}{3} ".format(
                "" if monochrome else "\033[1;35m",
                choice[0], mood[1], choice[1:])
        formatted_choices = prompt[:-1] + ("%s}" % mood[0])
    else:
        formatted_choices = ""

    try:
        response = function("{0}({1}{2}{0}){3}> {4}".format(
            mood[0], mood[1], text, formatted_choices,
            "" if monochrome else "\033[0m"))
        if not choices:
            return response
        elif response == "":
            response = default or " "
        char = response.lower()[0]
        if char in [c[0].lower() for c in choices]:
            return char
        return paren_prompt("Invalid choice", False, choices, function)

    except EOFError:
        print("")
        return ""


def sane_value(key, prompt, positive=True, return_empty=False):
    response = paren_prompt(prompt, positive)
    if return_empty and response == "":
        return response
    try: network.validate(key, response)
    except AssertionError as e:
        return sane_value(key, e.description, False)
    return response


def password_loop(prompt, positive=True):
    response1 = paren_prompt(prompt, positive, function=getpass)
    if response1 == "":
        confprompt = "Confirm empty password"
    else:
        confprompt = "Confirm it"
    response2 = paren_prompt(confprompt, function=getpass)
    if response1 != response2:
        return password_loop("Those didnt match. Try again", False)
    return response1


def nameloop(prompt, positive):
    name = sane_value("user_name", prompt, positive)
    if network.user_is_registered(name):
        return nameloop("%s is already registered" % name, False)
    return name


def log_in(relog=False):
    """
    Handles login or registration using an oldschool input()
    chain. The user is run through this before starting the
    curses app.
    """
    if relog:
        name = sane_value("user_name", "Username", return_empty=True)
    else:
        name = get_arg("user") \
           or os.getenv("BBJ_USER") \
           or sane_value("user_name", "Username", return_empty=True)
    if name == "":
        print_rainbows("~~W3 4R3 4n0nYm0u5~~")
    else:
        # ConnectionRefusedError means registered but needs a
        # password, ValueError means we need to register the user.
        try:
            network.set_credentials(
                name,
                os.getenv("BBJ_PASSWORD", default="")
                  if not relog else ""
            )
            # make it easy for people who use an empty password =)
            print_rainbows("~~welcome back {}~~".format(network.user_name))

        except ConnectionRefusedError:
            def login_loop(prompt, positive):
                try:
                    password = paren_prompt(prompt, positive, function=getpass)
                    network.set_credentials(name, password)
                except ConnectionRefusedError:
                    login_loop("// R E J E C T E D //.", False)

            login_loop("Enter your password", True)
            print_rainbows("~~welcome back {}~~".format(network.user_name))

        except ValueError:
            print_rainbows("Nice to meet'cha, %s!" % name)
            response = paren_prompt(
                "Register as %s?" % name,
                choices=["yes!", "change name", "nevermind!"]
            )

            if response == "c":
                name = nameloop("Pick a new name", True)

            elif response == "n":
                raise InterruptedError

            password = password_loop("Enter a password. It can be empty if you want")
            network.user_register(name, password)
            print_rainbows("~~welcome to the party, %s!~~" % network.user_name)
    sleep(0.5) # let that confirmation message shine


def bbjrc(mode, **params):
    # TODO: Refactor this, the arguments and code do not properly match how this
    # function is used anymore
    """
    Maintains a user a preferences file, setting or returning
    values depending on `mode`.
    """
    try:
        with open(rcpath, "r") as _in:
            values = json.load(_in)
        # update it with new keys if necessary
        for key, default_value in default_prefs.items():
            # The application will never store a config value
            # as the NoneType, so users may set an option as
            # null in their file to reset it to default.
            # Also covers a previous encounter a user
            # had with having a NoneType set in their
            # config by accident, crashing the program.
            if key not in values or values[key] == None:
                values[key] = default_value
    # else make one
    except FileNotFoundError:
        values = default_prefs

    values.update(params)
    # we always write
    with open(rcpath, "w") as _out:
        json.dump(values, _out, indent=2)

    return values


def mark(directive=True):
    """
    Set and retrieve positional marks for threads.
    This uses a seperate file from the preferences
    to keep it free from clutter.
    """
    try:
        with open(markpath, "r") as _in:
            values = json.load(_in)
    except FileNotFoundError:
        values = {}

    if directive == True and app.mode == "thread":
        pos = app.get_focus_post()
        values[app.thread["thread_id"]] = pos
        with open(markpath, "w") as _out:
            json.dump(values, _out)
        return pos

    elif isinstance(directive, str):
        try:
            return values[directive]
        except KeyError:
            return 0


def load_client_pins():
    """
    Retrieve the pinned threads list.
    """
    try:
        with open(pinpath, "r") as _in:
            pins = json.load(_in)
    except FileNotFoundError:
        pins = []
    return pins


def toggle_client_pin(thread_id):
    """
    Given a thread_id, will either add it to the pins or remove it from the
    pins if it already exists.
    """
    pins = load_client_pins()
    if thread_id in pins:
        pins.remove(thread_id)
    else:
        pins.append(thread_id)
    with open(pinpath, "w") as _out:
        json.dump(pins, _out)
    return pins


def ignore(*_, **__):
    """
    The blackness of my soul.
    """
    pass


def wipe_screen(*_):
    """
    A crude hack to repaint the whole screen. I didnt immediately
    see anything to acheive this in the MainLoop methods so this
    will do, I suppose.
    """
    app.loop.stop()
    call("clear", shell=True)
    app.loop.start()


def main():
    global app
    urwid.set_encoding("utf8")
    app = App()
    thread_arg = get_arg("thread", False)
    if thread_arg:
        try:
            # check to make sure thread_id exists. will throw
            # ValueError if not
            thread, usermap = network.thread_load(thread_arg)
            app.immediate_thread_load.append(thread_arg)
        except ValueError as e:
            exit("Specified --thread does not exist")
    call("clear", shell=True)
    print_rainbows(obnoxious_logo)
    print(welcome_monochrome if app.prefs["monochrome"] or os.getenv("NO_COLOR") else welcome)
    try:
        log_in()

        app.index()
        app.loop.run()
    except (InterruptedError, KeyboardInterrupt):
        frilly_exit()


if __name__ == "__main__":
    main()
