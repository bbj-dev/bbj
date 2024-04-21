from hashlib import sha256
import socket
import json


class BBJ:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.username  = None
        self.auth_hash = None


    def __call__(self, method, **params):
        return self.request(method, **params)


    def setuser(self, username, unhashed_password):
        self.auth_hash = sha256(bytes(unhashed_password, "utf8")).hexdigest()
        self.username = username
        return self.auth_hash


    def request(self, method, **params):
        params["method"] = method

        if not params.get("user") and self.username:
            params["user"] = self.username

        if not params.get("auth_hash") and self.auth_hash:
            params["auth_hash"] = self.auth_hash


        connection = socket.create_connection((self.host, self.port))
        connection.sendall(bytes(json.dumps(params), "utf8"))
        connection.shutdown(socket.SHUT_WR)

        try:
            buff, length = bytes(), 1
            while length != 0:
                recv = connection.recv(2048)
                length = len(recv)
                buff += recv

        finally:
            connection.close()

        response = json.loads(str(buff, "utf8"))
        if not isinstance(response, dict):
            return response

        error = response.get("error")
        if not error:
            return response

        code, desc = error["code"], error["description"]

        # tfw no qt3.14 python case switches
        if error in (0, 1):
            raise ChildProcessError("internal server error: " + desc)
        elif error in (2, 3):
            raise ChildProcessError(desc)

        return response
