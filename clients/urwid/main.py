from time import sleep, localtime
from string import punctuation
from subprocess import run
from random import choice
from network import BBJ
import urwid

network = BBJ(host="127.0.0.1", port=8080)

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


class App:
    def __init__(self):
        colors = [
            ("bar", "light magenta", "default", "underline"),
            ("button", "light red", "default")
        ]
        self.loop = urwid.MainLoop(urwid.Frame(
            urwid.LineBox(ActionBox(urwid.SimpleFocusListWalker([]))),
        ), colors)
        self.date_format = "{1}/{2}/{0}"
        self.index()


    def set_header(self, text, *format_specs):
        self.loop.widget.header = urwid.AttrMap(urwid.Text(
            ("%s@bbj | " % network.user_name)
            + text.format(*format_specs)
        ), "bar")


    def set_footer(self, *controls):
        text = str()
        for control in controls:
            text += "[{}]{} ".format(control[0], control[1:])
        self.loop.widget.footer = urwid.AttrMap(urwid.Text(text), "bar")


    def readable_delta(self, created, modified):
        delta = modified - created
        minutes = delta // 60
        if not minutes:
            return "less than a minute ago"
        elif minutes < 60:
            return "%d minutes ago" % minutes
        hours = delta // 60
        if hours == 1:
            return "about an hour ago"
        elif hours < 48:
            return "%d hours ago" % hours
        return self.date_format.format(*localtime(modified))


    def index(self):
        threads, usermap = network.thread_index()
        self.set_header("{} threads", len(threads))
        self.set_footer("Compose")
        walker = self.loop.widget.body.base_widget.body
        for thread in threads:
            button = urwid.Button("", self.thread_load, thread["thread_id"])
            super(urwid.Button, button).__init__(
                urwid.SelectableIcon(">>"))
            title = urwid.Text(thread["title"])

            last_mod = thread["last_mod"]
            created = thread["created"]
            infoline = "by ~{} @ {} | last active {}".format(
                usermap[thread["author"]]["user_name"],
                self.date_format.format(*localtime(created)),
                self.readable_delta(created, last_mod)
            )

            walker.append(urwid.Columns([(3, urwid.AttrMap(button, "button")), title]))
            walker.append(urwid.Text(infoline))
            walker.append(urwid.Divider("-"))


    def thread_load(self, button, thread_id):
        thread, usermap = network.thread_load(thread_id)
        walker = self.loop.widget.body.base_widget.body
        walker.clear()
        self.set_header("~{}: {}",
            usermap[thread["author"]]["user_name"], thread["title"])
        for message in thread["messages"]:
            pass


class ActionBox(urwid.ListBox):
    pass


def motherfucking_rainbows(string, inputmode=False, end="\n"):
    """
    I cANtT FeELLE MyYE FACECsEE ANYrrMOROeeee!!
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
    Handles login or registration using the oldschool input()
    method. The user is run through this before starting the
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
            motherfucking_rainbows("~~logged in as {}~~".format(network.user_name))

        except ConnectionRefusedError:
            def login_loop(prompt, positive):
                try:
                    password = paren_prompt(prompt, positive)
                    network.set_credentials(name, password)
                except ConnectionRefusedError:
                    login_loop("// R E J E C T E D //.", False)

            login_loop("Enter your password", True)
            motherfucking_rainbows("~~logged in as {}~~".format(network.user_name))

        except ValueError:
            motherfucking_rainbows("Nice to meet'cha, %s!" % name)
            response = paren_prompt(
                "Register as %s?" % name,
                choices=["yes!", "change name"]
            )

            if response == "c":
                name = sane_value("user_name", "Pick a new name")

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


def main():
    run("clear", shell=True)
    motherfucking_rainbows(obnoxious_logo)
    print(welcome)
    log_in()
    # sleep(1) # let that confirmation message shine

if __name__ == "__main__":
    global app
    main()
    app = App()
    app.loop.run()
