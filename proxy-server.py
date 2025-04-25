'''
Proxy Server at 127.0.0.1:port
Handles HTTP requests.
'''

import socket, sys, time
from _thread import start_new_thread
import mimetypes

class Server:
    # Constructors initializing basic architecture
    def __init__(self):
        self.max_conn = 0
        self.buffer_size = 0
        self.port = 0

    # Function which triggers the server
    def start_server(self, conn=5, buffer=4096, port=7070):
        try:
            self.listen(conn, buffer, port)

        except KeyboardInterrupt:
            print("Interrupting Server.")
            time.sleep(.5)

        finally:
            print("Stopping Server...")
            sys.exit()

    # Listener for incoming connections
    def listen(self, No_of_conn, buffer, port):
        try:
            # using TCP
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            s.listen(No_of_conn)
            print("Listening...")

        except:
            print("Error: Cannot start listening...")
            sys.exit(1)

        while True:
            # Accepting new connections at another thread
            try:
                conn, addr = s.accept()
                start_new_thread(self.connection_read_request, (conn, addr, buffer))

            except Exception as e:
                print("Error: Cannot establish connection..." + str(e))
                sys.exit(1)

        s.close()

    # generate header to send response in HTTPS connections
    def generate_header_lines(self, code, length, file_path=None):
        h = ''
        if code == 200:
            h = 'HTTP/1.1 200 OK\n'
        elif code == 404:
            h = 'HTTP/1.1 404 Not Found\n'

        # Infer Content-Type from file extension
        # It’s a default fallback when the type of file can't be determined.
        content_type = 'application/octet-stream'  # fallback # default, generic MIME type

        ###
        # if file_path exists:
        # convert to string if it's bytes
        # try to guess MIME type from the file name
        # if the guess was successful:
        # use that as content type
        # otherwise: keep the fallback
        
        if file_path: # if not None or empty
            # If file_path is a byte string (e.g., b'/path/file.jpg'), then decode it into a normal string using .decode()
            # Otherwise, just use file_path as it is
            # This tries to guess the MIME type of the file based on its filename or extension
            guessed_type, _ = mimetypes.guess_type(file_path.decode() if isinstance(file_path, bytes) else file_path)
            if guessed_type:
                content_type = guessed_type

        h += f'Content-Length: {length}\n'
        h += f'Content-Type: {content_type}\n'
        h += 'Connection: close\n\n'
        return h


    # Function to read request data
    def connection_read_request(self, conn, addr, buffer):
        # Try to split necessary info from the header
        try:
            request = conn.recv(buffer)
            header = request.split(b'\n')[0]
            requested_file = request
            requested_file = requested_file.split(b' ')
            url = header.split(b' ')[1]

            # Strip Port and Domain
            hostIndex = url.find(b"://")
            if hostIndex == -1:
                temp = url
            else:
                temp = url[(hostIndex + 3):]

            portIndex = temp.find(b":")

            serverIndex = temp.find(b"/")
            if serverIndex == -1:
                serverIndex = len(temp)

            # If no port in header i.e, if http connection then use port 80 else the port in header
            webserver = ""
            port = -1
            if (portIndex == -1 or serverIndex < portIndex):
                port = 80
                webserver = temp[:serverIndex]
            else:
                port = int((temp[portIndex + 1:])[:serverIndex - portIndex - 1])
                webserver = temp[:portIndex]

            # Strip requested file to see if it exists in cache
            requested_file = requested_file[1]
            print("Requested File ", requested_file)

            # Stripping method to find if HTTPS (CONNECT) or HTTP (GET)
            method = request.split(b" ")[0]

            # If method is CONNECT (HTTPS)
            if method == b"CONNECT":
                print("CONNECT Request")
                self.https_proxy(webserver, port, conn, request, addr, buffer, requested_file)

            # If method is GET (HTTP)
            else:
                print("GET Request")
                self.http_proxy(webserver, port, conn, request, addr, buffer, requested_file)

        except Exception as e:
            return

    # Function to handle HTTP Request
    def http_proxy(self, webserver, port, conn, request, addr, buffer_size, requested_file):
        # Stripping file name
        requested_file = requested_file.replace(b".", b"_").replace(b"http://", b"_").replace(b"/", b"")

        # Try to find in cache
        try:
            print("Searching for: ", requested_file)
            print("Cache Hit")
            file_handler = open(b"cache/" + requested_file, 'rb')
            response_content = file_handler.read()
            file_handler.close()
            response_headers = self.generate_header_lines(200, len(response_content), requested_file)
            conn.send(response_headers.encode("utf-8"))
            time.sleep(1)
            conn.send(response_content)
            conn.close()

        # If no cache hit, request from web
        except Exception as e:
            print(e)
            try:
                # the following socket is used to connect to the real web server, not the client
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                s.connect((webserver, port))
                s.send(request)

                print("Forwarding request from ", addr, " to ", webserver)
                # s.makefile('wb', 0) turns the socket s into a file-like object for writing bytes.
                file_object = s.makefile('wb', 0)
                # 'wb' → Write in binary mode.
                # 0 → Unbuffered. This means data is immediately sent, without waiting for a buffer to fill.
                # This is helpful because HTTP is very sequential—write request, get response.
                
                file_object.write(b"GET " + b"http://" + requested_file + b" HTTP/1.0\n\n")
                # Then, a new GET request is constructed and written to the server:
                # b"GET " + b"http://" + requested_file + b" HTTP/1.0\n\n"
                # This is a bit suspicious. Normally, you’d use just a path (GET /index.html HTTP/1.0), not a full URL. Sending http://... in the GET line is only used in proxy-style requests (not direct ones), so it may depend on how requested_file is structured.
                
                # Read the response into buffer
                file_object = s.makefile('rb', 0)
                buff = file_object.readlines()
                temp_file = open(b"cache/" + requested_file, "wb+")
                for i in range(0, len(buff)):
                    temp_file.write(buff[i])
                    conn.send(buff[i])

                print("Request of client " + str(addr) + " completed...")
                s.close()
                conn.close()

            except Exception as e:
                print("Error: forward request..." + str(e))
                return

    # Function to handle HTTPS Connection
    def https_proxy(self, webserver, port, conn, request, addr, buffer_size, requested_file):
        # Strip for filename
        requested_file = requested_file.replace(b".", b"_").replace(b"http://", b"_").replace(b"/", b"")

        # Trying to find in cache
        try:
            print("Searching for: ", requested_file)
            file_handler = open(b"cache/" + requested_file, 'rb')
            print("\n")
            print("Cache Hit\n")
            response_content = file_handler.read()
            file_handler.close()
            response_headers = self.generate_header_lines(200, len(response_content))
            conn.send(response_headers.encode("utf-8"))
            time.sleep(1)
            conn.send(response_content)
            conn.close()

        # If no Cache Hit, request data from web
        except:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                # If successful, send 200 code response
                s.connect((webserver, port))
                reply = "HTTP/1.0 200 Connection established\r\n"
                reply += "\r\n"
                conn.sendall(reply.encode())
            except socket.error as err:
                pass
            
            conn.setblocking(0) 
            s.setblocking(0)
            # Makes both sockets non-blocking — no recv() or send() call will block the thread. It allows for simultaneous I/O.
            
            print("HTTPS Connection Established")
            while True:
                try:
                    request = conn.recv(buffer_size)
                    s.sendall(request)
                except socket.error as err:
                    pass

                try:
                    reply = s.recv(buffer_size)
                    conn.sendall(reply)
                except socket.error as e:
                    pass

if __name__ == "__main__":
    server = Server()
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        print("Usage: python proxy_server.py <port>")
        sys.exit(1)
    server.start_server(conn=5, buffer=4096, port=port)
