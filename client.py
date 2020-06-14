import threading
from socket import SHUT_RDWR
from typing import Iterable, Callable, Optional

import chat_protocol
from chat_protocol import Packet, Login, LoginResponse
from framed_protocol import PacketSender, PacketReceiver


class Client:
  def __init__(self, sock, user_name: Optional[str], packet_handler: Callable[[Packet], None]):
    self._socket = sock
    self._user_name = user_name
    self._packet_handler = packet_handler
    self._sender = PacketSender(self._socket)
    self._receiver = PacketReceiver(self._socket, chat_protocol.parse_packet)
    self._connected = True

  @property
  def connected(self):
    return self._connected

  def __enter__(self):
    print("Logging in...")
    login = Login(self._user_name)
    self._sender.send_packets([login])
    login_response = self._receiver.wait_for_packet()
    if not isinstance(login_response, LoginResponse):
      raise Exception(f"Unexpected login response from server: {login_response}")
    if not login_response.success:
      raise Exception(f"Failed to log in! ({login_response.message})")
    self._user_name = login_response.message
    print(f"Logged in as '{login_response.message}'")
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
    while self._connected:
      packet = self._receiver.wait_for_packet()
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
