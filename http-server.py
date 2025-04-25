'''
   A web server that handles one HTTP request at a time.

   Accepts and parses the HTTP request, get the requested file
   from the server’s file system, create an HTTP response message
   consisting of the requested file preceded by header lines, and
   then send the response directly to the client.

   If the requested file is not present in the server, the server
   should send an HTTP “404 Not Found” message back to the client.
'''

import sys
import socket          

# Server files are stored in the same directory as this python server
directory = './'  # 

# Handle HTTP requests
def handle_request(client_socket):
    
    # Receive the HTTP request from the client
    request = client_socket.recv(1024).decode()
    print(f"Received request:\n{request}")

    # Parse the request to get the requested file path
    request_lines = request.splitlines()
    if len(request_lines) == 0:
        client_socket.close()
        return

    # Extract the requested file path from the first line of the request
    method, path, _ = request_lines[0].split()
    if path == '/':
        path = '/index.html'  # Default file

    # Construct the full file path
    file_path = directory + path

    try:
        # Open and read the requested file
        with open(file_path, 'rb') as file:
            file_content = file.read()
        
        # Prepare the HTTP response headers
        response_headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(file_content)}\r\n"
            "\r\n"
        ).encode()

        # Send the headers and file content to the client
        client_socket.send(response_headers + file_content)
        print(f"Sent file: {file_path}")

    except FileNotFoundError:
        # If the file is not found, send a 404 Not Found response
        response_headers = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/html\r\n"
            "\r\n"
            "<h1>404 Not Found</h1>"
        ).encode()

        client_socket.send(response_headers)
        print(f"File not found: {file_path}")

    finally:
        # Close the client socket
        client_socket.close()

# Main function to start the server
def start_server(host='127.0.0.1', port=8080):
    
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to the server address and port
    server_socket.bind((host, port))
    print(f"Server started on http://{host}:{port}")

    # Listen for incoming connections
    server_socket.listen(1)
    print("Waiting for connections...")

    while True:
        # Accept a new connection
        client_socket, client_address = server_socket.accept()
        print(f"Connection from: {client_address}")

        # Handle the client's request
        handle_request(client_socket)

# Run the server
if __name__ == '__main__':
    # The server's IP address and port
    host = '127.0.0.1'
    port = int(sys.argv[1])
    start_server(host, port)
