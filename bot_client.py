#!/usr/bin/env python3
import random
from socket import socket, AF_INET, SOCK_STREAM
from time import sleep

from client import Client
from protocol import Ping, SubmitMessage


def run_bot(server_port: int):
  messages = [b"Apple", b"Banana", b"Pineapple"]
  with socket(AF_INET, SOCK_STREAM) as sock:
    print(f"Connecting to server (remote_port: {server_port})...")
    sock.connect(("localhost", server_port))
    with Client(sock) as client:
      while client.connected:
        message = random.choice(messages)
        print(f"Sending message: {message}")
        chat_message = SubmitMessage(bytearray(message))
        client.send_packets([Ping(), chat_message, Ping()])
        sleep(random.randint(5, 10))
      print("Exiting.")


if __name__ == '__main__':
  run_bot(5100)
