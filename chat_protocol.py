from enum import Enum
from typing import Optional

from framed_protocol import Packet, OpaquePacket, u8_to_bytes


def bool_to_bytes(b: bool) -> bytes:
  return bool.to_bytes(b, 1, 'big', signed=False)


class PacketType(Enum):
  PING = 1
  SUBMIT_MESSAGE = 2
  USER_WROTE_MESSAGE = 3
  SUBMIT_USER_STATUS = 4
  USER_STATUS_WAS_UPDATED = 5
  LOGIN = 6
  LOGIN_RESPONSE = 7

  def __bytes__(self) -> bytes:
    return u8_to_bytes(self.value)


# TODO Separate between server and client packets (to increase type-safety and clarity around what messages need to be
# handled where.

class Ping(Packet):
  def __init__(self):
    super().__init__(PacketType.PING.value)

  def encode_payload(self) -> bytes:
    return b""

  @staticmethod
  def decode_payload(_: bytearray) -> Optional[Packet]:
    return Ping()


class SubmitMessage(Packet):
  """ Sent from a client to the server to submit a new chat message to the channel. """

  def __init__(self, message: str):
    if len(message) > 255:
      raise Exception("Payload must not be larger than 255 bytes!")
    super().__init__(PacketType.SUBMIT_MESSAGE.value)
    self.message = message

  def __repr__(self):
    return f"{super().__repr__()}('{self.message}')"

  def encode_payload(self) -> bytes:
    return self.message.encode("utf8")

  @staticmethod
  def decode_payload(payload: bytearray) -> Optional[Packet]:
    message = payload.decode("utf8")
    return SubmitMessage(message)


class UserWroteMessage(Packet):
  """ Broadcast from the server. Informs that a user sent a message. """

  def __init__(self, user_name: str, message: str):
    if len(message) > 255:
      raise Exception("Payload must not be larger than 255 bytes!")
    super().__init__(PacketType.USER_WROTE_MESSAGE.value)
    self.user_name = user_name
    self.message = message

  def __repr__(self):
    return f"{super().__repr__()}({self.user_name}: '{self.message}')"

  def encode_payload(self) -> bytes:
    return u8_to_bytes(len(self.user_name)) \
           + self.user_name.encode("utf8") \
           + self.message.encode("utf8")

  @staticmethod
  def decode_payload(payload: bytearray) -> Optional[Packet]:
    user_name_length = payload[0]
    user_name = payload[1:1 + user_name_length].decode("utf8")
    message = payload[1 + user_name_length:].decode("utf8")
    return UserWroteMessage(user_name, message)


class UserStatus(Enum):
  LOGGED_IN = 1
  LOGGED_OUT = 2
  TYPING = 3
  NOT_TYPING = 4

  def __bytes__(self) -> bytes:
    return u8_to_bytes(self.value)


class SubmitUserStatus(Packet):
  """ Sent from a client to the server to inform about a status update. """

  def __init__(self, status: UserStatus):
    super().__init__(PacketType.SUBMIT_USER_STATUS.value)
    self.status = status

  def __repr__(self):
    return f"{super().__repr__()}({self.status})"

  def encode_payload(self) -> bytes:
    return bytes(self.status)

  @staticmethod
  def decode_payload(payload: bytearray) -> Optional[Packet]:
    status = UserStatus(payload[0])
    return SubmitUserStatus(status)


class UserStatusWasUpdated(Packet):
  """ Broadcast from the server. Informs that a user went through a status update. """

  def __init__(self, user_name: str, status: UserStatus):
    super().__init__(PacketType.USER_STATUS_WAS_UPDATED.value)
    self.user_name = user_name
    self.status = status

  def __repr__(self):
    return f"{super().__repr__()}({self.user_name} - {self.status})"

  def encode_payload(self) -> bytes:
    return bytes(self.status) \
           + self.user_name.encode("utf8")

  @staticmethod
  def decode_payload(payload: bytearray) -> Optional[Packet]:
    status = UserStatus(payload[0])
    user_name = payload[1:].decode("utf8")
    return UserStatusWasUpdated(user_name, status)


class Login(Packet):
  """ Sent from a client to the server to register register itself and claim a user-name. """

  def __init__(self, user_name: Optional[str]):
    super().__init__(PacketType.LOGIN.value)
    self.user_name = user_name if user_name else ""

  def __repr__(self):
    return f"{super().__repr__()}({self.user_name})"

  def encode_payload(self):
    return self.user_name.encode("utf8")

  @staticmethod
  def decode_payload(payload: bytearray) -> Optional[Packet]:
    name = payload.decode("utf8")
    return Login(name)


class LoginResponse(Packet):
  """ Sent from the server as a response to a login-attempt from a client. """

  def __init__(self, success: bool, message: str):
    super().__init__(PacketType.LOGIN_RESPONSE.value)
    self.success = success
    self.message = message

  def __repr__(self):
    return f"{super().__repr__()}(success={self.success}, message={self.message})"

  def encode_payload(self):
    return bool_to_bytes(self.success) \
           + self.message.encode("utf8")

  @staticmethod
  def decode_payload(payload: bytearray) -> Optional[Packet]:
    success = bool(payload[0])
    message = payload[1:].decode("utf8")
    return LoginResponse(success, message)


def parse_packet(opaque_packet: OpaquePacket) -> Optional[Packet]:
  # noinspection PyBroadException
  try:
    packet_classes_by_type = {
      PacketType.PING: Ping,
      PacketType.SUBMIT_MESSAGE: SubmitMessage,
      PacketType.USER_WROTE_MESSAGE: UserWroteMessage,
      PacketType.SUBMIT_USER_STATUS: SubmitUserStatus,
      PacketType.USER_STATUS_WAS_UPDATED: UserStatusWasUpdated,
      PacketType.LOGIN: Login,
      PacketType.LOGIN_RESPONSE: LoginResponse
    }
    packet_class = packet_classes_by_type[PacketType(opaque_packet.packet_type)]
    return packet_class.decode_payload(opaque_packet.payload)
  except Exception:
    print(f"Failed to parse packet: {opaque_packet}")
    raise
