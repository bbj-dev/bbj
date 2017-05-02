"""
This is a small script that creates the endpoint doc page. It should be
evoked from the command line each time changes are made. It writes
to ./documentation/docs/api_overview.md

The code used in this script is the absolute minimum required to
get the job done; it can be considered a crude hack at best. I am
more interested in writing good documentation than making sure that
the script that shits it out is politcally correct ;)
"""

from server import API
import pydoc

body = """
# How to BBJ?

## Input

BBJ is interacted with entirely through POST requests, whose bodies are
json objects.

The endpoints, all listed below, can be contacted at the path /api/ relative
to the root of where BBJ is hosted. If bbj is hosted on a server on port 80
at the root:

`http://server.com/api/endpoint_here`

The body of your request contains all of it's argument fields, instead of
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
not clog up any pipes :) In the same vein, endpoints who dont take arguments
don't care if you supply them anyway.

## Output

BBJ returns data in a consistently formatted json object. The base object
has three keys: `data`, `usermap`, and `error`. Visualizied:

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
are user objects. It should be noted that the anonymous user has it's own
ID and profile object as well.

### error

`error` is typically `false`. If it is __not__ false, then the request failed
and the json object that `error` contains should be inspected. (see the above
visualation) Errors follow a strict code system, making it easy for your client
to map these responses to native exception types or signals in your language of
choice. See [the full error page](errors.md) for details.


"""

endpoints = [
    ref for name, ref in API.__dict__.items()
    if hasattr(ref, "exposed")
]

types = {
    function.doctype: list() for function in endpoints
}

for function in endpoints:
    types[function.doctype].append(function)

for doctype in sorted(types.keys()):
    body += "# %s\n\n" % doctype
    funcs = sorted(types[doctype], key=lambda _: _.__name__)
    for f in funcs:
        body += "## %s\n\n%s\n\n" % (f.__name__, pydoc.getdoc(f))
    body += "\n\n--------\n\n"

with open("documentation/docs/api_overview.md", "w") as output:
    output.write(body)
