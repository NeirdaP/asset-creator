import os
from ayon_core.addon import (
    AYONAddon,
    ITrayAction
)
from .version import __version__

MY_STUDIO_ADDON_ROOT = os.path.dirname(os.path.abspath(__file__))
ADDON_NAME = "asset_creator"
ADDON_LABEL = "Asset Creator"

class AssetCreator(AYONAddon, ITrayAction):
    name = ADDON_NAME
    label = ADDON_LABEL
    version = __version__

    def initialize(self, settings):
        """Initialization of module."""
        self._dialog = None

    # ITrayAddon, ITrayAction
    def tray_init(self):
        """Tray init."""
        pass
        
    def on_action_trigger(self):
        if self._dialog is None:
            from .ui.ui import MainWindow
            self._dialog = MainWindow()
        self._dialog.open()

