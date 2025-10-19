# ComfyUI Inventory Tracking

This note summarises how ComfyUI organises its assets and explains the new
`scripts/comfy_inventory_watcher.py` utility that keeps a live inventory of the
installation.  It is intended to address the requirements captured in
`tasks/Task1.md`.

## How ComfyUI manages assets

ComfyUI is a node-based Stable Diffusion interface.  The upstream project
focuses on orchestrating inference pipelines and delegates model management to
regular filesystem folders.  A typical installation contains:

- `models/` with subdirectories such as `checkpoints/`, `vae/`, `loras/`,
  `controlnet/`, etc.  ComfyUI reads whatever files exist in those folders at
  startup; there is no background watcher that reports newly added or deleted
  models.
- `custom_nodes/` containing Python packages that provide extra nodes.  When a
  module is added or removed, ComfyUI discovers it on the next launch.
- `input/` and `output/` folders used for workflow assets and renders.

The project does **not** ship an official inventory or auditing mechanism for
models, custom nodes, or download folders.  Community launchers such as ComfyUI
Manager can install content, but they still rely on the same directories.  As a
result, keeping a "current inventory" requires an external watcher.

## Inventory watcher overview

`scripts/comfy_inventory_watcher.py` provides a small CLI to monitor the
directories above and any download locations you want to track.  It produces a
JSON file (default: `comfy_inventory.json`) that lists every file and directory
with its size, last-modified time, and a path relative to the ComfyUI parent
folder when possible.

Key behaviours:

- Runs happily from the directory above `ComfyUI` (default assumption) but
  allows overriding `--comfy-root`, `--downloads`, and `--extra` watch paths.
- Performs a full scan on startup so the inventory reflects the current state
  before live monitoring begins.
- Updates the JSON atomically on each change so other processes can read a
  consistent snapshot.
- Ignores noisy directory modification events while still tracking creations,
  deletions, moves, and file updates.

Example usage:

```bash
python scripts/comfy_inventory_watcher.py \
  --comfy-root ./ComfyUI \
  --downloads ~/Downloads \
  --extra ~/stable-diffusion-assets
```

This command creates/updates `comfy_inventory.json` in the working directory and
logs changes as they happen.

## Am I reinventing something ComfyUI already does?

No.  ComfyUI itself only reads the filesystem when you launch the application or
when you manually reload custom nodes; it does not maintain a historical record
of models or downloads.  The new watcher complements ComfyUI by providing the
continuous inventory you described, especially for folders like `~/Downloads`
where models and custom nodes are staged before installation.
