import textual
from textual.app import App
from textual.screen import Screen

print(f"Textual Version: {textual.__version__}")

class TestApp(App):
    def on_mount(self):
        timer = self.set_interval(1.0, self.callback)
        print(f"set_interval returns: {type(timer)}")
        print(f"Has pause? {hasattr(timer, 'pause')}")
        self.exit()

    def callback(self):
        pass

if __name__ == "__main__":
    try:
        TestApp().run()
    except Exception as e:
        print(f"Error: {e}")
