```markdown
# ASCII Tinkerbell

A 3D ASCII animation of Tinkerbell rendered in Python with Pygame and NumPy.

A lotus flower opens from a bud, Tinkerbell flies out with a golden wand trail and color-shifting wings, and at the end of the 28-second loop she returns inside as the petals close.

## Requirements

- Python 3.9+
- `numpy`
- `pygame`

Install dependencies:

```bash
pip install numpy pygame

```

## Usage

```bash
python fairy.py

```

## Controls

* `Space` — Pause / resume
* `R` — Restart animation
* `S` — Save a PNG screenshot in the script directory
* `Esc` — Quit

## How it works

All geometry (flower petals, body, dress, wings, and particle trails) is generated procedurally in 3D, projected onto a character grid with depth buffering, shaded by surface normals into ASCII density pools, and finished with motion trails and a two-pass bloom effect.

```

```
