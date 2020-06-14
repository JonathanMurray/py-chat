#!/usr/bin/env python3
import threading
from dataclasses import dataclass
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SHUT_RDWR
from typing import Dict, Optional

import chat_protocol
from chat_protocol import SubmitMessage, UserWroteMessage, Packet, UserStatusWasUpdated, \
  UserStatus, Login, LoginResponse
from framed_protocol import PacketSender, PacketReceiver

GENERIC_NAMES = ["Alice", "Bob", "Charlie"]


@dataclass
class ClientHandle:
  logged_in: bool
  name: Optional[str]
  sender: PacketSender


class ClientHandles:
  def __init__(self):
    self._lock = threading.Lock()
    self._clients_by_id: Dict[int, ClientHandle] = {}
    self._next_client_id = 1

  def add_client(self, sender: PacketSender) -> int:
    with self._lock:
      client_id = self._next_client_id
      self._next_client_id += 1
      self._clients_by_id[client_id] = ClientHandle(False, None, sender)
      return client_id

  def broadcast_to_logged_in(self, packet: Packet):
    with self._lock:
      for sender in (handle.sender for handle in self._clients_by_id.values() if handle.logged_in):
        sender.send_packet(packet)

  def send_to_client(self, client_id, packet: Packet):
    with self._lock:
      self._clients_by_id[client_id].sender.send_packet(packet)

  def try_claim_name_for_client(self, client_id: int, user_name: Optional[str]) -> Optional[str]:
    with self._lock:
      if user_name:
        if self._is_name_free(user_name):
          self._clients_by_id[client_id].name = user_name
          return user_name
      else:
        # No user name requested. Try to assign a generic one.
        for generic_name in GENERIC_NAMES:
          if self._is_name_free(generic_name):
            self._clients_by_id[client_id].name = generic_name
            return generic_name

  def _is_name_free(self, user_name: str):
    for c in self._clients_by_id.values():
      if c.name == user_name:
        return False
    return True

  def mark_client_as_logged_in(self, client_id: int):
    with self._lock:
      self._clients_by_id[client_id].logged_in = True

  def is_client_logged_in(self, client_id: int):
    with self._lock:
      return self._clients_by_id[client_id].logged_in

  def remove_client(self, client_id: int):
    with self._lock:
      del self._clients_by_id[client_id]


class Server:

  def __init__(self, port: int):
    self._port = port
    self._clients = ClientHandles()

  def run(self):
    self._accept_new_clients(self._port)

  def _accept_new_clients(self, port):
    with socket(AF_INET, SOCK_STREAM) as server_socket:
      server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      print(f"Binding to port {port} ...")
      server_socket.bind(("localhost", port))
      server_socket.listen()
      while True:
        print("Waiting for client to connect...")
        client_socket, addr = server_socket.accept()
        print(f"New client connected: {addr}")
        client_id = self._clients.add_client(PacketSender(client_socket))
        print(f"Client was assigned id {client_id}")

        client_thread = threading.Thread(target=self._communicate_with_client, args=(client_id, client_socket,))
        client_thread.start()

  def _communicate_with_client(self, client_id: int, client_socket):
    receiver = PacketReceiver(client_socket, chat_protocol.parse_packet)
    try:
      should_continue = True
      while should_continue:
        print(f"[{client_id}] Waiting for message from client...")
        packet = receiver.wait_for_packet()
        if not packet:
          print(f"[{client_id}] Received end-of-stream from client.")
          self._disconnect_client(client_id, client_socket)
          break
        print(f"[{client_id}] Received packet from client: {packet}")
        should_continue = not self._handle_packet_from_client(client_id, client_socket, packet)
    except ConnectionResetError as e:
      print(f"[{client_id}] Connection reset: {e}")
      self._disconnect_client(client_id, client_socket)

  def _handle_packet_from_client(self, client_id: int, client_socket, packet: Packet):
    if isinstance(packet, SubmitMessage):
      if not self._clients.is_client_logged_in(client_id):
        print(f"[{client_id}] Client tries to send message before logging in! Will disconnect client.")
        self._disconnect_client(client_id, client_socket)
        return True
      print(f"[{client_id}] Broadcasting response to clients...")
      self._clients.broadcast_to_logged_in(UserWroteMessage(client_id, packet.message))
      print(f"[{client_id}] Broadcast complete.")
    elif isinstance(packet, Login):
      claimed_name = self._clients.try_claim_name_for_client(client_id, packet.user_name)
      if claimed_name:
        self._clients.send_to_client(client_id, LoginResponse(True, claimed_name))
        self._clients.broadcast_to_logged_in(UserStatusWasUpdated(client_id, UserStatus.LOGGED_IN))
        self._clients.mark_client_as_logged_in(client_id)
      else:
        self._clients.send_to_client(client_id, LoginResponse(False, "Name taken."))

  def _disconnect_client(self, client_id: int, client_socket):
    try:
      client_socket.shutdown(SHUT_RDWR)
    except OSError:
      print(
          f"[{client_id}] Couldn't shutdown client socket (because it was already shutdown from client's side likely)")
    client_socket.close()
    was_logged_in = self._clients.is_client_logged_in(client_id)
    self._clients.remove_client(client_id)
    print(f"[{client_id}] Disconnected client {client_id}")
    if was_logged_in:
      self._clients.broadcast_to_logged_in(UserStatusWasUpdated(client_id, UserStatus.LOGGED_OUT))


if __name__ == '__main__':
  server = Server(5100)
  server.run()
