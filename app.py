from dotenv import load_dotenv

from minutesai.ui import build_ui

load_dotenv()  # load .env before the UI checks for a dev key
demo = build_ui()

if __name__ == "__main__":
    demo.launch()
