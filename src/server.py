from socketserver import StreamRequestHandler, TCPServer
from src import endpoints
from src import schema
from src import db
import json


class RequestHandler(StreamRequestHandler):
    """
    Receieves and processes json input; dispatches input to the
    requested endpoint, or responds with error objects.
    """


    def reply(self, obj):
        self.wfile.write(bytes(json.dumps(obj), "utf8"))


    def handle(self):
        try:
            request = json.loads(str(self.rfile.read(), "utf8"))
            endpoint = request.get("method")

            if endpoint not in endpoints.endpoints:
                return self.reply(schema.error(2, "Invalid endpoint"))

            # check to make sure all the arguments for endpoint are provided
            elif any([key not in request for key in endpoints.endpoints[endpoint]]):
                return self.reply(schema.error(3, "{} requires: {}".format(
                    endpoint, ", ".join(endpoints.endpoints[endpoint]))))

            elif endpoint not in endpoints.authless:
                if not request.get("user"):
                    return self.reply(schema.error(4, "No username provided."))

                user = db.user_resolve(request["user"])
                request["user"] = user

                if not user:
                    return self.reply(schema.error(5, "User not registered"))

                elif endpoint != "check_auth" and not \
                     db.user_auth(user, request.get("auth_hash")):
                     return self.reply(schema.error(6, "Authorization failed."))

            # exception handling is now passed to the endpoints;
            # anything unhandled beyond here is a code 1
            self.reply(eval("endpoints." + endpoint)(request))

        except json.decoder.JSONDecodeError as E:
            return self.reply(schema.error(0, str(E)))

        except Exception as E:
            return self.reply(schema.error(1, str(E)))


def run(host, port):
    server = TCPServer((host, port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("bye")
        server.server_close()
