"""
YURXZ REJOIN - Main Entry Point
Kivy app yang buka WebView ke server Python lokal
"""

import threading, time, os, sys

def start_backend():
    from server import start_server
    start_server(port=7437)

backend_thread = threading.Thread(target=start_backend, daemon=True)
backend_thread.start()
time.sleep(1.5)

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock

try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    WebView        = autoclass('android.webkit.WebView')
    WebViewClient  = autoclass('android.webkit.WebViewClient')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class AndroidWebView(Widget):
        def __init__(self, **kw):
            super().__init__(**kw)
            Clock.schedule_once(self._create, 0)

        @run_on_ui_thread
        def _create(self, dt):
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

    class YurxzApp(App):
        def build(self): return AndroidWebView()

except ImportError:
    import webbrowser
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.core.window import Window
    from kivy.utils import get_color_from_hex

    Window.clearcolor = get_color_from_hex("#080810")
    Window.size = (400, 700)

    class YurxzApp(App):
        def build(self):
            layout = BoxLayout(orientation='vertical', padding=20, spacing=12)
            layout.add_widget(Label(text="YURXZ REJOIN", font_size=22,
                color=get_color_from_hex("#a855f7"), size_hint_y=None, height=50))
            layout.add_widget(Label(text="http://localhost:7437",
                font_size=14, color=get_color_from_hex("#5a5878"),
                size_hint_y=None, height=40))
            btn = Button(text="Buka Browser", size_hint_y=None, height=48,
                background_color=get_color_from_hex("#7c3aed"))
            btn.bind(on_press=lambda *a: webbrowser.open("http://localhost:7437"))
            layout.add_widget(btn)
            webbrowser.open("http://localhost:7437")
            return layout

if __name__ == '__main__':
    YurxzApp().run()
