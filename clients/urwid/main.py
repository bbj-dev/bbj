# -*- fill-column: 72 -*-

from network import BBJ, URLError
from string import punctuation
from datetime import datetime
from time import time, sleep
from subprocess import run
from random import choice
import tempfile
import urwid
import json
import os


try:
    network = BBJ(host="127.0.0.1", port=7099)
except URLError as e:
    # print the connection error in red
    exit("\033[0;31m%s\033[0m" % repr(e))


obnoxious_logo = """
       OwO    8 888888888o    8 888888888o               8 8888         1337
   %          8 8888    `88.  8 8888    `88.          !  8 8888   >><>
       !!     8 8888     `88  8 8888     `88   *         8 8888
 $            8 8888     ,88  8 8888     ,88             8 8888    <><><><>
    <3        8 8888.   ,88'  8 8888.   ,88'      !      8 8888    ^   >|
           ^  8 8888888888    8 8888888888               8 8888    ----||
      (       8 8888    `88.  8 8888    `88.  88.        8 8888         |
              8 8888      88  8 8888      88  `88.    |  8 888'    !??!
  g      ?    8 8888.   ,88'  8 8888.   ,88'    `88o.   .8 88'  ----_
              8 888888888P    8 888888888P        `Y888888 '         |
"""

welcome = """
>>> Welcome to Bulletin Butter & Jelly! ---------------------------------------@
| BBJ is a persistent, chronologically ordered discussion board for tilde.town.|
| You may log in, register as a new user, or participate anonymously.          |
| \033[1;31mTo go anon, just press enter. Otherwise, give me a name (registered or not)\033[0m  |
@______________________________________________________________________________@
"""

colors = [
    "\033[1;31m", "\033[1;33m", "\033[1;33m",
    "\033[1;32m", "\033[1;34m", "\033[1;35m"
]


editors = ["nano", "vim", "emacs", "vim -u NONE", "emacs -Q", "micro", "ed", "joe"]
# defaults to internal editor, integrates the above as well
default_prefs = {
    "editor": None,
    "integrate_external_editor": True,
    "dramatic_exit": True,
    "date": "%Y/%m/%d",
    "time": "%H:%M",
    "frame_title": "> > T I L D E T O W N < <",
    "max_text_width": 80
}


class App(object):
    def __init__(self):
        self.bars = {
            "index": "[C]ompose [R]efresh [O]ptions [?]Help/More [Q]uit",
            "thread": "[C]ompose [Q]Back [R]efresh [Enter]Post Options [/]Search [B/T]End [?]Help/More"
        }

        colors = [
            ("default", "default", "default"),
            ("bar", "light magenta", "default"),
            ("button", "light red", "default"),
            ("hover", "light cyan", "default"),
            ("dim", "dark gray", "default"),

            # map the bbj api color values for display
            ("0", "default", "default"),
            ("1", "dark red", "default"),
            # sounds ugly but brown is as close as we can get to yellow without being bold
            ("2", "brown", "default"),
            ("3", "dark green", "default"),
            ("4", "dark blue", "default"),
            ("5", "dark cyan", "default"),
            ("6", "dark magenta", "default")
        ]

        self.mode = None
        self.thread = None
        self.usermap = {}
        self.prefs = bbjrc("load")
        self.window_split = False
        self.last_pos = 0

        self.walker = urwid.SimpleFocusListWalker([])
        self.loop = urwid.MainLoop(urwid.Frame(
            urwid.LineBox(
                ActionBox(self.walker),
                title=self.prefs["frame_title"],
                **frame_theme()
            )), colors)

        self.index()


    def set_header(self, text, *format_specs):
        """
        Update the header line with the logged in user, a seperator,
        then concat text with format_specs applied to it. Applies
        bar formatting to it.
        """
        self.loop.widget.header = \
            urwid.AttrMap(
                urwid.Text(
                    ("{}@bbj | " + text).format(
                        (network.user_name or "anonymous"),
                        *format_specs)),
                "bar")


    def set_footer(self, string):
        """
        Sets the footer to display `string`, applying bar formatting.
        Other than setting the color, `string` is shown verbatim.
        """
        self.loop.widget.footer = urwid.AttrMap(urwid.Text(string), "bar")


    def set_default_header(self):
        """
        Sets the header to the default for the current screen.
        """
        if self.mode == "thread":
            name = self.usermap[self.thread["author"]]["user_name"]
            self.set_header("~{}: {}", name, self.thread["title"])
        else:
            self.set_header("{} threads", len(self.walker))


    def set_default_footer(self):
        """
        Sets the footer to the default for the current screen.
        """
        self.set_footer(self.bars[self.mode])


    def set_bars(self):
        """
        Sets both the footer and header to their default values
        for the current mode.
        """
        self.set_default_header()
        self.set_default_footer()


    def close_editor(self):
        """
        Close whatever editing widget is open and restore proper
        state back the walker.
        """
        if self.window_split:
            self.window_split = False
            self.loop.widget.focus_position = "body"
            self.set_footer(self.bars["thread"])
        else:
            self.loop.widget = self.loop.widget[0]
        self.set_default_header()


    def switch_editor(self):
        """
        Switch focus between the thread viewer and the open editor
        """
        if not self.window_split:
            return

        elif self.loop.widget.focus_position == "body":
            self.loop.widget.focus_position = "footer"
            focus = "[focused on editor]"
            attr = ("bar", "dim")

        else:
            self.loop.widget.focus_position = "body"
            focus = "[focused on thread]"
            attr = ("dim", "bar")

        control = "[save/quit to send]" if self.prefs["editor"] else "[F3]Send"
        self.loop.widget.footer[0].set_text(
            "[F1]Abort [F2]Swap %s %s" % (control, focus))

        # this hideous and awful sinful horrid unspeakable shithack changes
        # the color of the help/title lines and editor border to reflect which
        # object is currently in focus.
        self.loop.widget.footer.contents[1][0].original_widget.attr_map = \
            self.loop.widget.footer.contents[0][0].attr_map = {None: attr[0]}
        self.loop.widget.header.attr_map = {None: attr[1]}


    def readable_delta(self, modified):
        """
        Return a human-readable string representing the difference
        between a given epoch time and the current time.
        """
        delta = time() - modified
        hours, remainder = divmod(delta, 3600)
        if hours > 48:
            return self.timestring(modified)
        elif hours > 1:
            return "%d hours ago" % hours
        elif hours == 1:
            return "about an hour ago"
        minutes, remainder = divmod(remainder, 60)
        if minutes > 1:
            return "%d minutes ago" % minutes
        return "less than a minute ago"


    def make_message_body(self, message):
        """
        Returns the widgets that comprise a message in a thread, including the
        text body, author info and the action button
        """
        info = "@ " + self.timestring(message["created"])
        if message["edited"]:
            info += " [edited]"

        name = urwid.Text("~{}".format(self.usermap[message["author"]]["user_name"]))
        post = str(message["post_id"])
        head = urwid.Columns([
                (2 + len(post), urwid.AttrMap(cute_button(">" + post), "button", "hover")),
                (len(name._text) + 1,
                   urwid.AttrMap(name, str(self.usermap[message["author"]]["color"]))),
                urwid.AttrMap(urwid.Text(info), "dim")
            ])

        head.message = message
        return [
            head,
            urwid.Divider(),
            MessageBody(message["body"]),
            urwid.Divider(),
            urwid.AttrMap(urwid.Divider("-"), "dim")
        ]


    def timestring(self, epoch, mode="both"):
        """
        Returns a string of time representing a given epoch and mode.
        """
        if mode == "delta":
            return self.readable_delta(epoch)

        date = datetime.fromtimestamp(epoch)
        if mode == "time":
            directive = self.prefs["time"]
        elif mode == "date":
            directive = self.prefs["date"]
        else:
            directive = "%s %s" % ( self.prefs["time"], self.prefs["date"])
        return date.strftime(directive)


    def make_thread_body(self, thread):
        """
        Returns the pile widget that comprises a thread in the index.
        """
        button = cute_button(">>", self.thread_load, thread["thread_id"])
        title = urwid.Text(thread["title"])
        user = self.usermap[thread["author"]]
        dateline = [
            ("default", "by "),
            (str(user["color"]), "~%s " % user["user_name"]),
            ("dim", "@ %s" % self.timestring(thread["created"]))
        ]

        infoline = "%d replies; active %s" % (
            thread["reply_count"], self.timestring(thread["last_mod"], "delta"))

        pile = urwid.Pile([
            urwid.Columns([(3, urwid.AttrMap(button, "button", "hover")), title]),
            urwid.Text(dateline),
            urwid.AttrMap(urwid.Text(infoline), "dim"),
            urwid.AttrMap(urwid.Divider("-"), "dim")
        ])

        pile.thread = thread
        return pile


    def index(self):
        """
        Browse the index.
        """
        self.mode = "index"
        self.thread = None
        self.window_split = False
        threads, usermap = network.thread_index()
        self.usermap.update(usermap)
        self.walker.clear()
        for thread in threads:
            self.walker.append(self.make_thread_body(thread))
        self.set_bars()
        try: self.loop.widget.body.base_widget.set_focus(self.last_pos)
        except IndexError:
            pass


    def thread_load(self, button, thread_id):
        """
        Open a thread.
        """
        if self.mode == "index":
            self.last_pos = self.loop.widget.body.base_widget.get_focus()[1]
        self.mode = "thread"
        thread, usermap = network.thread_load(thread_id)
        self.usermap.update(usermap)
        self.thread = thread
        self.walker.clear()
        for message in thread["messages"]:
            self.walker += self.make_message_body(message)
        self.set_bars()


    def refresh(self, bottom=False):
        if self.mode == "index":
            return self.index()
        self.thread_load(None, self.thread["thread_id"])
        if bottom:
            self.loop.widget.body.base_widget.set_focus(len(self.walker) - 5)


    def back(self):
        if app.mode == "index":
            frilly_exit()
        elif app.mode == "thread":
            self.index()


    def set_new_editor(self, button, value, key):
        """
        Callback for the option radio buttons to set the the text editor.
        """
        if value == False:
            return
        elif key == "internal":
            key = None
        self.prefs.update({"editor": key})
        bbjrc("update", **self.prefs)


    def set_editor_mode(self, button, value):
        """
        Callback for the editor mode radio buttons in the options.
        """
        self.prefs["integrate_external_editor"] = value
        bbjrc("update", **self.prefs)


    def relog(self, *_, **__):
        """
        Options menu callback to log the user in again.
        Drops back to text mode because im too lazy to
        write a responsive urwid thing for this.
        """
        self.loop.widget = self.loop.widget[0]
        self.loop.stop()
        run("clear", shell=True)
        print(welcome)
        log_in()
        self.loop.start()
        self.set_default_header()
        self.options_menu()


    def unlog(self, *_, **__):
        """
        Options menu callback to anonymize the user and
        then redisplay the options menu.
        """
        network.user_name = network.user_auth = None
        self.loop.widget = self.loop.widget[0]
        self.set_default_header()
        self.options_menu()


    def set_color(self, button, value, color):
        if value == False:
            return
        network.user_update(color=color)


    def options_menu(self):
        """
        Create a popup for the user to configure their account and
        display settings.
        """
        editor_buttons = []
        edit_mode = []
        user_colors = []

        if network.user_auth:
            account_message = "Logged in as %s." % network.user_name
            colors = ["None", "Red", "Yellow", "Green", "Blue", "Cyan", "Magenta"]
            for index, color in enumerate(colors):
                urwid.RadioButton(
                    user_colors, color,
                    network.user["color"] == index,
                    self.set_color, index)

            account_stuff = [
                urwid.Button("Change login.", on_press=self.relog),
                urwid.Button("Go anonymous.", on_press=self.unlog),
                urwid.Divider(),
                urwid.Text(("button", "Your color:")),
                *user_colors

            ]
        else:
            account_message = "You're browsing anonymously, and cannot set account preferences."
            account_stuff = [
                urwid.Button("Login/Register", on_press=self.relog)
            ]


        urwid.RadioButton(
            editor_buttons, "Internal",
            state=not self.prefs["editor"],
            on_state_change=self.set_new_editor,
            user_data="internal")

        for editor in editors:
            urwid.RadioButton(
                editor_buttons, editor,
                state=self.prefs["editor"] == editor,
                on_state_change=self.set_new_editor,
                user_data=editor)

        urwid.RadioButton(
            edit_mode, "Integrate",
            state=self.prefs["integrate_external_editor"],
            on_state_change=self.set_editor_mode)

        urwid.RadioButton(
            edit_mode, "Overthrow",
            state=not self.prefs["integrate_external_editor"])

        widget = OptionsMenu(
            urwid.Filler(
                urwid.Pile([
                    urwid.Text(("button", "Your account:")),
                    urwid.Text(account_message),
                    urwid.Divider(),
                    *account_stuff,
                    urwid.Divider("-"),
                    urwid.Text(("button", "Text editor:")),
                    urwid.Divider(),
                    *editor_buttons,
                    urwid.Divider("-"),
                    urwid.Text(("button", "External text editor mode:")),
                    urwid.Text("If you have problems using an external text editor, "
                               "set this to Overthrow."),
                    urwid.Divider(),
                    *edit_mode,
                    urwid.Divider("-"),
                ]), "top"),
            title="BBJ Options",
            **frame_theme()
        )

        self.loop.widget = urwid.Overlay(
            widget, self.loop.widget,
            align="center",
            valign="middle",
            width=30,
            height=(self.loop.screen_size[1] - 10)
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


    def reset_footer(self, *_, **__):
        try:
            self.set_footer(self.bars[self.mode])
            self.loop.widget.focus_position = "body"
        except:
            # just keep trying until the widget can handle it
            self.loop.set_alarm_in(0.5, self.reset_footer)


    def temp_footer_message(self, string, duration=3):
        self.loop.set_alarm_in(duration, self.reset_footer)
        self.set_footer(string)


    def overthrow_ext_edit(self):
        """
        Opens the external editor, but instead of integreating it into the app,
        stops the mainloop and blocks until the editor is killed. Returns the
        body of text the user composed.
        """
        self.loop.stop()
        descriptor, path = tempfile.mkstemp()
        run("%s %s" % (self.prefs["editor"], path), shell=True)
        with open(descriptor) as _:
            body = _.read()
        os.remove(path)
        self.loop.start()
        return body.strip()


    def compose(self, title=None):
        if self.mode == "index" and not title:
            return self.footer_prompt("Title", self.compose)

        elif title:
            try: network.validate("title", title)
            except AssertionError as e:
                return self.footer_prompt(
                    "Title", self.compose, extra_text=e.description)

        if self.prefs["editor"] and not self.prefs["integrate_external_editor"]:
            body = self.overthrow_ext_edit()
            if not body:
                return self.temp_footer_message("EMPTY POST DISCARDED")
            params = {"body": body}

            if self.mode == "thread":
                endpoint = "reply"
                params.update({"thread_id": self.thread["thread_id"]})
            else:
                endpoint = "create"
                params.update({"title": title})

            network.request("thread_" + endpoint, **params)
            return self.refresh(True)

        if self.mode == "index":
            self.set_header('Composing "{}"', title)
            if self.prefs["editor"]:
                editor = ExternalEditor("thread_create", title=title)
                self.set_footer("[F1]Abort [Save and quit to submit your thread]")
            else:
                editor = urwid.Filler(
                    InternalEditor("thread_create", title=title),
                    valign=urwid.TOP)
                self.set_footer("[F1]Abort [F3]Send")

            self.loop.widget = urwid.Overlay(
                urwid.LineBox(
                    editor,
                    title=self.prefs["editor"] or "",
                    **frame_theme()),
                self.loop.widget,
                align="center",
                valign="middle",
                width=self.loop.screen_size[0] - 2,
                height=(self.loop.screen_size[1] - 4))

        elif self.mode == "thread":
            self.window_split=True
            self.set_header('Replying to "{}"', self.thread["title"])
            if self.prefs["editor"]:
                editor = ExternalEditor("thread_reply", thread_id=self.thread["thread_id"])
            else:
                editor = urwid.AttrMap(urwid.Filler(
                    InternalEditor("thread_reply", thread_id=self.thread["thread_id"]),
                    valign=urwid.TOP), "default")
            self.loop.widget.footer = urwid.Pile([
                urwid.AttrMap(urwid.Text(""), "bar"),
                urwid.BoxAdapter(urwid.AttrMap(urwid.LineBox(
                    editor, **frame_theme()
                ), "bar"), self.loop.screen_size[1] // 2),])
            self.switch_editor()


class MessageBody(urwid.Text):
    pass


class FootPrompt(urwid.Edit):
    def __init__(self, callback, *callback_args):
        super(FootPrompt, self).__init__()
        self.callback = callback
        self.args = callback_args


    def keypress(self, size, key):
        if key != "enter":
            return super(FootPrompt, self).keypress(size, key)
        app.loop.widget.focus_position = "body"
        app.set_footer(app.bars[app.mode])
        self.callback(self.get_edit_text(), *self.args)


class InternalEditor(urwid.Edit):
    def __init__(self, endpoint, **params):
        super(InternalEditor, self).__init__(multiline=True)
        self.endpoint = endpoint
        self.params = params

    def keypress(self, size, key):
        if key not in ["f1", "f2", "f3"]:
            return super(InternalEditor, self).keypress(size, key)
        elif key == "f1":
            app.close_editor()
            return app.refresh()
        elif key == "f2":
            return app.switch_editor()

        body = self.get_edit_text().strip()
        app.close_editor()
        if body:
            self.params.update({"body": body})
            network.request(self.endpoint, **self.params)
            app.refresh(True)
        else:
            app.temp_footer_message("EMPTY POST DISCARDED")


class ExternalEditor(urwid.Terminal):
    def __init__(self, endpoint, **params):
        self.file_descriptor, self.path = tempfile.mkstemp()
        self.endpoint = endpoint
        self.params = params
        env = os.environ
        env.update({"LANG": "POSIX"})
        command = ["bash", "-c", "{} {}; echo Press any key to kill this window...".format(
            app.prefs["editor"], self.path)]
        super(ExternalEditor, self).__init__(command, env, app.loop, "f1")


    def keypress(self, size, key):
        if self.terminated:
            app.close_editor()
            with open(self.file_descriptor) as _:
                self.params.update({"body": _.read().strip()})
            os.remove(self.path)
            if self.params["body"]:
                network.request(self.endpoint, **self.params)
                return app.refresh(True)
            else:
                return app.temp_footer_message("EMPTY POST DISCARDED")

        elif key not in ["f1", "f2"]:
            return super(ExternalEditor, self).keypress(size, key)

        elif key == "f1":
            self.terminate()
            app.close_editor()
            app.refresh()
        # key == "f2"
        app.switch_editor()


class OptionsMenu(urwid.LineBox):
    def keypress(self, size, key):
        super(OptionsMenu, self).keypress(size, key)
        if key.lower() == "q":
            app.loop.widget = app.loop.widget[0]
        elif key in ["ctrl n", "j", "n"]:
            return self.keypress(size, "down")
        elif key in ["ctrl p", "k", "p"]:
            return self.keypress(size, "up")


class ActionBox(urwid.ListBox):
    """
    The listwalker used by all the browsing pages. Most of the application
    takes place in an instance of this box. Handles many keybinds.
    """
    def keypress(self, size, key):
        super(ActionBox, self).keypress(size, key)

        if key == "f2":
            app.switch_editor()

        elif key in ["j", "n", "ctrl n"]:
            self._keypress_down(size)

        elif key in ["k", "p", "ctrl p"]:
            self._keypress_up(size)

        elif key in ["J", "N"]:
            for x in range(5):
                self._keypress_down(size)

        elif key in ["K", "P"]:
            for x in range(5):
                self._keypress_up(size)

        elif key in ["h", "left"]:
            app.back()

        elif key in ["l", "right"]:
            self.keypress(size, "enter")

        elif key == "b":
            self.change_focus(size, len(app.walker) - 1)

        elif key == "t":
            self.change_focus(size, 0)

        elif key in ["c", "R", "+"]:
            app.compose()

        elif key == "r":
            app.refresh()

        elif key == "o":
            app.options_menu()

        elif key.lower() == "q":
            app.back()


def frilly_exit():
    """
    Exit with some flair. Will fill the screen with rainbows
    and shit, or just say bye, depending on the user's bbjrc
    setting, `dramatic_exit`
    """
    app.loop.stop()
    if app.prefs["dramatic_exit"]:
        width, height = app.loop.screen_size
        for x in range(height - 1):
            motherfucking_rainbows(
                "".join([choice([" ", choice(punctuation)])
                        for x in range(width)]
                ))
        out = "  ~~CoMeE BaCkK SooOn~~  0000000"
        motherfucking_rainbows(out.zfill(width))
    else:
        run("clear", shell=True)
        motherfucking_rainbows("Come back soon! <3")
    exit()


def cute_button(label, callback=None, data=None):
    """
    Urwid's default buttons are shit, and they have ugly borders.
    This function returns buttons that are a bit easier to love.
    """
    button = urwid.Button("", callback, data)
    super(urwid.Button, button).__init__(
        urwid.SelectableIcon(label))
    return button


def urwid_rainbows(string):
    """
    Same as below, but instead of printing rainbow text, returns
    a markup list suitable for urwid's Text contructor.
    """
    colors = [str(x) for x in range(1, 7)]
    return urwid.Text([(choice(colors), char) for char in string])


def motherfucking_rainbows(string, inputmode=False, end="\n"):
    """
    I cANtT FeELLE MyYE FACECsEE ANYrrMOROeeee
    """
    for character in string:
        print(choice(colors) + character, end="")
    print('\033[0m', end="")
    if inputmode:
        return input("")
    return print(end, end="")


def paren_prompt(text, positive=True, choices=[]):
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

    mood = ("\033[1;36m", "\033[1;32m") if positive \
           else ("\033[1;31m", "\033[1;33m")

    if choices:
        prompt = "%s{" % mood[0]
        for choice in choices:
            prompt += "{0}[{1}{0}]{2}{3} ".format(
                "\033[1;35m", choice[0], mood[1], choice[1:])
        formatted_choices = prompt[:-1] + ("%s}" % mood[0])
    else:
        formatted_choices = ""

    try:
        response = input("{0}({1}{2}{0}){3}> \033[0m".format(
            *mood, text, formatted_choices))
        if not choices:
            return response
        elif response == "":
            response = " "
        char = response.lower()[0]
        if char in [c[0] for c in choices]:
            return char
        return paren_prompt("Invalid choice", False, choices)

    except EOFError:
        print("")
        return ""

    except KeyboardInterrupt:
        exit("\nNevermind then!")


def sane_value(key, prompt, positive=True, return_empty=False):
    response = paren_prompt(prompt, positive)
    if return_empty and response == "":
        return response
    try: network.validate(key, response)
    except AssertionError as e:
        return sane_value(key, e.description, False)
    return response


def log_in():
    """
    Handles login or registration using an oldschool input()
    chain. The user is run through this before starting the
    curses app.
    """
    name = sane_value("user_name", "Username", return_empty=True)
    if name == "":
        motherfucking_rainbows("~~W3 4R3 4n0nYm0u5~~")
    else:
        # ConnectionRefusedError means registered but needs a
        # password, ValueError means we need to register the user.
        try:
            network.set_credentials(name, "")
            # make it easy for people who use an empty password =)
            motherfucking_rainbows("~~welcome back {}~~".format(network.user_name))

        except ConnectionRefusedError:
            def login_loop(prompt, positive):
                try:
                    password = paren_prompt(prompt, positive)
                    network.set_credentials(name, password)
                except ConnectionRefusedError:
                    login_loop("// R E J E C T E D //.", False)

            login_loop("Enter your password", True)
            motherfucking_rainbows("~~welcome back {}~~".format(network.user_name))

        except ValueError:
            motherfucking_rainbows("Nice to meet'cha, %s!" % name)
            response = paren_prompt(
                "Register as %s?" % name,
                choices=["yes!", "change name"]
            )

            if response == "c":
                def nameloop(prompt, positive):
                    name = sane_value("user_name", prompt, positive)
                    if network.user_is_registered(name):
                        return nameloop("%s is already registered" % name, False)
                    return name
                name = nameloop("Pick a new name", True)

            def password_loop(prompt, positive=True):
                response1 = paren_prompt(prompt, positive)
                if response1 == "":
                    confprompt = "Confirm empty password"
                else:
                    confprompt = "Confirm it"
                response2 = paren_prompt(confprompt)
                if response1 != response2:
                    return password_loop("Those didnt match. Try again", False)
                return response1

            password = password_loop("Enter a password. It can be empty if you want")
            network.user_register(name, password)
            motherfucking_rainbows("~~welcome to the party, %s!~~" % network.user_name)
    sleep(0.8) # let that confirmation message shine


def frame_theme(mode="default"):
    """
    Return the kwargs for a frame theme.
    """
    if mode == "default":
        return dict(
            tlcorner="@", trcorner="@", blcorner="@", brcorner="@",
            tline="=", bline="=", lline="|", rline="|"
        )



def bbjrc(mode, **params):
    """
    Maintains a user a preferences file, setting or returning
    values depending on `mode`.
    """
    path = os.path.join(os.getenv("HOME"), ".bbjrc")
    try:
        # load it up
        with open(path, "r") as _in:
            values = json.load(_in)
        # update it with new keys if necessary
        for key, default_value in default_prefs.items():
            if key not in values:
                values[key] = default_value
    # else make one
    except FileNotFoundError:
        values = default_prefs

    if mode == "update":
        values.update(params)

    with open(path, "w") as _out:
        json.dump(values, _out)

    return values



def main():
    run("clear", shell=True)
    motherfucking_rainbows(obnoxious_logo)
    print(welcome)
    log_in()

if __name__ == "__main__":
    # global app
    main()
    app = App()
    app.loop.run()
    # app.loop.widget.keypress(app.loop.screen_size, "up")
