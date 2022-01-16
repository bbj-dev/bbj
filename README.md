# Bulletin Butter & Jelly

BBJ is a trivial collection of python scripts and database queries that
miraculously shit out a fully functional, text-driven community bulletin board.
Requires Python 3.4 and up for the server and the official TUI client (clients/urwid/).

![AAAAAAAAAAAAAAAAAAAA](readme.png)
<div style="text-align: center;"><h2>Look Ma, it boots !!11!</h2></div>

It's all driven by an API sitting on top of CherryPy. Currently, it does not
serve HTML but this is planned for the (distant?) future.

The two official client implementations are a standalone TUI client for
the unix terminal, and GNU Emacs. The API is simple and others are welcome
to join the party at some point.

## Setup Instructions

1. Make a virtual env
```
python3 -m venv venv
source venv/bin/activate
```

2. Run setup.sh
```
./setup.sh venv/bin/python3
```

3. Add systemd service (optional)
```
cp contrib/bbj.service /etc/systemd/system/
$EDITOR /etc/systemd/system/bbj.service
systemctl enable --now bbj
```
Be sure to edit bbj.service with your venv and paths.

4. Make a client script

Create a script somewhere in your `$PATH` (I used `/usr/local/bin/bbj`) with the following contents,
adapting the path to your install:
```shell
#!/bin/sh
exec /srv/bbj/venv/bin/python3 /srv/bbj/clients/urwid/main.py
```
