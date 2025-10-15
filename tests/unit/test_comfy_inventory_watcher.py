import json
import threading
from pathlib import Path

import pytest

from app.utils.comfy_inventory import create_inventory_item, dump_inventory, normalise_path


def test_create_inventory_item_file_and_directory(tmp_path):
    base = tmp_path

    file_path = base / "test.txt"
    file_path.write_text("hello")
    file_item = create_inventory_item(file_path, base)

    assert file_item is not None
    assert file_item.kind == "file"
    assert file_item.size == 5
    assert file_item.relative_path == "test.txt"

    dir_path = base / "models"
    dir_path.mkdir()
    dir_item = create_inventory_item(dir_path, base)

    assert dir_item is not None
    assert dir_item.kind == "directory"
    assert dir_item.size == 0
    assert dir_item.relative_path == "models"


def test_dump_inventory_orders_items(tmp_path):
    output = tmp_path / "inventory.json"
    inventory = {
        "/tmp/models": {
            "absolute_path": "/tmp/models",
            "relative_path": "ComfyUI/models",
            "kind": "directory",
            "size": 0,
            "modified": "2024-01-01T00:00:00+0000",
        },
        "/tmp/model.ckpt": {
            "absolute_path": "/tmp/model.ckpt",
            "relative_path": "ComfyUI/models/checkpoints/model.ckpt",
            "kind": "file",
            "size": 42,
            "modified": "2024-01-01T00:00:00+0000",
        },
    }

    dump_inventory(output, inventory)

    data = json.loads(output.read_text())
    assert data[0]["kind"] == "directory"
    assert data[1]["kind"] == "file"


def test_handler_updates_inventory(tmp_path):
    pytest.importorskip("watchdog", reason="watchdog dependency is required for handler tests")
    from scripts.comfy_inventory_watcher import InventoryEventHandler

    output = tmp_path / "inventory.json"
    inventory: dict[str, dict[str, object]] = {}
    handler = InventoryEventHandler(
        inventory=inventory,
        lock=threading.Lock(),
        base=tmp_path,
        output_file=output,
        log_events=False,
    )

    class Event:
        def __init__(self, src: Path, dest: Path | None = None):
            self.src_path = str(src)
            self.dest_path = str(dest) if dest else None
            self.is_directory = False

    file_path = tmp_path / "node.py"
    file_path.write_text("print('hi')")

    handler.on_created(Event(file_path))
    assert len(inventory) == 1

    contents = json.loads(output.read_text())
    assert contents[0]["absolute_path"] == str(normalise_path(file_path))

    file_path.write_text("print('hello')")
    handler.on_modified(Event(file_path))
    assert len(inventory) == 1

    file_path.unlink()
    handler.on_deleted(Event(file_path))
    assert inventory == {}
    assert json.loads(output.read_text()) == []


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
