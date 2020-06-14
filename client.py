import threading
from socket import SHUT_RDWR
from typing import Iterable, Callable

from protocol import PacketSender, PacketReceiver, Packet


class Client:
  def __init__(self, sock, packet_handler: Callable[[Packet], None]):
    self._socket = sock
    self._packet_handler = packet_handler
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
      self._packet_handler(packet)

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
