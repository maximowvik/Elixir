# vendor/core/command_manager.py

import re

class CommandManager:
    def __init__(self):
        self.commands = {}

    def register_command(self, name, handler):
        self.commands[name] = handler

    def parse_command(self, text):
        if not text.startswith("/"):
            return None, None

        parts = text.strip().split(" ", 1)
        command = parts[0]
        args_text = parts[1] if len(parts) > 1 else ""

        args = self.parse_arguments(args_text)
        return command, args

    def parse_arguments(self, text):
        args = {}
        matches = re.findall(r'--(\w+)="?(.*?)"?\s', text + " ")
        for key, value in matches:
            args[key] = value
        return args

    def execute(self, command_text):
        command, args = self.parse_command(command_text)
        if command in self.commands:
            return self.commands[command](args)
        else:
            raise ValueError("Command not found.")
