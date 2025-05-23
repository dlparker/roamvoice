#!/usr/bin/env python
import pydbus
import os
import sys
from gi.repository import GLib

# D-Bus interface XML
DBUS_INTERFACE_XML = """
<node>
  <interface name="com.example.WindowManagement">
    <method name="WindowFound"/>
    <method name="WindowNotFound"/>
  </interface>
</node>
"""

class WindowManagement:
    """D-Bus interface to receive KWin script results."""
    __doc__ = DBUS_INTERFACE_XML

    def __init__(self):
        self.found = False

    def WindowFound(self):
        self.found = True
        print("WindowFound signal received", file=sys.stderr)

    def WindowNotFound(self):
        self.found = False
        print("WindowNotFound signal received", file=sys.stderr)

def generate_kwin_script(window_title=None, window_class=None):
    """Generate a KWin script to activate a window by title or class."""
    window_title_escaped = (window_title or "").replace("'", "\\'")
    window_class_escaped = (window_class or "").replace("'", "\\'")
    return f"""
    function activateWindow() {{
        print("Starting KWin script for class='{window_class_escaped}', title='{window_title_escaped}'");
        var compareToCaption = new RegExp('{window_title_escaped}' || '', 'i');
        var compareToClass = '{window_class_escaped}';
        var isCompareToClass = compareToClass.length > 0;
        var clients = workspace.clientList();
        print("Found " + clients.length + " clients");
        for (var i = 0; i < clients.length; i++) {{
            var client = clients[i];
            print("Client " + i + ": caption='" + client.caption + "', class='" + client.resourceClass + "'");
            var classCompare = (isCompareToClass && client.resourceClass == compareToClass);
            var captionCompare = (!isCompareToClass && compareToCaption.test(client.caption));
            if (classCompare || captionCompare) {{
                print("Activating window: " + client.caption);
                workspace.activeClient = client;
                callDBus("com.example.WindowManagement", "/WindowManagement", "com.example.WindowManagement", "WindowFound");
                print("WindowFound signal sent");
                return;
            }}
        }}
        print("No matching window found");
        callDBus("com.example.WindowManagement", "/WindowManagement", "com.example.WindowManagement", "WindowNotFound");
    }}
    activateWindow();
    """

def activate_window(window_title=None, window_class=None):
    """Activate a window by title or class using KWin D-Bus scripting."""
    if not window_title and not window_class:
        raise ValueError("Must provide window_title or window_class")

    # Connect to the session bus
    bus = pydbus.SessionBus()

    # Create a D-Bus service to receive script results
    window_mgmt = WindowManagement()
    try:
        publication = bus.publish("com.example.WindowManagement", ("/WindowManagement", window_mgmt))
        print("D-Bus service published at com.example.WindowManagement", file=sys.stderr)
    except Exception as e:
        print(f"Failed to publish D-Bus service: {e}", file=sys.stderr)
        return False

    # Generate the KWin script
    script_content = generate_kwin_script(window_title, window_class)

    # Save the script to a temporary file
    script_path = "/tmp/kwin_activate_window.js"
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        os.chmod(script_path, 0o644)
    except OSError as e:
        print(f"Failed to write script file: {e}", file=sys.stderr)
        return False

    # Load and run the KWin script
    try:
        kwin = bus.get("org.kde.KWin", "/Scripting")
        script_id = kwin.loadScript(script_path)
        if not script_id:
            print("Failed to load script: Invalid script ID", file=sys.stderr)
            return False

        script_obj = bus.get("org.kde.KWin", f"/{script_id}")
        print(f"Running script with ID: {script_id}", file=sys.stderr)
        script_obj.run()

        # Run a GLib main loop to process D-Bus signals
        loop = GLib.MainLoop()
        timeout = 0.001  # Minimal timeout (1ms) since signals are immediate
        GLib.timeout_add(int(timeout * 1000), loop.quit)
        loop.run()

        return window_mgmt.found
    except Exception as e:
        print(f"Error running KWin script: {e}", file=sys.stderr)
        return False
    finally:
        # Unpublish the D-Bus service
        try:
            publication.unpublish()
            print("D-Bus service unpublished", file=sys.stderr)
        except:
            pass
        # Clean up the script file
        try:
            os.remove(script_path)
        except OSError:
            pass

# Example usage
if __name__ == "__main__":
    success = activate_window(window_class="emacs")
    print("Activation successful" if success else "Activation failed")
