from ayon_server.settings import BaseSettingsModel, SettingsField
from ayon_server.settings.enum import folder_types_enum

class FolderTypeToParentItem(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(
        title="Folder type",
        enum_resolver=folder_types_enum
    )
    parent_folder: str = SettingsField(
        '',
        title="Parent folder",
        description=(
            "Folder in which the new asset will be created"
        ),
    )

class AssetCreatorSettings(BaseSettingsModel):
    """Asset Creator settings."""

    folder_types: list[FolderTypeToParentItem] = SettingsField(
        default_factory=FolderTypeToParentItem,
        title="Folder Types",
        description=(
            "Folder types from the project anatomy that will be available "
            "for the user when they create a new asset"
        )
    )


DEFAULT_VALUES = {
    "folder_types": [
        {"name": "Character", "parent_folder": "/ASSETS/CHARS"},
        {"name": "Prop", "parent_folder": "/ASSETS/PROPS"},
        {"name": "Ambiance", "parent_folder": "/ASSETS/AMBS"},
        {"name": "Set", "parent_folder": "/ASSETS/SETS"},
        {"name": "FX", "parent_folder": "/ASSETS/FX"},
        {"name": "Camera", "parent_folder": "/ASSETS/CAMS"},
    ],
}
