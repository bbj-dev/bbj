# Bulletin Butter & Jelly

Hi. This will be BBJs final form. The prototype and its elisp client
are available in the *prototype* folder.

Not all endpoints are fully operational or implemented. Database
logic is not final. Documentation is not fully available and ideas
are not completely fleshed out. While the prototype is currently more
operational, it lacks features and has severe structural issues that
are now being addressed.

The biggest changes from the prototype are:

  * moved from stdlib `socketserver` to a cherrypy http server
  * more consistent response and data objects
  * a real database (sqlite3)
  * better internal exception handling

There are more. I will write about them later.
