from ayon_server.settings import BaseSettingsModel, SettingsField
from ayon_server.settings.enum import folder_types_enum
from ayon_server.settings.enum import task_types_enum


class TasksTemplateGroup(BaseSettingsModel):
    name: str = SettingsField(
        title="Name",
    )
    default_task_types: list[str] = SettingsField(
        title="Default task types",
        enum_resolver=task_types_enum,
        description=(
            "Default task types for this folder type"
        )
    )


class FolderTypeGroup(BaseSettingsModel):
    name: str = SettingsField(
        enum_resolver=folder_types_enum,
    )
    parent_folder: str = SettingsField(
        description=(
            "Folder in which the new asset will be created"
        )
    )
    tasks_templates: list[TasksTemplateGroup] = SettingsField(
        default=[{
            "name": "Default",
            "default_task_types": []
        }],
        description=(
            "Different task templates for this folder"
        ),
    )


class AssetCreatorSettings(BaseSettingsModel):
    """Asset Creator settings."""

    folder_types: list[FolderTypeGroup] = SettingsField(
        default_factory=list,
        description=(
            "Folder types from the project anatomy that will be available "
            "for the user when they create a new asset"
        )
    )


DEFAULT_VALUES = {
    "folder_types": []
}
