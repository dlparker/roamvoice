#!/usr/bin/env python
import sys
import multiprocessing
import subprocess
from nicegui import ui, app
from nicegui.events import KeyEventArguments
import pydbus
from gi.repository import GLib
from activate import activate_window

# Your existing invoke_speech_note_action
async def invoke_speech_note_action(action, param=""):
    try:
        bus = pydbus.SessionBus()
        speech_note = bus.get("net.mkiol.SpeechNote", "/net/mkiol/SpeechNote")
        param_variant = GLib.Variant('s', param)
        result = speech_note.InvokeAction(action, param_variant)
        print(f"Successfully invoked action '{action}' with param '{param}'", file=sys.stderr)
        return result
    except Exception as e:
        print(f"Error invoking SpeechNote action: {e}", file=sys.stderr)
        return None

def handle_key(e: KeyEventArguments):
    if e.key == 'f' and not e.action.repeat:
        if e.action.keyup:
            ui.notify('f was just released')
        elif e.action.keydown:
            ui.notify('f was just pressed')
    if e.modifiers.shift and e.action.keydown:
        if e.key.arrow_left:
            ui.notify('going left')
        elif e.key.arrow_right:
            ui.notify('going right')
        elif e.key.arrow_up:
            ui.notify('going up')
        elif e.key.arrow_down:
            ui.notify('going down')

async def send_emacs_command(command):
    try:
        result = subprocess.run(
            ["emacsclient", "-e", command],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error sending Emacs command: {e}", file=sys.stderr)
        return None

async def start_listening():
    if activate_window("emacs"):
        result = await invoke_speech_note_action("start-listening-active-window", "")
        ui.notify("Transcription complete" if result else "Transcription failed", type="positive" if result else "negative")
    else:
        ui.notify("Failed to activate Emacs", type="negative")

async def create_note():
    result = await send_emacs_command("(org-roam-capture)")
    ui.notify("Note created" if result else "Failed to create note", type="positive" if result else "negative")

@ui.page('/')
async def main():
    ui.button("Start Listening", on_click=start_listening)
    ui.button("New Note", on_click=create_note)
    ui.label("Press buttons to control Emacs and SpeechNote")
    keyboard = ui.keyboard(on_key=handle_key)

async def startup():
    await main()

multiprocessing.set_start_method("spawn", force=True)
app.on_startup(startup)
ui.run(native=True, window_size=(200, 500), fullscreen=False, title="Org-Roam Note Taker")
