The server has an endpoint called `db_sanity_check`. What this does is take
a `key` and a `value` and compares `value` to a set of rules specified by
`key`. This is the same function used internally by the database to scan
values before committing them to the database. By default it returns a
descriptive object under `data`, but you can specify the key/value pair
`"error": True` to get a standard error response back. A standard call
to `db_sanity_check` will look like this.

```
{
    "key": "title",
    "value": "this title\nis bad \nbecause it contains \nnewlines"
}
```

and the server will respond like this when the input should be corrected.

```
{
    "data": {
        "bool": False,
        "description": "Titles cannot contain whitespace characters besides spaces."
    },
    "error": False,
    "usermap": {}
}
```

if everything is okay, the data object will look like this instead.

```
    "data": {
        "bool": True,
        "description": null
    },
```

Alternatively, you can supply `"error": True` in the request.

```
{
    "error": True,
    "key": "title",
    "value": "this title\nis bad \nbecause it contains \nnewlines"
}
// and you get...
{
    "data": null,
    "usermap": {},
    "error": {
        "code": 4,
        "description": "Titles cannot contain whitespace characters besides spaces."
    }
}
```

The following keys are currently available.

  * "user_name"
  * "auth_hash"
  * "quip"
  * "bio"
  * "title"
  * "body"
  * "color"

The descriptions returned are friendly, descriptive, and should be shown
directly to users

## Implementing good sanity checks in your client

By using this endpoint, you will never have to validate values in your
own code before sending them to the server. This means you can do things
like implement an interactive prompt which will not allow the user to
submit it unless the value is correct.

This is used in the elisp client when registering users and for the thread
title prompt which is shown before opening a composure window. The reason
for rejection is displayed clearly to the user and input window is restored.

```
(defun bbj-sane-value (prompt key)
  "Opens an input loop with the user, where the response is
passed to the server to check it for validity before the
user is allowed to continue. Will recurse until the input
is valid, then it is returned."
  (let* ((value (read-from-minibuffer prompt))
         (response (bbj-request! 'db_sanity_check
                     'value value 'key key)))
    (if (alist-get 'bool response)
        value
      (message (alist-get 'description response))
      (sit-for 2)
      (bbj-sane-value prompt key))))
```
