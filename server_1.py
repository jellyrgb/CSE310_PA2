'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util


class Server:
    '''
    This is the main Server Class. You will  write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.clients = {}

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.

        '''
        
        while True:
            data, addr = self.sock.recvfrom(1024)
            msg_type, seqno, data, checksum = util.parse_packet(data.decode())

            if msg_type == "join":
                self.handle_join(data, addr)
            elif msg_type == "request_users_list":
                self.handle_list_users(addr)
            elif msg_type == "send_message":
                self.handle_send_message(data, addr)
            elif msg_type == "disconnect":
                self.handle_disconnect(addr)
            else:
                print(f"Unknown command from {addr}")
        

    def handle_join(self, data, addr):
        username = data.split(' ')[2]
        
        if username in self.clients:
            self.send_error_message("ERR_USERNAME_UNAVAILABLE", addr)
        elif len(self.clients) >= 10:
            self.send_error_message("ERR_SERVER_FULL", addr)
        else:
            self.clients[username] = addr
            print(f"join: {username}")


    def send_error_message(self, error, addr):
        if error == "ERR_USERNAME_UNAVAILABLE":
            error_msg = "username not available"
        elif error == "ERR_SERVER_FULL":
            error_msg = "server full"
        else:
            error_msg = "unknown error"
        msg = f"err {error.lower()} {error_msg}"
        packet = util.make_packet(msg_type="data", msg=msg)
        self.sock.sendto(packet.encode(), addr)
        print(f"Sent error to {addr}: {error_msg}")


    def handle_list_users(self, addr):
        # Retrieve the username associated with the client's address, if it exists
        requesting_username = next((user for user, address in self.clients.items() if address == addr), None)

        # Proceed only if the requesting client is recognized (i.e., is in the clients list)
        if requesting_username:
            # Generate the list of usernames
            user_list = " ".join(sorted(self.clients.keys()))
            message = f"{len(self.clients)} {user_list}"
            
            # Format the message to be sent back
            msg = util.make_message("response_users_list", 3, message)
            packet = util.make_packet(msg_type="data", msg=msg)

            # Send the packet back to the requesting client
            self.sock.sendto(packet.encode(), addr)
            print(f"request_users_list: {requesting_username}")

        else:
            # If the client is not recognized, send an error
            self.send_error_message("ERR_INVALID_CLIENT", addr)

    def handle_send_message(self, data, addr):
        # Extract sender username based on the client's address
        sender_username = next((user for user, address in self.clients.items() if address == addr), None)

        if sender_username is None:
            self.send_error_message("ERR_INVALID_CLIENT", addr)
            return

        # Parse the data to extract the number of recipients, recipient usernames, and the actual message
        parts = data.split(' ')  # This should be adjusted based on actual expected data format

        if len(parts) < 4:
            self.send_error_message("ERR_INVALID_FORMAT", addr)
            return

        num_recipients = int(parts[2])
        recipient_names = parts[3:3 + num_recipients]  # Get the recipient names
        message = ' '.join(parts[3 + num_recipients:])  # The rest is the message

        # Forward the message to each specified recipient
        for recipient in recipient_names:
            if recipient in self.clients:
                recipient_addr = self.clients[recipient]

                num = 1
                msg_body = f"{num} {sender_username} {message}"
                forward_msg = util.make_message("forward_message", 4, msg_body)
                packet = util.make_packet(msg_type="forward_message", msg=forward_msg)
                self.sock.sendto(packet.encode(), recipient_addr)
                print(f"msg: {sender_username}")
            else:
                print(f"msg: {sender_username} to non-existent user {recipient}")

    def handle_disconnect(self, addr):
        """
        Handles a disconnect request from a client.
        :param addr: Address tuple of the client (IP, port) who wants to disconnect
        """
        # Find the username associated with the client's address
        username_to_remove = None
        for username, address in self.clients.items():
            if address == addr:
                username_to_remove = username
                break

        if username_to_remove:
            # Remove the client from the active clients list
            del self.clients[username_to_remove]
            # Log the disconnection
            print(f"disconnected: {username_to_remove}")
        else:
            self.send_error_message("ERR_INVALID_CLIENT", addr) 

# Do not change below part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
