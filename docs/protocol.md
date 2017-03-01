Data Standards
--------------


  * UTF-8 in, UTF-8 out. No exceptions.

  * SHA256 for auth_hash. Server will do a basic check to make sure of this.

  * Security is not a #1 concern. Basic authorization will be implemented
    to **help prevent** users from impersonating each other, but this isn't
    intended to be bulletproof and you shouldn't trust the system with a
    password you use elsewhere. All clients should inform the user of this.

  * Command-line, on-tilde comes first. Local clients should be possible using
    SSH port binding, however features like inline images, graphical elements
    and the like will never be implemented as part of the protocol. Local clients
    can definitely do things like URL image previews though. Hyperlinks with a
    different text then the link itself will never be implemented.


Text Entities
-------------

The `entities` attribute is an array of objects that represent blocks
of text within a post that have special properties. Clients may safely
ignore these things without losing too much meaning, but in a rich
implementation like an Emacs or GUI, they can provide
some highlighting and navigation perks. The array object may be
empty. If its not, its populated with arrays representing the
modifications to be made.

Objects **always** have a minimum of 3 attributes:
```
["quote", 5, 7]
```
object[0] is a string representing the attribute type. They are
documented below. The next two items are the indices of the
property in the body string. The way clients are to access these
indices is beyond the scope of this document; accessing a subsequence
varies a lot between programming languages.

Some objects will provide further arguments beyond those 3. They will
always be at the end of the array.

| Name        | Description                                              |
|-------------|----------------------------------------------------------|
| `quote`     | This is a string that refers to a previous post number.  |
|             | These are formatted like >>5, which means it is a        |
|             | reference to `post_id` 5. These are not processed in     |
|             | thread OPs. >>0 may be used to refer to the OP. In       |
|             | addition to the indices at i[1] and i[2], a fourth value |
|             | is provided, which is an integer of the `post_id` being  |
|             | quoted. Note that the string indices include the >>'s.   |
|-------------|----------------------------------------------------------|
| `linequote` | This is a line of text, denoted by a newline during      |
|             | composure, representing text that is assumed to be       |
|             | a quote of someone else. The indices span from the >     |
|             | until (not including) the newline.                       |
|-------------|----------------------------------------------------------|
| `color`     | This is a block of text, denoted by [[color: body]]      |
|             | during composure. The body may span across newlines.     |
|             | A fourth item is provided in the array: it is one of the |
|             | following strings representing the color.                |
|             | `red`, `green`, `yellow`, `blue`, `magenta`, or `cyan`.  |
|-------------|----------------------------------------------------------|
| `bold`      | Like color, except that no additional attribute is       |
| `italic`    | provided. it is denoted as [[directive: body]] during    |
| `underline` | composure.                                               |


Threads & Replies
-----------------

Threads are represented the same when using `thread_index` and
`thread_load`, except that the `replies` attribute is only
present with `thread_load`. The following attributes are
available on the parent object:

| Name          | Description                                          |
|---------------|------------------------------------------------------|
| `author`      | The ID string of the author.                         |
|---------------|------------------------------------------------------|
| `thread_id`   | The ID string of the thread.                         |
|---------------|------------------------------------------------------|
| `title`       | The title string of the thread.                      |
|---------------|------------------------------------------------------|
| `body`        | The body string of the post's text.                  |
|---------------|------------------------------------------------------|
| `entities`    | A (possibly empty) array of entity objects for       |
|               | the post `body`.                                     |
|---------------|------------------------------------------------------|
| `tags`        | An array of strings representing tags the            |
|               | author gave to the thread at creation.               |
|               | When empty, it is an array with no elements.         |
|---------------|------------------------------------------------------|
| `replies`     | An array containing full reply objects in            |
|               | the order they were posted. Your clients             |
|               | do not need to sort these. Array can be empty.       |
|---------------|------------------------------------------------------|
| `reply_count` | An integer representing the number of replies        |
|               | that have been posted in this thread.                |
|---------------|------------------------------------------------------|
| `lastmod`     | Unix timestamp of when the thread was last           |
|               | posted in, or a message was edited.                  |
|---------------|------------------------------------------------------|
| `edited`      | Boolean of whether the post has been edited.         |
|---------------|------------------------------------------------------|
| `created`     | Unix timestamp of when the post was originally made. |

The following attributes are available on each reply object in `replies`:


| Name       | Description                                             |
|------------|---------------------------------------------------------|
| `post_id`  | An integer of the posts ID; unlike thread and user ids, |
|            | this is not a uuid but instead is incremental, starting |
|            | from 1 as the first reply and going up by one for each  |
|            | post. These may be referenced by `quote` entities.      |
|------------|---------------------------------------------------------|
| `author`   | Author ID string                                        |
|------------|---------------------------------------------------------|
| `body`     | The body string the reply's text.                       |
|------------|---------------------------------------------------------|
| `entities` | A (possibly empty) array of entity objects for          |
|            | the reply `body`.                                       |
|------------|---------------------------------------------------------|
| `lastmod`  | Unix timestamp of when the post was last edited, or     |
|            | the same as `created` if it never was.                  |
|------------|---------------------------------------------------------|
| `edited`   | A boolean of whether the post was edited.               |
|------------|---------------------------------------------------------|
| `created`  | Unix timestamp of when the reply was originally posted. |


Errors
------

Errors are represented in the `error` field of the response. The error
field is always present, but is usually false. If its not false, it is
an object with the fields `code` and `description`. `code` is an integer
representing the type of failure, and `description` is a string describing
the problem. `description` is intended for human consumption; in your client
code, use the error codes to handle conditions. The `presentable` column
indicates whether the `description` should be shown to users verbatim.

| Code | Presentable  | Documentation                                     |
|------|--------------|---------------------------------------------------|
|    0 | Never, fix   | Malformed json input. `description` is the error  |
|      | your client  | string thrown by the server-side json decoder.    |
|------|--------------|---------------------------------------------------|
|    1 | Not a good   | Internal server error. Unaltered exception text   |
|      | idea, the    | is returned as `description`. This shouldn't      |
|      | exceptions   | happen, and if it does, make a bug report.        |
|      | are not      | clients should not attempt to intelligently       |
|      | helpful      | recover from any errors of this class.            |
|------|--------------|---------------------------------------------------|
|    2 | Nadda.       | Unknown `method` was requested.                   |
|------|--------------|---------------------------------------------------|
|    3 | Fix. Your.   | Missing or malformed parameter values for the     |
|      | Client.      | requested `method`.                               |
|------|--------------|---------------------------------------------------|
|    4 | Only during  | Invalid or unprovided `user`.                     |
|      | registration |                                                   |
|      |              | During registration, this code is returned with a |
|      |              | `description` that should be shown to the user.   |
|      |              | It could indicate an invalid name input, an       |
|      |              | occupied username, invalid/missing `auth_hash`,   |
|      |              | etc.                                              |
|------|--------------|---------------------------------------------------|
|    5 | Always       | `user` is not registered.                         |
|------|--------------|---------------------------------------------------|
|    6 | Always       | User `auth_hash` failed or was not provided.      |
|------|--------------|---------------------------------------------------|
|    7 | Always       | Requested thread does not exist.                  |
|------|--------------|---------------------------------------------------|
|    8 | Always       | Requested thread does not allow posts.            |
|------|--------------|---------------------------------------------------|
|    9 | Always       | Message edit failed; there is a 24hr limit for    |
|      |              | editing posts.                                    |
|------|--------------|---------------------------------------------------|
|   10 | Always       | User action requires `admin` privilege.           |
|------|--------------|---------------------------------------------------|
|   11 | Always       | Invalid formatting directives in text submission. |
