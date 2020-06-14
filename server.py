#!/usr/bin/env python3
import threading
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SHUT_RDWR
from typing import Dict

from protocol import SubmitMessage, PacketSender, PacketReceiver, UserWroteMessage, Packet, UserStatusWasUpdated, \
  UserStatus


class ClientConnections:
  def __init__(self):
    self._lock = threading.Lock()
    self._senders_by_id: Dict[int, PacketSender] = {}
    self._next_client_id = 1

  def add_client(self, sender: PacketSender) -> int:
    with self._lock:
      client_id = self._next_client_id
      self._next_client_id += 1
      self._senders_by_id[client_id] = sender
      return client_id

  def broadcast(self, packet: Packet):
    with self._lock:
      for sender in self._senders_by_id.values():
        sender.send_packet(packet)

  def remove_client(self, client_id: int):
    with self._lock:
      del self._senders_by_id[client_id]


class Server:

  def __init__(self, port: int):
    self._port = port
    self._client_connections = ClientConnections()

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
        client_id = self._client_connections.add_client(PacketSender(client_socket))
        print(f"Client was assigned id {client_id}")
        self._client_connections.broadcast(UserStatusWasUpdated(client_id, UserStatus.CONNECTED))
        client_thread = threading.Thread(target=self._communicate_with_client, args=(client_id, client_socket,))
        client_thread.start()

  def _communicate_with_client(self, client_id: int, client_socket):
    receiver = PacketReceiver(client_socket)
    try:
      while True:
        print(f"[{client_id}] Waiting for message from client...")
        packet = receiver.wait_for_packet()
        if not packet:
          print(f"[{client_id}] Received end-of-stream from client.")
          self._disconnect_client(client_id, client_socket)
          break

        print(f"[{client_id}] Received packet from client: {packet}")
        if isinstance(packet, SubmitMessage):
          print(f"[{client_id}] Broadcasting response to clients...")
          self._client_connections.broadcast(UserWroteMessage(client_id, packet.payload))
          print(f"[{client_id}] Broadcast complete.")
    except ConnectionResetError as e:
      print(f"[{client_id}] Connection reset: {e}")
      self._disconnect_client(client_id, client_socket)

  def _disconnect_client(self, client_id: int, client_socket):
    try:
      client_socket.shutdown(SHUT_RDWR)
    except OSError:
      print(
          f"[{client_id}] Couldn't shutdown client socket (because it was already shutdown from client's side likely)")
    client_socket.close()
    self._client_connections.remove_client(client_id)
    print(f"[{client_id}] Disconnected client {client_id}")
    self._client_connections.broadcast(UserStatusWasUpdated(client_id, UserStatus.DISCONNECTED))


if __name__ == '__main__':
  server = Server(5100)
  server.run()
