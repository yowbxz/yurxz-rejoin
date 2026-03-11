"""
YURXZ REJOIN - Main Entry Point
Kivy app yang buka WebView ke server Python lokal
"""

import threading
import time
import os
import sys

# Tangkap semua error ke file log
import traceback

LOG_FILE = "/sdcard/yurxz_log.txt"

def write_log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except:
        pass

write_log("=== YURXZ START ===")

def start_backend():
    try:
        write_log("Starting server...")
        from server import start_server
        start_server(port=7437)
    except Exception as e:
        write_log(f"SERVER ERROR: {e}")
        write_log(traceback.format_exc())

backend_thread = threading.Thread(target=start_backend, daemon=True)
backend_thread.start()
write_log("Backend thread started")
time.sleep(2)
write_log("Importing kivy...")

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock

write_log("Kivy imported OK")

try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    WebView        = autoclass('android.webkit.WebView')
    WebViewClient  = autoclass('android.webkit.WebViewClient')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    write_log("Android imports OK")

    class AndroidWebView(Widget):
        def __init__(self, **kw):
            super().__init__(**kw)
            Clock.schedule_once(self._create, 0)

        @run_on_ui_thread
        def _create(self, dt):
            try:
                activity = PythonActivity.mActivity
                self.wv  = WebView(activity)
                s = self.wv.getSettings()
                s.setJavaScriptEnabled(True)
                s.setDomStorageEnabled(True)
                s.setLoadWithOverviewMode(True)
                s.setUseWideViewPort(True)
                s.setBuiltInZoomControls(False)
                s.setDisplayZoomControls(False)
                self.wv.setWebViewClient(WebViewClient())
                self.wv.loadUrl("http://localhost:7437")
                activity.setContentView(self.wv)
                write_log("WebView loaded OK")
            except Exception as e:
                write_log(f"WEBVIEW ERROR: {e}")
                write_log(traceback.format_exc())

    class YurxzApp(App):
        def build(self):
            write_log("Building app...")
            return AndroidWebView()

except ImportError as e:
    write_log(f"Android import failed (mungkin di PC): {e}")
    import webbrowser
    from kivy.core.window import Window
    from kivy.utils import get_color_from_hex
    from kivy.uix.button import Button

    Window.clearcolor = get_color_from_hex("#080810")
    Window.size = (400, 700)

    class YurxzApp(App):
        def build(self):
            layout = BoxLayout(orientation='vertical', padding=20, spacing=12)
            layout.add_widget(Label(
                text="YURXZ REJOIN",
                font_size=22,
                color=get_color_from_hex("#a855f7"),
                size_hint_y=None,
                height=50
            ))
            layout.add_widget(Label(
                text="http://localhost:7437",
                font_size=14,
                color=get_color_from_hex("#5a5878"),
                size_hint_y=None,
                height=40
            ))
            btn = Button(
                text="Buka Browser",
                size_hint_y=None,
                height=48,
                background_color=get_color_from_hex("#7c3aed")
            )
            btn.bind(on_press=lambda *a: webbrowser.open("http://localhost:7437"))
            layout.add_widget(btn)
            webbrowser.open("http://localhost:7437")
            return layout

try:
    write_log("Running app...")
    YurxzApp().run()
except Exception as e:
    write_log(f"APP ERROR: {e}")
    write_log(traceback.format_exc())
