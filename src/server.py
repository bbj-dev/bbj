from socketserver import StreamRequestHandler, TCPServer
from src import endpoints
from src import schema
from src import db
import json


class RequestHandler(StreamRequestHandler):
    """
    Receieves and processes json input; dispatches input to the
    approproate endpoint, or responds with error objects.
    """


    def reply(self, dictionary):
        self.wfile.write(bytes(json.dumps(dictionary), "utf8"))


    def handle(self):
        try:
            request = json.loads(str(self.rfile.read(), "utf8"))
            endpoint = request.get("method")

            if endpoint not in endpoints.endpoints:
                raise IndexError("Invalid endpoint")

            # check to make sure all the arguments for endpoint are provided
            elif any([key not in request for key in endpoints.endpoints[endpoint]]):
                raise ValueError("{} requires: {}".format(
                    endpoint, ", ".join(endpoints.endpoints[endpoint])))

            elif endpoint not in endpoints.authless:
                if not request.get("user"):
                    raise ConnectionError("No username provided.")

                user = db.user_resolve(request["user"])
                request["user"] = user

                if not user:
                    raise ConnectionAbortedError("User not registered")

                elif endpoint != "check_auth" and not db.user_auth(user, request.get("auth_hash")):
                    raise ConnectionRefusedError("Authorization failed.")

        except json.decoder.JSONDecodeError as E:
            return self.reply(schema.error(0, str(E)))

        except IndexError as E:
            return self.reply(schema.error(2, str(E)))

        except ValueError as E:
            return self.reply(schema.error(3, str(E)))

        except ConnectionError as E:
            return self.reply(schema.error(4, str(E)))

        except ConnectionAbortedError as E:
            return self.reply(schema.error(5, str(E)))

        except ConnectionRefusedError as E:
            return self.reply(schema.error(6, str(E)))

        except Exception as E:
            return self.reply(schema.error(1, str(E)))

        try:
            self.reply(eval("endpoints." + endpoint)(request))
        except Exception as E:
            self.reply(schema.error(1, str(E)))


def run(host, port):
    server = TCPServer((host, port), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("bye")
        server.server_close()
