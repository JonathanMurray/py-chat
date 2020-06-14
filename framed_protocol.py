import threading
from abc import abstractmethod, ABCMeta
from dataclasses import dataclass
from typing import Optional, Iterable, Callable


def u8_to_bytes(unsigned_8bit_int: int) -> bytes:
  return int.to_bytes(unsigned_8bit_int, 1, 'big', signed=False)


class Packet(metaclass=ABCMeta):
  def __init__(self, packet_type: int):
    self.packet_type = packet_type

  def __repr__(self) -> str:
    return self.__class__.__name__

  def __bytes__(self) -> bytes:
    payload = self.encode_payload()
    return u8_to_bytes(len(payload)) + u8_to_bytes(self.packet_type) + payload

  @abstractmethod
  def encode_payload(self) -> bytes:
    pass


@dataclass
class OpaquePacket:
  packet_type: int
  payload: bytearray


def extract_packet_from(buffer: bytearray) -> Optional[OpaquePacket]:
  if buffer:
    payload_length = buffer[0]  # packet consists of [ LENGTH | TYPE | PAYLOAD ]
    if len(buffer) >= 2 + payload_length:
      packet_type = buffer[1]
      payload = buffer[2: 2 + payload_length]
      buffer[:] = buffer[2 + payload_length:]
      return OpaquePacket(packet_type, payload)


class PacketSender:
  def __init__(self, socket):
    self._socket = socket
    self._lock = threading.Lock()  # Sending data over a socket is not thread-safe

  def send_packet(self, packet: Packet):
    with self._lock:
      self._socket.sendall(bytes(packet))

  def send_packets(self, packets: Iterable[Packet]):
    data = b""
    for p in packets:
      data += bytes(p)
    with self._lock:
      self._socket.sendall(data)


def debug(log_message: str):
  enabled = False
  if enabled:
    print(f"[DEBUG] {log_message}")


class PacketReceiver:
  CAPACITY = 1000  # No packet is larger than this, so if the buffer fills up this much something's broken.

  def __init__(self, socket, packet_parser: Callable[[OpaquePacket], Packet]):
    self._socket = socket
    self._packet_parser = packet_parser
    self._buffer = bytearray()

  def wait_for_packet(self) -> Optional[Packet]:
    while True:
      packet = extract_packet_from(self._buffer)
      if packet:
        return self._packet_parser(packet)

      if len(self._buffer) > PacketReceiver.CAPACITY:
        raise Exception("Buffer reached max size but no message could be extracted!")

      received = self._socket.recv(10)
      debug(f"Received bytes: {received}")
      self._buffer += received
      if len(received) == 0:
        # Receiving 0 bytes is interpreted as the remote host disconnecting
        return None
