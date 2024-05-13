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

MAX_CHUNK_SIZE = 1400
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
        self.sock.settimeout(0.5)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.running = True
        self.seq_num = 0
        self.ack_received = True
        self.last_packet = None

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message. 
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''

        try: 
            self.join_server()
            
            while self.running:
                try:
                    message = input()
                    if message.startswith("quit"):
                        self.quit()
                        break
                    elif message.startswith("msg"):
                        self.send_message(message)
                    elif message.startswith("list"):
                        self.request_user_list()
                    else:
                        print("incorrect userinput format")
                        # self.unknown_command()
                except socket.timeout:
                    self.handle_timeout()
        finally:
            self.sock.close()

    def join_server(self):
        """
        Handle joining the server and sending a JOIN message.
        """
        # Send START packet
        self.send_start_packet()

        # Send JOIN packet
        self.ack_received = False
        join_msg = util.make_message("join", 1, self.name)
        join_packet = util.make_packet("data", self.seq_num, join_msg)
        self.sock.sendto(join_packet.encode(), (self.server_addr, self.server_port))
        self.seq_num += 1
        self.last_packet = join_packet.encode()

        max_retry = 10

        # Wait for ACK
        while not self.ack_received:
            try:
                if max_retry == 0:
                    # quit the client
                    self.quit()
                    break
                data, _ = self.sock.recvfrom(1024)
                msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                
                # Calculate checksum for received data
                calculated_checksum = util.calculate_checksum(data)
                
                # If calculated checksum matches received checksum, send ACK
                if calculated_checksum == checksum:
                    if msg_type == "ack":
                        self.ack_received = True
                        
                        # Send cumulative ACK with seq_num it expects to receive next
                        ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                        self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                else:
                    # If checksums do not match, drop the packet
                    break
            except socket.timeout:
                self.seq_num += 1
                self.sock.sendto(join_packet.encode(), (self.server_addr, self.server_port))
                self.last_packet = join_packet.encode()

                max_retry -= 1

        # Send END packet
        self.send_end_packet()


    def send_start_packet(self):
        """
        Send a START packet to the server to establish new communication.
        """
        max_retry = 10

        self.ack_received = False
        start_packet = util.make_packet("start", 0, "")
        self.sock.sendto(start_packet.encode(), (self.server_addr, self.server_port))
        self.seq_num += 1
        self.last_packet = start_packet.encode()

        # Wait for ACK
        while not self.ack_received:
            try:
                if max_retry == 0:
                    # quit the client
                    self.quit()
                    break
                data, _ = self.sock.recvfrom(1024)
                msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                
                # Calculate checksum for received data
                calculated_checksum = util.calculate_checksum(data)
                
                # If calculated checksum matches received checksum, send ACK
                if calculated_checksum == checksum:
                    if msg_type == "ack":
                        self.ack_received = True
                        
                        # Send cumulative ACK with seq_num it expects to receive next
                        ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                        self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                else:
                    # If checksums do not match, drop the packet
                    break
            except socket.timeout:
                self.seq_num += 1
                self.sock.sendto(start_packet.encode(), (self.server_addr, self.server_port))
                self.last_packet = start_packet.encode()

                max_retry -= 1

    def send_end_packet(self):
        """
        Send an END packet to the server to end communication.
        """
        max_retry = 10

        self.ack_received = False
        end_packet = util.make_packet("end", self.seq_num)
        self.sock.sendto(end_packet.encode(), (self.server_addr, self.server_port))
        self.seq_num += 1
        self.last_packet = end_packet.encode()

        # Wait for ACK
        while not self.ack_received:
            try:
                if max_retry == 0:
                    # quit the client
                    self.quit()
                    break
                data, _ = self.sock.recvfrom(1024)
                msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                
                # Calculate checksum for received data
                calculated_checksum = util.calculate_checksum(data)
                
                # If calculated checksum matches received checksum, send ACK
                if calculated_checksum == checksum:
                    if msg_type == "ack":
                        self.ack_received = True
                        
                        # Send cumulative ACK with seq_num it expects to receive next
                        ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                        self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                else:
                    # If checksums do not match, drop the packet
                    break
            except socket.timeout:
                self.seq_num += 1
                self.sock.sendto(end_packet.encode(), (self.server_addr, self.server_port))
                self.last_packet = end_packet.encode()

                max_retry -= 1

    def send_message(self, cmd):
        """
        Handle sending a message to other clients through the server.
        """
        # Send START packet
        self.send_start_packet()

        # Send message to recipients
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

        # Divide into chunks of 1400 bytes
        chunks = [message[i:i+MAX_CHUNK_SIZE] for i in range(0, len(message), MAX_CHUNK_SIZE)]
        
        for chunk in chunks:
            self.ack_received = False

            # Make send_message packet
            msg_body = f"{num_recipients} {' '.join(recipient_names)} {chunk}"
            msg = util.make_message("send_message", 4, msg_body)
            packet = util.make_packet(msg_type="data", seqno=self.seq_num, msg=msg)

            # Send send_message packet to the server
            self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
            self.seq_num += 1
            self.last_packet = packet.encode()

            max_retry = 10

            # Wait for ACK
            while not self.ack_received:
                try:
                    if max_retry == 0:
                        # quit the client
                        self.quit()
                        break
                    data, _ = self.sock.recvfrom(1024)
                    msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                    
                    # Calculate checksum for received data
                    calculated_checksum = util.calculate_checksum(data)
                    
                    # If calculated checksum matches received checksum, send ACK
                    if calculated_checksum == checksum:
                        if msg_type == "ack":
                            self.ack_received = True
                            
                            # Send cumulative ACK with seq_num it expects to receive next
                            ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                            self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                    else:
                        # If checksums do not match, drop the packet
                        break
                except socket.timeout:
                    self.seq_num += 1
                    self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
                    self.last_packet = packet.encode()

                    max_retry -= 1
        
        # Send END packet
        self.send_end_packet()
                    

    def request_user_list(self):
        """
        Handle sending request to retrieve all online users from the server.
        """
        # Send START packet
        self.send_start_packet()

        # Make request_users_list packet
        msg = util.make_message("request_users_list", 3, "")
        packet = util.make_packet(msg_type="data", seqno=self.seq_num, msg=msg)

        # Send request_users_list packet to the server
        self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
        self.seq_num += 1
        self.last_packet = packet.encode()

        max_retry = 10

        # Wait for ACK
        while not self.ack_received:
            try:
                if max_retry == 0:
                    # quit the client
                    self.quit()
                    break
                data, _ = self.sock.recvfrom(1024)
                msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                
                # Calculate checksum for received data
                calculated_checksum = util.calculate_checksum(data)
                
                # If calculated checksum matches received checksum, send ACK
                if calculated_checksum == checksum:
                    if msg_type == "ack":
                        self.ack_received = True
                        
                        # Send cumulative ACK with seq_num it expects to receive next
                        ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                        self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                else:
                    # If checksums do not match, drop the packet
                    break
            except socket.timeout:
                self.seq_num += 1
                self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
                self.last_packet = packet.encode()

                max_retry -= 1

        # Send END packet
        self.send_end_packet()


    def quit(self):
        """
        Handle quitting the client from the server.
        """
        # Send START packet
        self.send_start_packet()
    
        try:
            # Make disconnect packet
            msg = util.make_message("disconnect", 1, self.name)
            packet = util.make_packet(msg_type="data", msg=msg)

            # Send disconnect packet to the server
            self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
            self.seq_num += 1
            self.last_packet = packet.encode()

            max_retry = 10

            # Wait for ACK
            while not self.ack_received:
                try:
                    if max_retry == 0:
                        # quit the client
                        self.quit()
                        break
                    data, _ = self.sock.recvfrom(1024)
                    msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                    
                    # Calculate checksum for received data
                    calculated_checksum = util.calculate_checksum(data)
                    
                    # If calculated checksum matches received checksum, send ACK
                    if calculated_checksum == checksum:
                        if msg_type == "ack":
                            self.ack_received = True
                            
                            # Send cumulative ACK with seq_num it expects to receive next
                            ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                            self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                    else:
                        # If checksums do not match, drop the packet
                        break
                except socket.timeout:
                    self.seq_num += 1
                    self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
                    self.last_packet = packet.encode()

                    max_retry -= 1

            # Send END packet
            self.send_end_packet()

        finally:
            # Signal the receive_handler to stop and then close the currnet socket
            self.running = False
            # self.sock.close()
            print("quitting")
            sys.exit(0)

    
    def unknown_command(self):
        """
        Handle an unknown command input by the user.
        """
        # Send START packet
        self.send_start_packet()

        # Make unknown_command packet
        msg = util.make_message("unknown_command", 2, "")
        packet = util.make_packet(msg_type="data", msg=msg)

        # Send unknown_command packet to the server
        self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
        self.last_packet = packet.encode()

        max_retry = 10

        # Wait for ACK
        while not self.ack_received:
            try:
                if max_retry == 0:
                    # quit the client
                    self.quit()
                    break
                data, _ = self.sock.recvfrom(1024)
                msg_type, seqno, data, checksum = util.parse_packet(data.decode())
                
                # Calculate checksum for received data
                calculated_checksum = util.calculate_checksum(data)
                
                # If calculated checksum matches received checksum, send ACK
                if calculated_checksum == checksum:
                    if msg_type == "ack":
                        self.ack_received = True
                        
                        # Send cumulative ACK with seq_num it expects to receive next
                        ack_msg = util.make_packet(msg_type="ack", seqno=seqno+1)
                        self.sock.sendto(ack_msg.encode(), (self.server_addr, self.server_port))
                else:
                    # If checksums do not match, drop the packet
                    break
            except socket.timeout:
                self.seq_num += 1
                self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
                self.last_packet = packet.encode()

                max_retry -= 1

        # Send END packet
        self.send_end_packet()


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

                    if message[0] == "ack":
                        self.ack_received = True
                        
                    elif message[0] == "start":
                        # Send ACK packet
                        ack_packet = util.make_packet("ack", self.seq_num)
                        self.sock.sendto(ack_packet.encode(), (self.server_addr, self.server_port))
                        self.seq_num += 1

                    elif message[0] == "end":
                        # Send ACK packet
                        ack_packet = util.make_packet("ack", self.seq_num)
                        self.sock.sendto(ack_packet.encode(), (self.server_addr, self.server_port))
                        self.seq_num += 1
                    
                    elif message[0] == "data":
                        ack_packet = util.make_packet("ack", self.seq_num)
                        self.sock.sendto(ack_packet.encode(), (self.server_addr, self.server_port))
                        self.seq_num += 1
                        
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

    def handle_timeout(self):
        """
        Handle a timeout error when waiting for a response from the server.
        """
        if not self.ack_received:
            self.sock.sendto(self.last_packet, (self.server_addr, self.server_port))


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
