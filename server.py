# Python version : 3.7.4
# -*- coding: utf-8 -*-
import socket
import threading
import logging
import json
from sys import argv, exit
from os import _exit, path

def main():
    logging.basicConfig(filename = 'log.log', format='%(asctime)s %(message)s', datefmt = '%m/%d/%Y %I:%M:%S %p')
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Initializing server socket with option REUSEADDR On
    except socket.error:
        print("Error in creating socket")
        exit(0)
    if len(argv) !=2:
        print("Invalid Command; Command Format: server.py [port]")
        return
    
    IP_Address = "127.0.0.1"
    try:
        Port = int(argv[1])
    except ValueError:
        print("The Port is invalid ; The Port is supposed to be an integer of base 10")
        exit(0)

    server.bind((IP_Address,Port))
    server.listen(100)
    # The Server can listen to upto 100 connections
    print("Now listening at socket: {}".format(server.getsockname()))
    logging.warning("The server has started accepting connections at {}".format(server.getsockname()))

    if path.exists("database.json"):
        # Reading from the json database
        with open("database.json", "r") as db:
            try:
                user_data = json.load(db)
            except Exception:
                user_data = {"the_host" : {"is_connected" : True, "connection_details" : [], "bio" : "I am the Host"}}
    else:
        # Initializing the json database
        user_data = {"the_host" : {"is_connected" : True, "connection_details" : [], "bio" : "I am the Host"}}

    for user in user_data.keys():
        # Searching for the Host's username and storing it in host_name
        if user_data[user]["is_connected"] == True:
            host_name = user
            break
    try:
        command_thread = threading.Thread(target = server_commands, args = (user_data, server, host_name), daemon = True)
    except UnboundLocalError:
        host_name = list(user_data.keys())[0]
        user_data[host_name]["is_connected"] = True
        command_thread = threading.Thread(target = server_commands, args = (user_data, server, host_name), daemon = True)
    command_thread.start()
    # Inputs Commands and messages from the server(messages will be sent from username = host_name)
    new_conn_thread = threading.Thread(target = new_connections, args = (user_data, server,))
    new_conn_thread.start()
    new_conn_thread.join()
    # Searching for new connections
    return

def new_connections(user_data, server):
    help_string = help(0)
    while True:
        try:
            connection, address = server.accept()
        except OSError:
            break
        except EOFError:
            break

        new_user = connection.recv(2048).decode("ascii")
        # Accepts a username provided by the host
        
        if new_user not in user_data.keys():
            # Storing the new users info
            user_data[new_user] = {"is_connected" : True, "connection_details" : [connection, address], "bio" : "Hi, I am new to the chatroom!"}
            connection.sendall("Welcome to the server, {}\nType /help to view available commands".format(new_user).encode("ascii"))
        elif user_data[new_user]["is_connected"] == False:
            # For an existing user logging back in
            user_data[new_user]["is_connected"] = True
            user_data[new_user]["connection_details"] = [connection,address]
            connection.sendall("Welcome back to the server, {}\nType /help to view available commands".format(new_user).encode("ascii"))
        else:
            # Username taken
            connection.sendall("user taken".encode("ascii"))
            connection.close()
            continue

        logging.warning("{} has joined the server".format(new_user))
        broadcast(user_data,"{} has joined the server".format(new_user),new_user)
        print("{} has joined the server".format(new_user))

        message_thread = threading.Thread(target = message_handler, args = (user_data, connection, new_user, help_string), daemon = True)
        message_thread.start()
        # message_thread.join()
        # Starting a thread to send and receive messages and commands from this new connection

def message_handler(user_data, connection, user, help_string):
    while True:
        try:
            message = connection.recv(2048).decode("ascii")
            if len(message) == 0:
                continue
            if message[0] == '/':
                # If the first character of the message is '/', the server assumes the user is trying to execute a command
                command, message = split_command_and_message(message, "")
                if command == "exit" or command == "quit":
                    # user exits the chatroom, connection is closed, along with thread
                    broadcast(user_data, "{} has left the server".format(user), user)
                    logging.warning("{} has left the server".format(user))
                    print("{} has left the server".format(user))
                    user_data[user]["is_connected"] = False
                    user_data[user]["connection_details"] = []
                    connection.sendall("exit".encode("ascii"))
                    connection.close()
                    break
                elif command == "users":
                    # displays list of all users
                    connection.sendall(gen_user_list(user_data, 1, "Online: ", "Offline: ").encode("ascii"))
                elif command == "users_online":
                    # displays list of all users online
                    connection.sendall(gen_user_list(user_data, 0, "Online: ", "").encode("ascii"))
                elif command == "users_offline":
                    # displays list of all users offline
                    connection.sendall(gen_user_list(user_data, 2, "", "Offline: ").encode("ascii"))
                elif command == "change_name":
                    # Command to change username
                    if message[1:] == command:
                        connection.sendall("Incorrect command, the command is /change_name [new username] \n"\
                                           "You have not mentioned a new username".encode("ascii"))
                        continue

                    for i in range(len(message)):
                        # If the name given has spaces, only the first word is taken
                        if message[i] == " ":
                            message = message[0:(i-1)]
                            break
                    
                    if message in user_data.keys():
                        # Username is taken
                        connection.sendall("The username, {} is taken, please choose a different name".format(message).encode("ascii"))
                    else:
                        user_data[message] = user_data.pop(user)
                        broadcast(user_data,"{} has changed their name to {}".format(user,message),"")
                        logging.warning("{} has changed their name to {}".format(user, message))
                        print("{} has changed their name to {}".format(user, message))
                        connection.sendall("Succesfully changed name to {}".format(message).encode("ascii"))
                        user = message
                elif command == "whisper" or command == "msg":
                    # whispering to a single user
                    if message[1:] == command:
                        connection.sendall("Incorrect command, the command is /whisper [receiver] [message]\n"\
                                           "You have neither mentioned the receiver nor the message".encode("ascii"))
                        continue

                    receiver = ""
                    for i in range(len(message)):
                        # split receiver and message body
                        if message[i] == " ":
                            receiver = message[0:i]
                            message = message[i:]
                            break
                    
                    if receiver == "":
                        connection.sendall("Incorrect command, the command is /whisper [receiver] [message]\n"\
                                           "You have not written a message for the reciver".encode("ascii"))
                    elif receiver not in user_data.keys():
                        connection.sendall("The user mentioned does not exist".encode("ascii"))
                    elif user_data[receiver]["is_connected"] == False:
                        connection.sendall("The user, {} is not online at the moment".format(receiver).encode("ascii"))
                    else:
                        try:
                            user_data[receiver]["connection_details"][0].sendall("{} whispers to you: {}".format(user, message).encode("ascii"))
                        except IndexError:
                            print("{} whispers to you: {}".format(user, message))
                        connection.sendall("You whispered to {}: {}".format(receiver, message).encode("ascii"))
                elif command  == "bio_write":
                    if message[1:] == command:
                        connection.sendall("Incorrect command, the command is /bio_write [bio]\n"\
                                           "You have not written a bio".encode("ascii"))
                    else:
                        user_data[user]["bio"] = message
                        connection.sendall("You have successfully changed your bio".encode("ascii"))
                elif command == "bio_append":
                    if message[1:] == command:
                        connection.sendall("You haven't added anything".encode("ascii"))
                    else:
                        user_data[user]["bio"] += message
                        connection.sendall("You have successfully changed your bio".encode("ascii"))
                elif command == "bio":
                    if message[1:] == command:
                        connection.sendall("{}'s bio: {}".format(user, user_data[user]["bio"]).encode("ascii"))
                        continue

                    for i in range(len(message)):
                        # split receiver and message body
                        if message[i] == " ":
                            name = message[0:i]
                            message = message[i:]
                            break
                        if i == len(message)-1:
                            name = message
                    
                    if name not in user_data.keys():
                        connection.sendall("The user, {} doesn't exist".format(name).encode("ascii"))
                    else:
                        connection.sendall("{}'s bio: {}".format(name, user_data[name]["bio"]).encode("ascii"))

                elif command == "help":
                    # Shows list of commands
                    connection.sendall(help_string.encode("ascii"))
                else:
                    # For invalid commands
                    connection.sendall("Unknown Command\nType /help to see the list of available commands".encode("ascii"))
                continue

            message = "<{}{}".format(user,message)
            logging.warning(message)
            print(message)
            broadcast(user_data,message, user)
            # Broadcasting message to other users
        except ConnectionAbortedError:
            logging.warning("Connection from {} aborted successfully".format(user))
            print("Connection from {} aborted successfully".format(user))
            break
        except ConnectionResetError:
            connection.close()
            user_data[user]["is_connected"] = False
            logging.warning("The user {} forcibly disconnected by closing the terminal".format(user))
            print("The user {} forcibly disconnected by closing the terminal".format(user))
            broadcast(user_data, "{} has left the server".format(user), "")
            break
        except IndexError:
            connection.close()
            user_data[user]["is_connected"] = False
            logging.warning("The user {} forcibly disconnected either using a keyboard Interrupt or EOF".format(user))
            print("The user {} forcibly disconnected either using a keyboard Interrupt or EOF".format(user))
            broadcast(user_data, "{} has left the server".format(user), "")
            break

def server_commands(user_data, server, host_name):
    help_string = help(1)
    while True:
        try:
            message = input("")
            if len(message) == 0:
                continue
        except EOFError:
            print("EOF/Keyboard Interrupt detected")
            handle_exit(server, user_data)
        except KeyboardInterrupt:
            print("Keyboard Interrupt detected")
            handle_exit(server, user_data)
        if message[0] == "/":
            # / character at the beginning of the message signifies a command
            command, message = split_command_and_message(message, "")
            if command == "exit" or command == "quit":
                handle_exit(server, user_data)
            elif command == "users":
                # displays list of all users
                print(gen_user_list(user_data, 1, "Online: ", "Offline: "))
            elif command == "users_online":
                # displays list of all users online
                print(gen_user_list(user_data, 0, "Online: ", ""))
            elif command == "users_offline":
                # displays list of all users offline
                print(gen_user_list(user_data, 2, "", "Offline: "))
            elif command == "change_name":
                # command to change host name
                if message[1:] == command:
                        print("Incorrect command, the command is /change_name [new username] \n"\
                                           "You have not mentioned a new username")
                        continue

                for i in range(len(message)):
                    # If the name given has spaces, only the first word is taken
                    if message[i] == " ":
                        message = message[0:(i-1)]
                        break
                    
                if message in user_data.keys():
                    print("The username, {} is taken, please choose a different name".format(message))
                else:
                    user_data[message] = user_data.pop(host_name)
                    broadcast(user_data,"The Host,{} has changed their name to {}".format(host_name, message),"")
                    logging.warning("The Host,{} has changed their name to {}".format(host_name, message))
                    print("Succesfully changed name to {}".format(message))
                    host_name = message
            elif command == "whisper" or command == "msg":
                # Whisper to 1 user privately
                if message[1:] == command:
                    print("Incorrect command, the command is /whisper [receiver] [message]\n"\
                                           "You have neither mentioned the receiver nor the message")
                    continue

                receiver = ""
                for i in range(len(message)):
                    # split receiver and message body
                    if message[i] == " ":
                        receiver = message[0:i]
                        message = message[i:]
                        break
                    
                if receiver == "":
                    print("Incorrect command, the command is /whisper [receiver] [message]\n"\
                                           "You have not written a message for the reciver")
                elif receiver not in user_data.keys():
                    print("The user mentioned does not exist")
                elif user_data[receiver]["is_connected"] == False:
                    print("The user, {} is not online at the moment".format(receiver))
                else:
                    user_data[receiver]["connection_details"][0].sendall("{}(HOST) whispers to you: {}".format(host_name, message).encode("ascii"))
                    print("You whispered to {}: {}".format(receiver, message).encode("ascii"))
            elif command  == "bio_write":
                if message[1:] == command:
                    print("Incorrect command, the command is /bio_write [bio]\n"\
                                        "You have not written a bio")
                else:
                    user_data[host_name]["bio"] = message
                    print("You have successfully changed your bio")
            elif command == "bio_append":
                if message[1:] == command:
                    print("You haven't added anything")
                else:
                    user_data[host_name]["bio"] += message
                    print("You have successfully changed your bio")
            elif command == "bio":
                if message[1:] == command:
                    print("{}'s bio: {}".format(host_name, user_data[host_name]["bio"]))
                    continue

                for i in range(len(message)):
                    # split receiver and message body
                    if message[i] == " ":
                        name = message[0:i]
                        message = message[i:]
                        break
                    if i == len(message)-1:
                        name = message
                
                if name not in user_data.keys():
                    print(message)
                    print("The user, {} doesn't exist".format(name))
                else:
                    print("{}'s bio: {}".format(name, user_data[name]["bio"]))
            elif command == "kick":
                if message[1:] == command:
                    print("Incorrect command, the command is /kick [username]\n"\
                                           "You have not written a username to kick")
                    continue

                for i in range(len(message)):
                    # split receiver and message body
                    if message[i] == " ":
                        name = message[0:i]
                        message = message[i:]
                        break
                    if i == len(message)-1:
                        name = message
                
                if name not in user_data.keys():
                    print(message)
                    print("The user, {} doesn't exist".format(name))
                else:
                    broadcast(user_data, "{} was kicked from the server".format(name), name)
                    logging.warning("{} has was kicked from the server".format(name))
                    print("{} has was kicked from the server".format(name))
                    connection = user_data[name]["connection_details"][0]
                    user_data[name]["is_connected"] = False
                    user_data[name]["connection_details"] = []
                    connection.sendall("kick".encode("ascii"))
                    connection.close()



            elif command == "help":
                print(help_string)
            else:
                print("Unknown Command\nType /help to see the list of available commands")
        else:
            message = "<{}>(HOST) {}".format(host_name,message)
            logging.warning(message)
            print(message)
            broadcast(user_data, message, host_name)

def handle_exit(server, user_data):
    # Handles server closure and unexpected crashes
    logging.warning("Closing connection")
    print("Closing connection")
    for user in user_data:
        # server data is saved to database.json and all connections are closed
        if len(user_data[user]["connection_details"]) == 2:
            user_data[user]["is_connected"] = False
            connection = user_data[user]["connection_details"][0]
            connection.close()
            user_data[user]["connection_details"] = []
    with open("database.json", "w") as db:
        json.dump(user_data, db, indent = 4)

    server.close()
    print("Server Closed Succesfully")
    logging.warning("Server Closed Succesfully\n\n\n")
    # _exit is used as there are multiple threads running
    _exit(0)

def broadcast(user_data, message, source):
    # broadcasts messages to all users who aren't the host or the source
    for user in user_data.keys():
        try:
            if user != source and user_data[user]["is_connected"]  == True:
                connection = user_data[user]["connection_details"][0]
                connection.sendall(message.encode("ascii"))
        except IndexError:
            continue

def split_command_and_message(message, command):
    # Used in command handling, does what the name says
    if " " in message:
        command, message = message.split(" ", 1)
        command = command[1:len(command)]
    else:
        command = message[1:]
    
    return command, message

def gen_user_list(user_data, option, online, offline):
    # used in generating lists of online, offline users
    for user in user_data.keys():
        if user_data[user]["is_connected"] == True and option < 2:
            # option is 'online' or 'both'
            online += "<{}>, ".format(user)
        
        if user_data[user]["is_connected"] == False and option > 0:
            # option is offline or 'both'
            offline += "<{}>, ".format(user)
    
    if len(online) == 8 and option < 2:
        online += "No users currently online  "
    if len(offline) == 9 and option > 0:
        offline += "No users currently offline  "

    if option == 0:
        return "{}\n".format(online[:len(online)-2])
    elif option == 1:
        return "{}\n\n{}\n".format(online[:len(online)-2], offline[:len(offline)-2])
    else:
        return "{}\n".format(offline[:len(offline)-2])

def help(opt):
    # generates help_string listing info about the available commands, opt 0 is for client, opt!=0 is for server
    help_string = "\nMessages prefixed with '/' are commands, here are the available commands: \n\n"
    if opt == 0:
        help_string += "/quit or /exit: Leave the chatroom\n"
    else:
        help_string += "/quit or /exit: Closes all connections and shuts down the server\n"
    help_string += \
        "Format: /quit or /exit \n\n"\
        "/users: shows all users, online and offline\n"\
        "Format: /users\n\n"\
        "/users_online: shows all users online\n"\
        "Format: /users_online\n\n"\
        "/users_offline: shows all users offline\n"\
        "Format: /users_offline\n\n"\
        "/change_name: For changing your username\n"\
        "Format: /change_name [new username]\n\n"\
        "/whisper or /msg: To whisper to another user\n"\
        "Format: /whisper [username] [message] or /msg [username] [message]\n\n"\
        "/bio_write: Write a bio for yourself\n"\
        "Format: /bio_write [bio]\n\n"\
        "/bio_append: Append a line to your bio\n"\
        "Format: /bio_append [Line]\n\n"\
        "/bio: View a user's bio, to view your own, don't pass any arguments\n"\
        "Format: /bio or /bio [username]\n"
    if opt !=0:
        help_string +=\
            "\n/kick: kick a user from the server\n"\
            "Format: /kick [username]\n"
                       
    return help_string

if __name__ == '__main__':
    main()