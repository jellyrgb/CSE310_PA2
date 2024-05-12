'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util

# Constant to control maximum number of clients
MAX_NUM_CLIENTS = 10

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

            # Get main task from the data
            task = data.strip().split(' ')[0]

            # Handle the task accordingly
            if task == "join":
                self.handle_join(data, addr)
            elif task == "request_users_list":
                self.handle_list_users(addr)
            elif task == "send_message":
                self.handle_send_message(data, addr)
            elif task == "disconnect":
                self.handle_disconnect(addr)
            else:
                sender_username = next((user for user, address in self.clients.items() if address == addr), None)
                self.send_error_message("ERR_UNKNOWN_MESSAGE", addr, sender=sender_username)
        

    def handle_join(self, data, addr):
        """
        Handle a join request from a client.
        """
        username = data.split(' ')[2]
        
        # Check if the username is already taken or if the server is full
        if username in self.clients:
            self.send_error_message("ERR_USERNAME_UNAVAILABLE", addr)
        elif len(self.clients) >= MAX_NUM_CLIENTS:
            self.send_error_message("ERR_SERVER_FULL", addr)
        
        # Add the client to the active clients list
        else:
            self.clients[username] = addr
            print(f"join: {username}")


    def send_error_message(self, error, addr, sender=None):
        """
        Send an unknown message error to the client.
        """
        if error == "ERR_UNKNOWN_MESSAGE":
            error_msg = f"{sender} sent unknown command"
            print(f"disconnected: {error_msg}")

        msg = util.make_message(error, 2)
        packet = util.make_packet(msg_type="data", msg=msg)
        self.sock.sendto(packet.encode(), addr)


    def handle_list_users(self, addr):
        """
        Handle a request for the list of active users.
        """
        # Retrieve the username by the client's address
        requesting_username = next((user for user, address in self.clients.items() if address == addr), None)

        # Proceed if the client is recognized
        if requesting_username:
            # Generate the list of usernames
            user_list = " ".join(sorted(self.clients.keys()))
            message = f"{len(self.clients)} {user_list}"
            
            # Make the response packet
            msg = util.make_message("response_users_list", 3, message)
            packet = util.make_packet(msg_type="data", msg=msg)

            # Send the response packet to the client
            self.sock.sendto(packet.encode(), addr)
            print(f"request_users_list: {requesting_username}")

        else:
            # If the client is not recognized, send an error
            self.send_error_message("ERR_INVALID_CLIENT", addr)

    def handle_send_message(self, data, addr):
        """
        Handle a message sent by a client.
        """
        # Extract sender username by the client's address
        sender_username = next((user for user, address in self.clients.items() if address == addr), None)

        # If the client is not recognized, send an error
        if sender_username is None:
            self.send_error_message("ERR_INVALID_CLIENT", addr)
            return

        # Extract data
        parts = data.split(' ')  

        # Check if the message is in the correct format
        if len(parts) < 4:
            self.send_error_message("ERR_INVALID_FORMAT", addr)
            return

        # Extract the message data
        num_recipients = int(parts[2])
        recipient_names = parts[3:3 + num_recipients]  # Get the recipient names
        message = ' '.join(parts[3 + num_recipients:])  # Get the message part
        print(f"msg: {sender_username}")

        # Forward the message to each specified recipient
        for recipient in recipient_names:

            # If the recipient exists, send the message
            if recipient in self.clients:
                recipient_addr = self.clients[recipient]
                num = 1
                msg_body = f"{num} {sender_username} {message}"

                # Make the forward message packet
                forward_msg = util.make_message("forward_message", 4, msg_body)
                packet = util.make_packet(msg_type="data", msg=forward_msg)

                # Send the forward message packet to the recipient
                self.sock.sendto(packet.encode(), recipient_addr)

            # If the recipient does not exist, send an error
            else:
                print(f"msg: {sender_username} to non-existent user {recipient}")

    def handle_disconnect(self, addr):
        """
        Handle a disconnect request from a client.
        """
        # Extract sender username by the client's address
        username_to_remove = None
        for username, address in self.clients.items():
            if address == addr:
                username_to_remove = username
                break

        # If the client is recognized, proceed with the disconnection
        if username_to_remove:
            # Remove the client from the active clients list
            del self.clients[username_to_remove]
            # Print disconnection
            print(f"disconnected: {username_to_remove}")
        
        # If the client is not recognized, send an error
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
