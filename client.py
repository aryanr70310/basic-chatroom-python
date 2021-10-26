# Python version : 3.7.4
# -*- coding: utf-8 -*-
import socket
import threading
from sys import argv, exit
from os import _exit

def main():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Initializing client socket
    except socket.error:
        print("Error in creating socket")
        exit(0)
    if len(argv) != 4:
        print("Invalid Command; Command Format: client.py [username] [hostname] [port]")
    
    IP_Address,Port = str(argv[len(argv)-2]), 0
    try:
        Port = int(argv[len(argv)-1])
    except ValueError:
        print("The Port is invalid ; The Port is supposed to be an integer of base 10")
        exit(0)

    username = str(argv[1]) 
    # setting username

    while True:
        # Attempts to connect to server with username
        try:
            client.settimeout(10.0)      
            client.connect((IP_Address,Port))
        except socket.gaierror:
            print("The hostname is invalid")
            exit(0)
        except ConnectionRefusedError:
            print("The address you have tried to connect to, {}, is either,\n" \
            "not accepting connections or simply doesn't exist".format((IP_Address + ":" + str(Port))))
            exit(0)
        except socket.timeout:
            print("Failed to connect, socket timed out, you may have input a false hostname")
            exit(0)

        client.sendall(username.encode("ascii"))
        message = client.recv(2048).decode("ascii")
        if message != "user taken":
            # User will be given an opportunity to enter a different name if their first choice is taken
            print(message)
            break
        else:
            username = input("User name, {} was taken, please choose another username : ".format(username))
            client.close()
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    client.settimeout(10000.0)
    receive_thread = threading.Thread(target = client_receive, args = (client,), daemon = True)
    receive_thread.start()
    # Thread to receive messages from the serverS
    send_thread = threading.Thread(target = client_send, args = (client,username,), daemon = True)
    send_thread.start()
    send_thread.join()
    # Thread to send messages and commands to the server
    return

def client_send(client, username):
    # Thread to send messages
    while True:
        try:
            message = input()
        except EOFError:
            client.sendall("/exit".encode("ascii"))
            print("Disconnected due to Keyboard Interrupt")
            client.close()
            _exit(0)
        except IndexError:
            print("invalid message")
            continue
        if message[0] != '/':
            # For a message
            client.sendall("> {}".format(message).encode("ascii"))
            print("<You> {}".format(message))
        else:
            # For a command
            client.sendall(message.encode("ascii"))


def client_receive(client):
    while True:
        try:
            message = client.recv(2048).decode("ascii")
            if message == "exit" or message == "kick":
                # If the user uses the /exit or /quit command
                client.close()
                if message == "kick":
                    print("You were kicked from the server")
                print("Connection Terminated Succesfully")
                _exit(0)
            print(message)
        except ConnectionResetError:
            print("Connection Lost due to server closure")
            client.close()
            _exit(0)
        except socket.timeout:
            print("Connection timed out due to server inactivity")

if __name__ == '__main__':
    main()