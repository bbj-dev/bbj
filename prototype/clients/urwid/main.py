from src import network


bbj = network.BBJ("192.168.1.137", 7066)


def geterr(obj):
    """
    Returns false if there are no errors in a network response,
    else a tuple of (code integer, description string)
    """
    error = obj.get("error")
    if not error:
        return False
    return error["code"], error["description"]


def register_prompt(user, initial=True):
    if initial:
        print("Register for BBJ as {}?".format(user))
        reply = input("(y[es], d[ifferent name], q[uit])> ").lower()

        if reply.startswith("d"):
            register_prompt(input("(Username)> "))
        elif reply.startswith("q"):
            exit("bye!")

        def getpass(ok):
            p1 = input(
                "(Choose a password)> " if ok else \
                "(Those didn't match. Try again)> ")
            p2 = input("(Now type it one more time)> ")
            return p1 if p1 == p2 else getpass(False)

        # this method will sha256 it for us
        bbj.setuser(user, getpass(True))

    response = bbj("user_register", quip="", bio="")
    error = geterr(response)
    if error:
        exit("Registration error: " + error[1])
    return response


def login(user, ok=True):
    if not bbj("is_registered", target_user=user):
        register_prompt(user)
    else:
        bbj.setuser(user, input(
            "(Password)> " if ok else \
            "(Invalid password, try again)> "))

    if not bbj("check_auth"):
        login(user, ok=False)

    return bbj("user_get", target_user=user)







# user = input("(BBJ Username)> ")
# if not bbj("is_registered", target_user=user):


login(input("(Username)> "))

import urwid

f = urwid.Frame(
    urwid.ListBox(
        urwid.SimpleFocusListWalker(
            [urwid.Text(i["body"]) for i in bbj("thread_index")["threads"]]
        )
    )
)

t = urwid.Overlay(
    f, urwid.SolidFill('!'),
    align='center',
    width=('relative', 80),
    height=('relative', 80),
    valign='middle'
)

loop = urwid.MainLoop(t)
