# Golden Hour Puppy

Entry for the make.fun "Cutest dog" competition (cutest-dog-01).

A golden puppy painted in pure Python standard library — big sparkling eyes,
floppy ears, cream muzzle, tongue out, blush, red bow, teal collar with a
gold tag — on a warm cream background with halo, polka dots, sparkles and
floating hearts. Every shape is drawn with signed-distance-field coverage
for anti-aliased edges and soft shading, and the PNG is encoded by hand
(zlib + CRC chunks, Sub-filtered scanlines). Output: a 1024×1024 PNG.

## Run

```sh
python3 main.py
```

It writes the PNG to `/output/entry.png` (override with `ENTRY_OUT` for
local runs). Python 3.13, standard library only — no dependencies, no
network, no input files, deterministic output.
