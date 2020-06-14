import threading
from enum import Enum
from typing import Optional, Iterable


def u8_to_bytes(unsigned_8bit_int: int) -> bytes:
  return int.to_bytes(unsigned_8bit_int, 1, 'big', signed=False)


def bool_to_bytes(b: bool) -> bytes:
  return bool.to_bytes(b, 1, 'big', signed=False)


class PacketType(Enum):
  PING = 1
  SUBMIT_MESSAGE = 2
  USER_WROTE_MESSAGE = 3
  USER_STATUS_WAS_UPDATED = 4
  LOGIN = 5
  LOGIN_RESPONSE = 6

  def __bytes__(self) -> bytes:
    return u8_to_bytes(self.value)


class Packet:
  def __init__(self, packet_type: PacketType):
    self.packet_type = packet_type

  def __repr__(self) -> str:
    return self.packet_type.name

  def __bytes__(self) -> bytes:
    return bytes(self.packet_type)


class Ping(Packet):
  def __init__(self):
    super().__init__(PacketType.PING)

  @staticmethod
  def extract_from(buffer: bytearray) -> Optional[Packet]:
    buffer.pop(0)
    return Ping()


class SubmitMessage(Packet):
  def __init__(self, payload: bytes):
    if len(payload) > 255:
      raise Exception("Payload must not be larger than 255 bytes!")
    super().__init__(PacketType.SUBMIT_MESSAGE)
    self.payload = payload

  def __repr__(self):
    payload = self.payload.decode("utf8")
    return f"{super().__repr__()}('{payload}')"

  def __bytes__(self) -> bytes:
    return super().__bytes__() \
           + u8_to_bytes(len(self.payload)) \
           + self.payload

  @staticmethod
  def extract_from(buffer: bytearray) -> Optional[Packet]:
    if len(buffer) >= 2:
      payload_size = buffer[1]
      if len(buffer) >= 2 + payload_size:
        payload = bytes(buffer[2:2 + payload_size])
        buffer[:] = buffer[2 + payload_size:]
        return SubmitMessage(payload)


class UserWroteMessage(Packet):
  def __init__(self, user_id: int, message: bytes):
    if len(message) > 255:
      raise Exception("Payload must not be larger than 255 bytes!")
    super().__init__(PacketType.USER_WROTE_MESSAGE)
    self.user_id = user_id
    self.message = message

  def __repr__(self):
    message = self.message.decode("utf8")
    return f"{super().__repr__()}({self.user_id}: '{message}')"

  def __bytes__(self) -> bytes:
    return super().__bytes__() \
           + u8_to_bytes(self.user_id) \
           + u8_to_bytes(len(self.message)) \
           + self.message

  @staticmethod
  def extract_from(buffer: bytearray) -> Optional[Packet]:
    if len(buffer) >= 3:
      user_id = buffer[1]
      message_size = buffer[2]
      if len(buffer) >= 3 + message_size:
        message = bytes(buffer[3:3 + message_size])
        buffer[:] = buffer[3 + message_size:]
        return UserWroteMessage(user_id, message)


class UserStatus(Enum):
  LOGGED_IN = 1
  LOGGED_OUT = 2

  def __bytes__(self) -> bytes:
    return u8_to_bytes(self.value)


class UserStatusWasUpdated(Packet):
  def __init__(self, user_id: int, status: UserStatus):
    super().__init__(PacketType.USER_STATUS_WAS_UPDATED)
    self.user_id = user_id
    self.status = status

  def __repr__(self):
    return f"{super().__repr__()}({self.user_id} - {self.status})"

  def __bytes__(self) -> bytes:
    return super().__bytes__() \
           + u8_to_bytes(self.user_id) \
           + bytes(self.status)

  @staticmethod
  def extract_from(buffer: bytearray) -> Optional[Packet]:
    if len(buffer) >= 3:
      user_id = buffer[1]
      status = UserStatus(buffer[2])
      buffer[:] = buffer[3:]
      return UserStatusWasUpdated(user_id, status)


class Login(Packet):
  def __init__(self, user_name: Optional[str]):
    super().__init__(PacketType.LOGIN)
    self.user_name = user_name if user_name else ""

  def __repr__(self):
    return f"{super().__repr__()}({self.user_name})"

  def __bytes__(self):
    return super().__bytes__() \
           + u8_to_bytes(len(self.user_name)) \
           + self.user_name.encode("utf8")

  @staticmethod
  def extract_from(buffer: bytearray) -> Optional[Packet]:
    if len(buffer) >= 2:
      name_length = buffer[1]
      if len(buffer) >= 2 + name_length:
        name = buffer[2:2 + name_length].decode("utf8")
        buffer[:] = buffer[2 + name_length:]
        return Login(name)


class LoginResponse(Packet):
  def __init__(self, success: bool, message: str):
    super().__init__(PacketType.LOGIN_RESPONSE)
    self.success = success
    self.message = message

  def __repr__(self):
    return f"{super().__repr__()}(success={self.success}, message={self.message})"

  def __bytes__(self):
    return super().__bytes__() \
           + bool_to_bytes(self.success) \
           + u8_to_bytes(len(self.message)) \
           + self.message.encode("utf8")

  @staticmethod
  def extract_from(buffer: bytearray) -> Optional[Packet]:
    if len(buffer) >= 3:
      success = bool(buffer[1])
      message_length = buffer[2]
      if len(buffer) >= 3 + message_length:
        message = buffer[3: 3 + message_length].decode("utf8")
        buffer[:] = buffer[3 + message_length:]
        return LoginResponse(success, message)


# TODO implement pinging (client sends ping to server, it responds, client notes the latency)


def extract_packet_from(buffer: bytearray) -> Optional[Packet]:
  try:
    if buffer:
      packet_type = PacketType(buffer[0])
      packet_class = {
        PacketType.PING: Ping,
        PacketType.SUBMIT_MESSAGE: SubmitMessage,
        PacketType.USER_WROTE_MESSAGE: UserWroteMessage,
        PacketType.USER_STATUS_WAS_UPDATED: UserStatusWasUpdated,
        PacketType.LOGIN: Login,
        PacketType.LOGIN_RESPONSE: LoginResponse
      }[packet_type]
      return packet_class.extract_from(buffer)
  except IndexError as e:
    print(f"[ERROR] Failed to parse buffer: {buffer}")
    raise e


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

  def __init__(self, socket):
    self._socket = socket
    self._buffer = bytearray()

  def wait_for_packet(self) -> Optional[Packet]:
    while True:
      packet = extract_packet_from(self._buffer)
      if packet:
        return packet

      if len(self._buffer) > PacketReceiver.CAPACITY:
        raise Exception("Buffer reached max size but no message could be extracted!")

      received = self._socket.recv(10)
      debug(f"Received bytes: {received}")
      self._buffer += received
      if len(received) == 0:
        # Receiving 0 bytes is interpreted as the remote host disconnecting
        return None
