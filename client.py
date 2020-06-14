#!/usr/bin/env python3
import random
import threading
from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR
from time import sleep
from typing import Iterable

from protocol import Ping, SubmitMessage, PacketSender, PacketReceiver, Packet


class Client:
  def __init__(self, sock):
    self._socket = sock
    self._sender = PacketSender(self._socket)
    self._connected = True

  @property
  def connected(self):
    return self._connected

  def __enter__(self):
    self._start_receiver_thread()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    details = f" ({exc_type.__name__}: {exc_val})" if exc_type else ""
    print(f"Closing client{details}")
    self.close()

  def _start_receiver_thread(self):
    receiver_thread = threading.Thread(target=self._receive_packets)
    receiver_thread.start()

  def _receive_packets(self):
    receiver = PacketReceiver(self._socket)
    while self._connected:
      packet = receiver.wait_for_packet()
      if not packet:
        print("Received end-of-stream from server. Will disconnect.")
        self.close()
        break
      print(f"Received from server: {packet}")

  def close(self):
    if self._connected:
      self._connected = False
      try:
        self._socket.shutdown(SHUT_RDWR)
      except OSError:
        print(f"Couldn't shutdown socket (because it was already shutdown from server's side likely)")
      self._socket.close()
      print(f"Disconnected from server")

  def send_packets(self, packets: Iterable[Packet]):
    if not self._connected:
      raise Exception("Cannot send packet. Client has disconnected!")
    self._sender.send_packets(packets)


def run_client(remote_port):
  messages = [b"Apple", b"Banana", b"Pineapple"]
  with socket(AF_INET, SOCK_STREAM) as sock:
    print(f"Connecting to server (remote_port: {remote_port})...")
    sock.connect(("localhost", remote_port))
    with Client(sock) as client:
      while client.connected:
        message = random.choice(messages)
        print(f"Sending message: {message}")
        chat_message = SubmitMessage(bytearray(message))
        client.send_packets([Ping(), chat_message, Ping()])
        sleep(random.randint(5, 10))
      print("Exiting.")


if __name__ == '__main__':
  run_client(5100)
