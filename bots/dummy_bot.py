from models.data_models import UiTree


class DummyBot:
    def __init__(self, config: dict):
        self.config = config

    def run(self, ui_tree: UiTree):
        pass
