import sys
import socket
import threading
import select
import time
import queue

clients = queue.Queue()

def main():

    # retrieve arguments
    try:
        proxy_port = int(sys.argv[1])
        telemetry = int(sys.argv[2])
        blacklist_file = sys.argv[3]
        blacklisted_urls = Extensions.parse_blacklist_txt(blacklist_file)
        extensions = Extensions(telemetry, blacklisted_urls)

    except (IndexError, ValueError):
        print("USAGE: python3 proxy.py <port (Integer)> <flag_telemetry (0 or 1)> <filename of blacklist (String)>")
        print("Please ensure that the arguments are in the correct format.")
        return

    # set up proxy socket
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(('', proxy_port))
    proxy_socket.listen(100)
    print("Proxy is listening at port: " + str(proxy_port), "\n")

    # a separate thread for listening for connections
    clients_thread = GetClientsThread(proxy_socket)
    clients_thread.start()

    # spawn at most 8 threads (excluded the first thread for connections as above)
    while True:
        # time.sleep(0)
        if threading.active_count() <= 8:
            proxy_thread = ProxyThread(clients.get(), extensions)
            proxy_thread.start()
            # print("Current number of clients in queue: ", clients.qsize())



class GetClientsThread(threading.Thread):

    def __init__(self, proxy):
        threading.Thread.__init__(self)
        self.proxy = proxy

    def run(self):
        # simply listens for connections
        while True:
            client, address = self.proxy.accept()
            clients.put(client)



class Extensions:

    def __init__(self, telemetry, blacklisted_urls):
        self.telemetry = telemetry
        self.blacklisted_urls = blacklisted_urls


    def get_telemetry(self):
        return self.telemetry


    def get_blacklisted_urls(self):
        return self.blacklisted_urls


    @classmethod
    def parse_blacklist_txt(self, blacklist_file):
        txt = open(blacklist_file, "r")
        urls = []
        for url in txt:
            # remove one-line breaks and append to urls array
            urls.append(url.strip())
        print("Blacklisted sites:")
        print(urls)
        return urls



class ProxyThread(threading.Thread):

    HTTP_METHODS = ["GET", "CONNECT", "POST", "PUT", "PATCH", "DELETE", "HEAD", "TRACE", "OPTIONS"]


    def __init__(self, client, extensions):
        threading.Thread.__init__(self)
        self.client = client
        self.server = None
        self.additional_request_data = None
        self.hostname = None
        self.size = 0
        self.start_time = None
        self.end_time = None
        self.extensions = extensions


    # overriden method from threading.Thread library
    def run(self):
        try:
            method, url, http_version = self.parse_request()

            # check if url is blacklisted
            blacklisted_urls = self.extensions.get_blacklisted_urls()
            is_blacklisted = False;
            for blacklist_url in blacklisted_urls:
                if blacklist_url in url:
                    is_blacklisted = True;
                    self.client.close()
                    self.server.close()

            self.hostname = url
            # print(method, url, http_version, "\n")
            self.handle_request(method, url, http_version)
            self.client.close()
            self.server.close()
            self.end_time = time.time()

            # handle telemetry
            telemetry_enabled = self.extensions.get_telemetry() == 1;
            if telemetry_enabled:
                # fetch time
                fetch_time = str(format((self.end_time - self.start_time), ".3f"))
                print("Hostname: " + url.split(":")[0] + ", Size: " + str(self.size) + " bytes, Time: " + fetch_time + " sec")

            # print("Threads active (including main but excluding current thread): ", threading.active_count() - 1, "\n")

            return

        except AttributeError:
            # throw error message to inform user that url is blacklisted
            if (is_blacklisted):
                print("Site " + str(url) + " is blacklisted in blacklist.txt. Closing connection.")
            # if the error is not due to blacklisting, don't catch it
            else:
                raise AttributeError


    # receive requests from client -> extract method, url, http_version
    def parse_request(self):
        request = ""

        while True:
            self.start_time = time.time()
            # request from client
            request += self.client.recv(1024).decode('ISO-8859-1')
            end_index = request.find('\r\n')
            
            if end_index > -1:
                # e.g CONNECT play.google.com:443 HTTP/1.1
                parsed_request = request[:end_index].split(" ")
                # e.g of additional request data
                # User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0
                # Proxy-Connection: keep-alive
                # Connection: keep-alive
                # Host: ssl.gstatic.com:443
                self.additional_request_data = bytes((request[end_index + 1:]), encoding="ISO-8859-1")
                # obtains method, url and http_version respectively
                return parsed_request[0], parsed_request[1], parsed_request[2]


    # method, url, http_version -> send requests to server
    def handle_request(self, method, url, http_version):
        
        if method not in self.HTTP_METHODS:
            print("Method is not supported!")
            return

        if method == "CONNECT":
            # e.g www.google.com:443
            parsed_address = url.split(":")
            # e.g www.google.com
            server_hostname = parsed_address[0]
            # e.g 443
            server_port = parsed_address[1]

        else:
            parsed_url = url.split("://")[1].split("/")
            # get the first part of the url (host name)
            server_hostname = parsed_url[0]
            # get the path after the hostname eg. /index
            url = parsed_url[1]
            server_port = 80

        server_info = socket.getaddrinfo(server_hostname, server_port)
        # e.g AddressFamily.AF_INET
        address_family = server_info[0][0]
        # e.g ('74.125.24.139', 443)
        server_address = server_info[0][4]
        # print(address_family, server_address, "\n")

        # establish connection with server socket
        self.server = socket.socket(address_family)
        self.server.connect(server_address)
        # if client attempts to establish a TCP connection, inform client that connection has been
        # established with server
        if method == "CONNECT":
            self.client.send(bytes((http_version + " 200 Connection established\r\n\r\n"), encoding="ISO-8859-1"))
        # otherwise, use the proxy tunnel to send HTTP messages to server
        else:
            self.server.send(bytes((method + " " + url + " " + http_version), encoding="ISO-8859-1"))
            self.server.send(self.additional_request_data)

        # classify into readable, writable and check for exception lists
        readable_list = [self.client, self.server]
        writable_list = []
        exceptional_list = [self.client, self.server]

        # interaction between client and server through proxy
        not_done = True
        while not_done:
            is_readable_list, is_writable_list, has_error_list = select.select(readable_list, writable_list, exceptional_list)
            # print("is readable")
            # print(is_readable_list)
            # print("is writable")
            # print(is_writable_list)
            # print("has error list")
            # print(has_error_list)
            try:
                if len(has_error_list) > 0:
                    break
                if len(is_readable_list) == 0:
                    break
                for sender_socket in is_readable_list:
                    data = sender_socket.recv(1024)
                    # data can come from either the client or server
                    # if data comes from server, send to client
                    if sender_socket == self.server:
                        receiver_socket = self.client
                        # telemetry requires us to find stream size of object from web server
                        self.size += len(data)
                    # if data comes from client, send to server
                    else:
                        receiver_socket = self.server
                    if data:
                        receiver_socket.send(data)
                    else:
                        not_done = False
                        break
            # # suppress error to show only valid telemetry entries
            except:
                pass

if __name__ == '__main__':
    main()
