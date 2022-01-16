
# How to BBJ?

## Input

BBJ is interacted with entirely through POST requests, whose bodies are
json objects.

The endpoints, all listed below, can be contacted at the path /api/ relative
to the root of where BBJ is hosted. If bbj is hosted on a server on port 80
at the root:

`http://server.com/api/endpoint_here`

The body of your request contains all of its argument fields, instead of
using URL parameters. As a demonstration, to call `thread_create`,
it requires two arguments: `title`, and `body`. We put those argument
names at the root of the json object, and their values are the info
passed into the API for that spot. Your input will look like this:

```json
{
    "title": "Hello world!!",
    "body": "Hi! I am exploring this cool board thing!!"
}
```

And you will POST this body to `http://server.com:PORT/api/thread_create`.

A few endpoints do not require any arguments. These can still be POSTed to,
but the body may be completely empty or an empty json object. You can even
GET these if you so choose.

For all endpoints, argument keys that are not consumed by the endpoint are
ignored. Posting an object with a key/value pair of `"sandwich": True` will
not clog up any pipes :) In the same vein, endpoints who don't take arguments
don't care if you supply them anyway.

## Output

BBJ returns data in a consistently formatted json object. The base object
has three keys: `data`, `usermap`, and `error`. Visualized:

```javascript
{
  "error":   false, // boolean false or error object
  "data":    null,  // null or the requested data from endpoint.
  "usermap": {}     // potentially empty object, maps user_ids to user objects
}

// If "error" is true, it looks like this:

{
  "error": {
      "code": // an integer from 0 to 5,
      "description": // a string describing the error in detail.
  }
  "data": null   // ALWAYS null if error is not false
  "usermap": {}  // ALWAYS empty if error is not false
}
```

### data

`data` is what the endpoint actually returns. The type of contents vary
by endpoint and are documented below. If an endpoint says it returns a
boolean, it will look like `"data": True`. If it says it returns an array,
it will look like `"data": ["stuff", "goes", "here"]`

### usermap

The usermap is a json object mapping user_ids within `data` to full user
objects. BBJ handles users entirely by an ID system, meaning any references
to them inside of response data will not include vital information like their
username, or their profile information. Instead, we fetch those values from
this usermap object. All of it's root keys are user_id's and their values
are user objects. It should be noted that the anonymous user has its own
ID and profile object as well.

### error

`error` is typically `false`. If it is __not__ false, then the request failed
and the json object that `error` contains should be inspected. (see the above
visualation) Errors follow a strict code system, making it easy for your client
to map these responses to native exception types or signals in your language of
choice. See [the full error page](errors.md) for details.


<br><br>
# Authorization
------
See also [the Authorization page](authorization.md).
## check_auth

**Arguments:**

 * __target_user__: string: either a user_name or a user_id

 * __target_hash__: string: sha256 hash for the password to check



Returns boolean `true` or `false` of whether the hash given
is correct for the given user.


<br>
<br><br>
# Threads & Messages
------
## delete_post

**Arguments:**

 * __thread_id__: string: the id of the thread this message was posted in.

 * __post_id__: integer: the id of the target message.



Requires the arguments `thread_id` and `post_id`.

Delete a message from a thread. The same rules apply
here as `edit_post` and `edit_query`: the logged-in user
must either be the one who posted the message within 24hrs,
or have admin rights. The same error descriptions and code
are returned on falilure. Boolean true is returned on
success.

If the post_id is 0, the whole thread is deleted.


<br>
## edit_post

**Arguments:**

 * __thread_id__: string: the thread the message was posted in.

 * __post_id__: integer: the target post_id to edit.

 * __body__: string: the new message body.

 * __OPTIONAL: send_raw__: boolean: set the formatting mode for the target message.



Replace a post with a new body. Requires the arguments
`thread_id`, `post_id`, and `body`. This method verifies
that the user can edit a post before commiting the change,
otherwise an error object is returned whose description
should be shown to the user.

To perform sanity checks and retrieve the unformatted body
of a post without actually attempting to replace it, use
`edit_query` first.

Optionally you may also include the argument `send_raw` to
set the message's formatting flag. However, if this is the
only change you would like to make, you should use the
endpoint `set_post_raw` instead.

Returns the new message object.


<br>
## edit_query

**Arguments:**

 * __thread_id__: string: the id of the thread the message was posted in.

 * __post_id__: integer: the id of the target message.



Queries the database to ensure the user can edit a given
message. Requires the arguments `thread_id` and `post_id`
(does not require a new body)

Returns the original message object without any formatting
on success. Returns a descriptive code 4 otherwise.


<br>
## message_feed

**Arguments:**

 * __time__: int/float: epoch/unix time of the earliest point of interest

 * __OPTIONAL: format__: string: the specifier for the desired formatting engine



Returns a special object representing all activity on the board since `time`.

```javascript
{
    "threads": {
        "thread_id": {
            // ...thread object
        },
        // ...more thread_id/object pairs
    },
    "messages": [
        ...standard message object array sorted by date
    ]
}
```

The message objects in `messages` are the same objects returned
in threads normally. They each have a thread_id parameter, and
you can access metadata for these threads by the `threads` object
which is also provided.

The `messages` array is already sorted by submission time, newest
first. The order in the threads object is undefined, and you should
instead use their `last_mod` attribute if you intend to list them
out visually.


<br>
## set_post_raw

**Arguments:**

 * __thread_id__: string: the id of the thread the message was posted in.

 * __post_id__: integer: the id of the target message.

 * __value__: boolean: the new `send_raw` value to apply to the message.



Requires the boolean argument of `value`, string argument
`thread_id`, and integer argument `post_id`. `value`, when false,
means that the message will be passed through message formatters
before being sent to clients. When `value` is true, this means
it will never go through formatters, all of its whitespace is
sent to clients verbatim and expressions are not processed.

The same rules for editing messages (see `edit_query`) apply here
and the same error objects are returned for violations.

You may optionally set this value as well when using `edit_post`,
but if this is the only change you want to make to the message,
using this endpoint instead is preferable.


<br>
## set_thread_pin

**Arguments:**

 * __thread_id__: string: the id of the thread to modify.

 * __value__: boolean: `true` to pin thread, `false` otherwise.



Requires the arguments `thread_id` and `value`. `value`
must be a boolean of what the pinned status should be.
This method requires that the caller is logged in and
has admin status on their account.

Returns the same boolean you supply as `value`


<br>
## thread_create

**Arguments:**

 * __body__: string: The body of the first message

 * __title__: string: The title name for this thread

 * __OPTIONAL: send_raw__: boolean: formatting mode for the first message.



Creates a new thread and returns it. Requires the non-empty
string arguments `body` and `title`.

If the argument `send_raw` is specified and has a non-nil
value, the OP message will never recieve special formatting.


<br>
## thread_index

**Arguments:**

 * __OPTIONAL: include_op__: boolean: Include a `messages` object containing the original post



Return an array with all the server's threads. They are already sorted for
you; most recently modified threads are at the beginning of the array.
Unless you supply `include_op`, these threads have no `messages` parameter.
If you do, the `messages` parameter is an array with a single message object
for the original post.


<br>
## thread_load

**Arguments:**

 * __thread_id__: string: the thread to load.

 * __OPTIONAL: op_only__: boolean: include only the original message in `messages`

 * __OPTIONAL: format__: string: the formatting type of the returned messages.



Returns the thread object with all of its messages loaded.
Requires the argument `thread_id`. `format` may also be
specified as a formatter to run the messages through.
Currently, only "sequential" is supported.

You may also supply the parameter `op_only`. When it's value
is non-nil, the messages array will only include post_id 0 (the first)


<br>
## thread_reply

**Arguments:**

 * __thread_id__: string: the id for the thread this message should post to.

 * __body__: string: the message's body of text.

 * __OPTIONAL: send_raw__: boolean: formatting mode for the posted message.



Creates a new reply for the given thread and returns it.
Requires the string arguments `thread_id` and `body`

If the argument `send_raw` is specified and has a non-nil
value, the message will never recieve special formatting.


<br>
<br><br>
# Tools
------
## db_validate

**Arguments:**

 * __key__: string: the identifier for the ruleset to check.

 * __value__: VARIES: the object for which `key` will check for.

 * __OPTIONAL: error__: boolean: when `true`, will return an API error response instead of a special object.



See also [the Input Validation page](validation.md).

Requires the arguments `key` and `value`. Returns an object
with information about the database sanity criteria for
key. This can be used to validate user input in the client
before trying to send it to the server.

If the argument `error` is supplied with a non-nil value,
the server will return a standard error object on failure
instead of the special object described below.

The returned object has two keys:

{
  "bool": true/false,
  "description": null/"why this value is bad"
}

If bool == false, description is a string describing the
problem. If bool == true, description is null and the
provided value is safe to use.


<br>
## format_message

**Arguments:**

 * __body__: string: the message body to apply formatting to.

 * __format__: string: the specifier for the desired formatting engine



Requires the arguments `body` and `format`. Applies
`format` to `body` and returns the new object. See
`thread_load` for supported specifications for `format`.


<br>
## user_map

_requires no arguments_

Returns an array with all registered user_ids, with the usermap
object populated by their full objects. This method is _NEVER_
neccesary when using other endpoints, as the usermap returned
on those requests already contains all the information you will
need. This endpoint is useful for statistic purposes only.


<br>
<br><br>
# Users
------
## get_me

_requires no arguments_

Requires no arguments. Returns your internal user object,
including your `auth_hash`.


<br>
## is_admin

**Arguments:**

 * __target_user__: string: user_id or user_name to check against.



Requires the argument `target_user`. Returns a boolean
of whether that user is an admin.


<br>
## user_get

**Arguments:**

 * __target_user__: string: either a user_name or a user_id



Returns a user object for the given target.


<br>
## user_is_registered

**Arguments:**

 * __target_user__: string: either a user_name or a user_id



Returns boolean `true` or `false` of whether the given target is
registered on the server.


<br>
## user_register

**Arguments:**

 * __user_name__: string: the desired display name

 * __auth_hash__: string: a sha256 hash of a password



Register a new user into the system and return the new user object
on success. The returned object includes the same `user_name` and
`auth_hash` that you supply, in addition to all the default user
parameters. Returns code 4 errors for any failures.


<br>
## user_update

**Arguments:**

 * __Any of the following may be submitted__: 

 * __user_name__: string: a desired display name

 * __auth_hash__: string: sha256 hash for a new password

 * __quip__: string: a short string that can be used as a signature

 * __bio__: string: a user biography for their profile

 * __color__: integer: 0-6, a display color for the user



Receives new parameters and assigns them to the user object.
This method requires that you send a valid User/Auth header
pair with your request, and the changes are made to that
account.

Take care to keep your client's User/Auth header pair up to date
after using this method.

The newly updated user object is returned on success,
including the `auth_hash`.


<br>
