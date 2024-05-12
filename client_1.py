'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util


'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''

class Client:
    '''
    This is the main Client Class. 
    '''
    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.running = True

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message. 
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''

        # Initial join message
        msg = util.make_message("join", 1, self.name)
        join_msg = util.make_packet(msg_type="data", msg=msg)
        self.sock.sendto(join_msg.encode(), (self.server_addr, self.server_port))

        # Main loop to handle user inputs
        while True:
            cmd = input()
            if cmd == "quit":
                self.quit()
            elif cmd.startswith("msg"):
                self.send_message(cmd)
            elif cmd == "list":
                self.request_list()
            else:
                print("incorrect userinput format")
                # self.unknown_command()


    def send_message(self, cmd):
        """
        Handle sending a message to other clients through the server.
        """
        parts = cmd.split(' ', 3)

        if len(parts) < 4:
            print("incorrect userinput format")
            return

        try:
            num_recipients = int(parts[1])
            recipient_names = parts[2].split(' ')[:num_recipients]
            message = parts[3]
        except ValueError:
            print("incorrect userinput format")
            return

        # Make send_message packet
        msg_body = f"{num_recipients} {' '.join(recipient_names)} {message}"
        msg = util.make_message("send_message", 4, msg_body)
        packet = util.make_packet(msg_type="data", msg=msg)

        # Send send_message packet to the server
        self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))


    def request_list(self):
        """
        Handle sending request to retrieve all online users from the server.
        """
        # Make request_users_list packet
        msg = util.make_message("request_users_list", 3, "")
        packet = util.make_packet(msg_type="data", msg=msg)

        # Send request_users_list packet to the server
        self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))


    def quit(self):
        """
        Handle quitting the client from the server.
        """
        try:
            # Make disconnect packet
            msg = util.make_message("disconnect", 1, self.name)
            packet = util.make_packet(msg_type="data", msg=msg)

            # Send disconnect packet to the server
            self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
        finally:
            # Signal the receive_handler to stop and then close the currnet socket
            self.running = False
            self.sock.close()
            print("quitting")
            sys.exit(0)

    
    def unknown_command(self):
        """
        Handle an unknown command input by the user.
        """
        # Make unknown_command packet
        msg = util.make_message("unknown_command", 2, "")
        packet = util.make_packet(msg_type="data", msg=msg)

        # Send unknown_command packet to the server
        self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))


    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        
        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)

                if data:
                    # Process response from server
                    message = data.decode()
                    message = message.split('|')
                    new_message = message[2].split(' ')

                    # Handle nomral responses from server
                    if new_message[0] == "response_users_list":
                        user_list = ' '.join(new_message[3:])
                        print("list: " + user_list)

                    elif new_message[0] == "forward_message":
                        msg = ' '.join(new_message[4:])
                        print("msg: " + new_message[3] + ": " + msg)
                    
                    # Handle error messages
                    elif new_message[0] == "ERR_USERNAME_UNAVAILABLE":
                        print("disconnected: username not available")
                        self.running = False
                        self.sock.close()
                        sys.exit(0)
                    
                    elif new_message[0] == "ERR_SERVER_FULL":
                        print("disconnected: server full")
                        self.running = False
                        self.sock.close()
                        sys.exit(0)
                    
                    elif new_message[0] == "ERR_UNKNOWN_MESSAGE":
                        print("disconnected: server received an unknown command")
                        self.running = False
                        self.sock.close()
                        sys.exit(0)
 
            except socket.error as e:
                if self.running:
                    print(f"socket error: {e}")
                break


# Do not change below part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
