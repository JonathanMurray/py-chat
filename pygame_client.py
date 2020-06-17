#!/usr/bin/env python3

import sys
from socket import socket, AF_INET, SOCK_STREAM
from typing import Optional, Set

import pygame
from pygame.font import Font
from pygame.rect import Rect
from pygame.surface import Surface

from chat_protocol import UserWroteMessage, UserStatusWasUpdated, UserStatus, SubmitMessage, SubmitUserStatus
from client import Client
from framed_protocol import Packet

COLOR_TEXT = (255, 255, 255)


# TODO Show list of online users


class PygameClient:

  def __init__(self, sock, user_name: Optional[str]):
    pygame.init()
    self._screen: Surface = pygame.display.set_mode((600, 400))
    self._font = Font("resources/font.ttf", 14)
    self._rendered_messages = []
    self._input_text = ""
    self._rendered_input = Surface((1, 1))
    self._update_input("")
    self._people_typing: Set[str] = set()
    self._rendered_people_typing = Surface((1, 1))
    self._client = Client(sock, user_name, self._handle_packet)
    user_name = self._client.log_in_to_server()
    self._add_message(f"You logged in as \"{user_name}\"")
    self._client.start_receiver_thread()

  def _update_input(self, text: str):
    if not self._input_text and text:
      self._client.send_packets([SubmitUserStatus(UserStatus.TYPING)])
    elif self._input_text and not text:
      self._client.send_packets([SubmitUserStatus(UserStatus.NOT_TYPING)])

    self._input_text = text
    self._rendered_input = self._render_text("> " + self._input_text)

  def _update_is_typing(self, user_name: str, is_typing: bool):
    if is_typing:
      self._people_typing.add(user_name)
    elif user_name in self._people_typing:
      self._people_typing.remove(user_name)
    num_people_typing = len(self._people_typing)
    if num_people_typing == 0:
      text = ""
    elif num_people_typing == 1:
      text = f"{next(iter(self._people_typing))} is typing..."
    elif num_people_typing == 2:
      it = iter(self._people_typing)
      text = f"{next(it)} and {next(it)} are typing..."
    else:
      text = "Several people are typing..."
    self._rendered_people_typing = self._render_text(text)

  def _render_text(self, text: str) -> Surface:
    rendered_text = self._font.render(text, True, COLOR_TEXT)
    return rendered_text

  def _handle_packet(self, packet: Packet):
    if isinstance(packet, UserWroteMessage):
      p: UserWroteMessage = packet
      self._add_message(f"{p.user_name}: {p.message}")
    elif isinstance(packet, UserStatusWasUpdated):
      p: UserStatusWasUpdated = packet
      if p.status == UserStatus.LOGGED_IN:
        self._add_message(
            f"{p.user_name} LOGGED IN")  # TODO Render status messages like this one with a different color
      elif p.status == UserStatus.LOGGED_OUT:
        self._add_message(f"{p.user_name} DISCONNECTED")
        self._update_is_typing(p.user_name, is_typing=False)
      elif p.status == UserStatus.TYPING:
        self._update_is_typing(p.user_name, is_typing=True)
      elif p.status == UserStatus.NOT_TYPING:
        self._update_is_typing(p.user_name, is_typing=False)

  def _add_message(self, text: str):
    self._rendered_messages.append(self._render_text(text))
    if len(self._rendered_messages) > 15:
      self._rendered_messages.pop(0)

  def run(self):
    while True:
      self.run_one_frame()

  def run_one_frame(self):
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        print("Good bye")
        pygame.quit()
        sys.exit(0)
      elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_BACKSPACE:
          self._update_input(self._input_text[:-1])
        elif event.key == pygame.K_RETURN:
          self._client.send_packets([SubmitMessage(self._input_text)])
          self._update_input("")
        else:
          self._update_input(self._input_text + chr(event.key))

    self._screen.fill((100, 50, 150))
    for i, rendered_message in enumerate(self._rendered_messages):
      self._screen.blit(rendered_message, (32, 32 + i * 20))
    pygame.draw.rect(self._screen, (255, 255, 255), Rect(28, 350, 400, 20), 1)
    self._screen.blit(self._rendered_input, (32, 350))
    self._screen.blit(self._rendered_people_typing, (32, 320))

    pygame.display.flip()


def run_client(server_port: int, user_name: Optional[str]):
  with socket(AF_INET, SOCK_STREAM) as sock:
    print(f"Connecting to server (remote_port: {server_port})...")
    sock.connect(("localhost", server_port))
    print("Connected.")
    pygame_client = PygameClient(sock, user_name)
    pygame_client.run()


def main():
  args = sys.argv[1:]
  if args:
    user_name = args[0]
  else:
    user_name = None
  run_client(5100, user_name)


if __name__ == '__main__':
  main()
