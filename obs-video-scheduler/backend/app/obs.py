from contextlib import contextmanager
from typing import Iterator

from obswebsocket import obsws, requests  # type: ignore

from .config import get_settings


@contextmanager
def obs_connection() -> Iterator[obsws]:
    settings = get_settings()
    client = obsws(settings.obs_host, settings.obs_port, settings.obs_password)
    client.connect()
    try:
        yield client
    finally:
        client.disconnect()


def launch_media(path: str, layer: int, scene_name: str, source_name: str, width: int | None, height: int | None, clear_on_media_end: bool = True) -> None:
    with obs_connection() as client:
        settings = {
            "is_local_file": True,
            "local_file": path,
        }
        if width:
            settings["width"] = width
        if height:
            settings["height"] = height
        client.call(requests.CreateSceneItem(scene_name, source_name, settings=settings, item_id=None, bounds=None, position=None, scale=None))
        if clear_on_media_end:
            client.call(requests.SetMediaInputSettings(source_name, settings, False))
        if layer:
            client.call(requests.SetSceneItemIndex(scene_name, source_name, layer))


def remove_source(scene_name: str, source_name: str) -> None:
    with obs_connection() as client:
        client.call(requests.DeleteSceneItem(scene_name, source_name))


def mute_source(source_name: str) -> None:
    with obs_connection() as client:
        client.call(requests.SetMute(source_name, True))


def unmute_source(source_name: str) -> None:
    with obs_connection() as client:
        client.call(requests.SetMute(source_name, False))


def heartbeat() -> None:
    with obs_connection():
        pass
