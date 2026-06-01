import usocket as socket
import ussl as ssl
import ubinascii

class SMTPSession:
    def __init__(self, host, port, ssl_context=True):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.sock = None

    def _send(self, data):
        self.sock.write((data + "\r\n").encode())

    def _recv(self):
        resp = self.sock.readline()
        print("SMTP:", resp)
        return resp

    def _recv_all(self):
        while True:
            resp = self._recv()
            if not resp:
                break
            if len(resp) >= 4 and resp[3:4] == b" ":
                break

    def login(self, user, password):
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]

        self.sock = socket.socket()
        self.sock.connect(addr)

        if self.ssl_context:
            self.sock = ssl.wrap_socket(
                self.sock,
                server_hostname=self.host
            )

        # Welcome
        self._recv()

        # EHLO
        self._send("EHLO esp32")
        self._recv_all()

        # AUTH
        self._send("AUTH LOGIN")
        self._recv()

        # USER
        self._send(
            ubinascii.b2a_base64(
                user.encode()
            ).decode().strip()
        )
        self._recv()

        # PASS
        self._send(
            ubinascii.b2a_base64(
                password.encode()
            ).decode().strip()
        )

        resp = self._recv()

        if not resp.startswith(b"235"):
            raise Exception(
                "Falha autenticação SMTP: {}".format(resp)
            )

    def sendmail(self, from_addr, to_addr, msg):

        self._send("MAIL FROM:<{}>".format(from_addr))
        self._recv()

        self._send("RCPT TO:<{}>".format(to_addr))
        self._recv()

        self._send("DATA")
        self._recv()

        self.sock.write((msg + "\r\n.\r\n").encode())

        self._recv()

    def quit(self):
        try:
            self._send("QUIT")
        except:
            pass

        try:
            self.sock.close()
        except:
            pass