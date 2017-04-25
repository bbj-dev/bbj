import sqlite3

with sqlite3.connect("data.sqlite") as _con:
    _con.execute('ALTER TABLE threads ADD COLUMN last_author text DEFAULT ""')
    _con.commit()
    for tid in _con.execute("SELECT thread_id FROM threads"):
        author = _con.execute("SELECT author FROM messages WHERE thread_id = ? ORDER BY post_id", tid).fetchall()[-1]
        _con.execute("UPDATE threads SET last_author = ? WHERE thread_id = ?", author + tid)
    _con.commit()
