#!/usr/bin/env python3
import sys
from socket import socket, AF_INET, SOCK_STREAM
from typing import Optional

from chat_protocol import SubmitMessage, Packet, UserWroteMessage, UserStatusWasUpdated, UserStatus
from client import Client


def handle_packet(packet: Packet):
  if isinstance(packet, UserWroteMessage):
    p: UserWroteMessage = packet
    print(f"{p.user_name}: {p.message}")
  elif isinstance(packet, UserStatusWasUpdated):
    p: UserStatusWasUpdated = packet
    if p.status == UserStatus.LOGGED_IN:
      print(f"NEW USER CONNECTED: {p.user_name}")
    elif p.status == UserStatus.LOGGED_OUT:
      print(f"USER {p.user_name} DISCONNECTED")


def run_client(server_port: int, user_name: Optional[str]):
  with socket(AF_INET, SOCK_STREAM) as sock:
    print(f"Connecting to server (remote_port: {server_port})...")
    sock.connect(("localhost", server_port))
    with Client(sock, user_name, handle_packet) as client:
      print("WELCOME! TYPE AND CLICK RETURN TO SEND MESSAGES.")
      while True:
        message = input("")
        chat_message = SubmitMessage(message)
        client.send_packets([chat_message])


def main():
  args = sys.argv[1:]
  if args:
    user_name = args[0]
  else:
    user_name = None
  run_client(5100, user_name)


if __name__ == '__main__':
  main()
