#!/usr/bin/env python3
from socket import socket, AF_INET, SOCK_STREAM

from client import Client
from protocol import Ping, SubmitMessage, Packet, UserWroteMessage, UserStatusWasUpdated, UserStatus


def handle_packet(packet: Packet):
  if isinstance(packet, UserWroteMessage):
    p: UserWroteMessage = packet
    print(f"{p.user_id}: {p.message.decode('utf8')}")
  elif isinstance(packet, UserStatusWasUpdated):
    p: UserStatusWasUpdated = packet
    if p.status == UserStatus.CONNECTED:
      print(f"NEW USER CONNECTED: {p.user_id}")
    elif p.status == UserStatus.DISCONNECTED:
      print(f"USER {p.user_id} DISCONNECTED")


def run_client(server_port: int):
  with socket(AF_INET, SOCK_STREAM) as sock:
    print(f"Connecting to server (remote_port: {server_port})...")
    sock.connect(("localhost", server_port))
    with Client(sock, handle_packet) as client:
      print("WELCOME! TYPE AND CLICK RETURN TO SEND MESSAGES.")
      while True:
        message = input("")
        chat_message = SubmitMessage(bytearray(message, "utf8"))
        client.send_packets([Ping(), chat_message, Ping()])


if __name__ == '__main__':
  run_client(5100)
