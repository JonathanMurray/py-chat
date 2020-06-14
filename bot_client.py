#!/usr/bin/env python3
import random
from socket import socket, AF_INET, SOCK_STREAM
from time import sleep

from chat_protocol import SubmitMessage
from client import Client


def run_bot(server_port: int):
  messages = ["Apple", "Banana", "Pineapple"]
  with socket(AF_INET, SOCK_STREAM) as sock:
    print(f"Connecting to server (remote_port: {server_port})...")
    sock.connect(("localhost", server_port))
    with Client(sock, "BOT", lambda p: print(f"Received message: {p}")) as client:
      while client.connected:
        message = random.choice(messages)
        print(f"Sending message: {message}")
        chat_message = SubmitMessage(message)
        client.send_packets([chat_message])
        sleep(random.randint(5, 10))
      print("Exiting.")


if __name__ == '__main__':
  run_bot(5100)
