## Skretch — CTF Writeup

> *"If only I could lay my eyes on that flag, that beautiful flag, one more time."*

---

### Overview

The challenge delivered a `.sb3.zstd` file — a zstd-compressed Scratch project. Opening it revealed a single sprite carrying **1,786,279 blocks** and one suspiciously named list. The scale was clearly theatrical, designed to discourage any manual or emulation-based approach. The real challenge was algebraic, not visual.

---

### Reconnaissance

After decompressing the `.zstd` container and unzipping the resulting `.sb3` archive, `project.json` exposed two targets: a Stage and the oversized sprite. Initial surface-level inspection covered the obvious bases:

- Searching for a literal flag string → nothing.
- Looking for a costume named `flag` or an embedded PNG → nothing.
- Treating the block graph as animation logic → immediately too expensive and structurally irrelevant.

The block count was noise. The signal was in the **numeric behavior** of the accumulator.

---

### The Pivot

Two named objects in the project were the real focus:

| Object | Role |
|---|---|
| `goodbye now, a sorrow in you` | Accumulator variable |
| `enwrap 330 times in long swaths of frozen blood` | Large input list |

Every `change [accumulator] by` operation in the sprite script was a **linear function of bytes read from the list**. Once framed that way, the 1.7 million blocks collapsed into a structured system of equations.

---

### Solution Path

**1. Extract and parse**
Decompress `.sb3.zstd` → unzip `.sb3` → parse `project.json` directly.

**2. Build a Scratch-accurate symbolic evaluator**
Implemented a symbolic evaluator for the opcode subset in use: arithmetic, string joins, comparisons, list access, and math operations. Scratch's coercion rules — string-to-number conversion, rounding behavior, and comparison semantics — were matched exactly to avoid silent divergence.

**3. Extract linear constraints**
Each `change-by` block became a constraint over bytes from the input list. Collecting all constraints produced a **tridiagonal system**, with a small separate set of boundary equations.

**4. Identify the two free variables**
The tridiagonal structure meant the entire system was determined by exactly **two seed bytes** at positions 1 and 2.

**5. Brute-force the seed space**
Iterated all 256 × 256 = 65,536 seed pairs. For each candidate, the recurrence was propagated across the full row set. Candidates were rejected if any intermediate value fell outside the valid byte range or violated the boundary equations.

**6. Undo the final obfuscation**
Once the hidden sequence `found[]` was recovered, the final layer was a simple modular subtraction:

```python
raw = bytes((found[i] - i) % 256 for i in range(1, len(found)))

out = PROJECT.with_name("skretch_recovered.png")
out.write_bytes(raw)

print("rows     ", len(rows))
print("seed     ", found[1], found[2])
print("signature", raw[:16])
```

The first 16 bytes of output matched a valid PNG signature, confirming a clean recovery.

---

### Result

The reconstructed byte stream rendered as a PNG — a real embedded asset, not noise. The flag was inside.

---

### Takeaway

The 1.7 million blocks were a psychological barrier, not a technical one. Strip away the Scratch scaffolding and what remained was a **linear recurrence with two free variables** — fully solvable by brute-forcing a 256² seed space and propagating forward. The challenge was less about Scratch internals and more about recognizing the underlying algebraic structure early enough to avoid every expensive dead end.
<img width="300" height="300" alt="skretch_recovered" src="https://github.com/user-attachments/assets/b56ad193-f6a1-43f5-b97a-8a77c0ad5715" />

### Flag
`gigem{g00d_k1tty_4nd_thx_7hom4s}`

