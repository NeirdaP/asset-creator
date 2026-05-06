from ayon_server.settings import BaseSettingsModel, SettingsField
from ayon_server.settings.enum import folder_types_enum
from ayon_server.settings.enum import task_types_enum


class FolderTypeToParentItem(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(
        title="Folder type",
        enum_resolver=folder_types_enum
    )
    parent_folder: str = SettingsField(
        "",
        title="Parent folder",
        description=(
            "Folder in which the new asset will be created"
        ),
    )
    default_task_types: list[str] = SettingsField(
        title="Default task types",
        enum_resolver=task_types_enum,
        description=(
            "Default task types for this folder type"
        )
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
    "folder_types": []
}
