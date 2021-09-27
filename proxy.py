import sys
import socket
import threading
import select

def main():

    # retrieve arguments
    try:
        proxy_port = int(sys.argv[1])
        proxy_telemetry = int(sys.argv[2])
        proxy_blacklist_path = sys.argv[3]

    except IndexError:
        print("USAGE: python3 proxy.py <port> <flag_telemetry (0 or 1)> <filename of blacklist>")
        return

    # set up proxy socket
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(('', proxy_port))
    proxy_socket.listen(5)
    print("Proxy is listening at port: " + str(proxy_port))

    # spawn a thread for every request
    while True:
        client, address = proxy_socket.accept()
        proxy_thread = ProxyThread(client)
        proxy_thread.start()



class ProxyThread(threading.Thread):
    
    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client
        self.server = None


    # overriden method from threading.Thread library
    def run(self):
        method, hostname_port, http_version = self.parse_request()
        print(method, hostname_port, http_version, "\n")
        
        self.handle_request(method, hostname_port, http_version)

        self.client.close()
        self.server.close()


    def parse_request(self):
        request = ""
    
        while True:
            request += self.client.recv(1024).decode('ISO-8859-1')
            end_index = request.find('\r\n')
            
            if end_index > -1:
                parsed_request = request[:end_index].split(" ")
                # obtains method, hostname:port and http_version respectively
                return parsed_request[0], parsed_request[1], parsed_request[2]


    def handle_request(self, method, hostname_port, http_version):
        if method == "CONNECT":
            
            parsed_address = hostname_port.split(":")
            server_hostname = parsed_address[0]
            server_port = parsed_address[1]

            server_info = socket.getaddrinfo(server_hostname, server_port)
            address_family = server_info[0][0]
            server_address = server_info[0][4]
            # print(address_family, server_address, "\n")

            self.server = socket.socket(address_family)
            self.server.connect(server_address)
            self.client.send(bytes((http_version + " 200 Connection established\r\n\r\n"), encoding="ISO-8859-1"))

            # classify into readable, writable and check for exception lists
            readable_list = [self.client, self.server]
            writable_list = []
            exceptional_list = [self.client, self.server]

            while True:
                is_readable_list, is_writable_list, has_error_list = select.select(readable_list, writable_list, exceptional_list)
                if len(has_error_list) > 0:
                    break
                if len(is_readable_list) == 0:
                    break
                for host in is_readable_list:
                    data = host.recv(1024)
                    if host == self.server:
                        sender_host = self.client
                    else:
                        sender_host = self.server
                    if data:
                        sender_host.send(data)

        else:
            print("handle this later")
            return



if __name__ == '__main__':
    main()
