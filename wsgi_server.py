###Setting up a Web Server Gateway Interface (WSGI) to use with all python frameworks###
##Imports
import io 
import socket
import sys
from datetime import datetime

class wsgiServer(object):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 1

    def __init__(self, server_address):
        #Creating the listening socket
        self.listen_socket = listen_socket = socket.socket(
            self.address_family,
            self.socket_type
        )
        #Allow for address reuse
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(server_address)
        listen_socket.listen(self.request_queue_size)
        host, port = self.listen_socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        #Return headers set by web framework / web app
        self.headers_set = []

    def set_app(self, application):
        self.application = application

    def serve_forever(self):
        listen_socket = self.listen_socket
        while True:
            self.client_connection, client_address = listen_socket.accept()
            ##Handles one request and closes the connection
            ##Then loops over itself and waits for new connections.
            self.handle_one_request()

    def handle_one_request(self):
        request_data = self.client_connection.recv(1024)
        self.request_data = request_data = request_data.decode('UTF-8')
        print(''.join(
            f'<{line}\n' for line in request_data.splitlines()
            ))
        self.parse_request(request_data)

        #constructing the environment
        env = self.get_environ()

        #get back result that will become HTTP Response body.
        result = self.application(env, self.start_response)
        
        #Construct a response and send back to client. 
        self.finish_response(result)

    def parse_request(self, text):
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')
        #Break down the request line
        (self.request_method,
         self.path,
         self.request_version
         ) = request_line.split()
    
    def get_environ(self):
        env = {}
        #Required WSGI variables
        env['wsgi.version'] = (1,0)
        env['wsgi.input'] = 'http'
        env['wsgi.url_scheme'] = io.StringIO(self.request_data)
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        #Required CGI Variables
        env['REQUEST_METHOD'] = self.request_method
        env['PATH_INFO'] = self.path
        env['SERVER_NAME'] = self.server_name
        env['SERVER_PORT'] = str(self.server_port)
        return env

    def start_response(self, status, response_headers, exc_info=None):
        #Server headers
        server_headers = [
            ('Date', datetime.now()),
            ('Server', 'WSGIServer 0.2') 
        ]
        self.headers_set = [status,response_headers + server_headers]
        return self.finish_response

    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = f'HTTP/1.1 {status}\r\n'
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            for data in result:
                response += data.decode('utf-8')
            print(''.join(
                f'>{line}\n' for line in response.splitlines()
            ))
            response_bytes = response.encode()  
            self.client_connection.sendall(response_bytes)
        finally:
            self.client_connection.close()

SERVER_ADDRESS = HOST, PORT = '',8888

def make_server(server_address, application):
    server = wsgiServer(server_address)
    server.set_app(application)
    return server

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Provide WSGI app as an object as module:callable')    
    app_path = sys.argv[1]
    module,application = app_path.split(':')
    module = __import__(module)
    application = getattr(module,application)
    httpd = make_server(SERVER_ADDRESS, application)
    print(f'WSGIServer: Serving on port {PORT}...')
    httpd.serve_forever()