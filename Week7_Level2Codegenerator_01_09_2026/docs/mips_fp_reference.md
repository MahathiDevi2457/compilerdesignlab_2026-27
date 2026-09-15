# MIPS Floating-Point Reference (Week 7)

Everything below was verified directly on real SPIM before being written here — floating-point
MIPS conventions have enough sharp edges that "looks right" and "is right" are different claims.

## Two separate register pools

| Pool | Registers | Used for |
|---|---|---|
| Integer | `$t0`–`$t9` | `INT`, `CHAR`, and `STRING` (a string variable holds an *address*, which is just a 4-byte int) |
| Floating-point | `$f0`, `$f2`, `$f4`, ..., `$f30` | `DOUBLE` only |

**Float registers are used in pairs.** MIPS's FPU registers are 32-bit; a `double` (64-bit) is
stored across two consecutive registers, but you always refer to the pair by its *even* index —
`$f0` actually means "the `$f0`/`$f1` pair." `alloc_float()`/`free_float()` handle this for you
(internally tracking 16 "double slots" indexed 0–15, mapped to `$f0, $f2, ..., $f30`) — you
never need to think about the odd half directly.

## Instructions and pseudo-instructions

| Purpose | Integer | Double |
|---|---|---|
| Load immediate | `li reg, N` | `li.d freg, N` (pseudo-instruction — confirmed working directly on SPIM) |
| Load from memory | `lw reg, off($fp)` | `l.d freg, off($fp)` |
| Store to memory | `sw reg, off($fp)` | `s.d freg, off($fp)` |
| Add/Sub/Mul/Div | `add`/`sub`/`mul`/`div` | `add.d`/`sub.d`/`mul.d`/`div.d` |
| Move between registers | `move rd, rs` | `mov.d fd, fs` |
| Move to `$a0`/`$f12` for print | `move $a0, reg` | `mov.d $f12, freg` |

`mul`/`div` (int) are the same 3-operand pseudo-instructions from Week 4, unaffected by this
week's changes.

## int ↔ double conversion

Converting between families needs the FPU's *move* instructions (`mtc1`/`mfc1`, moving bits
between an integer register and an FPU register with no numeric interpretation) combined with
its *convert* instructions (`cvt.d.w`/`cvt.w.d`, which do reinterpret the value numerically):

```mips
# int -> double  (source in $t0, result ends up in $f2)
mtc1  $t0, $f0        # move the raw int bits into the FPU
cvt.d.w $f2, $f0      # convert: interpret $f0 as a 32-bit int, produce a double in $f2

# double -> int  (source in $f0, result ends up in $t1, truncating toward zero)
cvt.w.d $f2, $f0      # convert: interpret $f0 as a double, produce a 32-bit int in $f2
mfc1  $t1, $f2         # move the raw int bits out of the FPU
```

Both directions need a **scratch FPU register** (`$f0`/`$f2` above) as an intermediate step —
you cannot `mtc1` directly into the register you'll later read the converted value from in one
step; the move and the convert are always two separate instructions.

## Comparing doubles: no direct "set on condition," always a branch

MIPS integers have `slt`/`blt`/etc. that work directly. The FPU has no equivalent — comparison
is always two steps: a `c.<cond>.d` instruction that sets an internal condition flag, then a
branch (`bc1t` = branch if the flag is *true*, `bc1f` = branch if *false*) to actually act on it.
There is no direct "greater than" or "not equal" FPU compare — only `c.lt.d`, `c.le.d`, `c.eq.d`
exist, and the other three comparisons are synthesized:

| Comparison | How |
|---|---|
| `a < b` | `c.lt.d $fa, $fb` ; `bc1t` |
| `a <= b` | `c.le.d $fa, $fb` ; `bc1t` |
| `a == b` | `c.eq.d $fa, $fb` ; `bc1t` |
| `a > b` | `c.lt.d $fb, $fa` (operands **swapped**) ; `bc1t` |
| `a >= b` | `c.le.d $fb, $fa` (operands **swapped**) ; `bc1t` |
| `a != b` | `c.eq.d $fa, $fb` ; `bc1f` (branch on **false**, i.e. not-equal) |

This asymmetry (int comparisons can materialize a 0/1 value directly via `slt`; double
comparisons always need a branch) is why `RelOpTriple` codegen uses **one uniform branch-based
shape for both types** — see below — rather than a `slt`-based fast path for `int` only. Fewer
distinct patterns to get right, and it's the same shape `Ternary` needs anyway.

## Materializing a comparison's 0/1 result (used by every `RelOpTriple`)

```mips
<condition test for the operand type, from the tables above>
<branch-if-true, to Ltrue>
li  $dest, 0
b   Lend
Ltrue:
li  $dest, 1
Lend:
```
For `int`/`char` operands, `<condition test + branch>` collapses to one instruction — SPIM
provides `blt`/`bgt`/`ble`/`bge`/`beq`/`bne` directly as 3-operand pseudo-ops (confirmed on real
SPIM), no separate compare instruction needed first.

## The ternary operator, fully traced

This is the exact pattern `gen_select()` needs to implement, worked through for
`c = (a > b) ? (double)a/b : (double)b/a;` with `a=40, b=50` (Slide 6's corrected Example 3,
`tests/test6.tc`) — the else-branch is taken, since 40 is not greater than 50:

```mips
# (2): a > b  -- RelOpTriple, INT result, INT operands
blt   $t0, $t1, L1      # NOT taken (40 < 50, so this is NOT "a > b")
li    $t2, 0
b     L0
L1:
li    $t2, 1
L0:
# $t2 now holds 0 (the comparison's result)

# (9): the ternary itself -- SelectTriple, DOUBLE result
                          # dest = $f12 (allocated FIRST, before either branch)
bne   $t2, $zero, L2      # condition is 0 -> NOT taken -> fall through to ELSE
# -- else branch: (double)b/a, already computed in an earlier triple, sitting in $f6 --
mov.d $f12, $f6
b     L3
L2:
# -- then branch: (double)a/b, sitting in $f0 -- NOT executed this run
mov.d $f12, $f0
L3:
# $f12 now holds the else-branch's value: 50.0/40.0 = 1.25
```

Running this on real SPIM prints `1.25` — matching the hand-computed value exactly. **The two
`mov.d`/`move` instructions (one per branch) are not optional** — without them, whichever branch
runs would leave its result in a *different* register depending on which path was taken, and the
code after the ternary (here, storing to `c`) wouldn't know which register to read from.

## Why `dest` must be allocated *before* evaluating either branch

If `gen_select()` allocated `dest` *after* resolving the branches instead, the allocator could
hand out `dest`'s register to something used *while computing* the then/else values — a subtle,
hard-to-reproduce bug that only shows up when register pressure is high enough for the allocator
to pick a colliding register. Allocating `dest` first — before the branches ever run — guarantees
the allocator marks it unavailable for the rest of this triple's processing.

## String literals need a `.data` section again

Frame-based codegen (Week 4 onward) removed `.data` entirely — every variable lives on the
stack. String literals are the one exception: `"hello"` needs to exist *somewhere* in memory
with a real address, since `la` (load address) needs a label to point at. `get_string_label()`
(provided) creates one `.asciiz` entry per *distinct* literal text the first time it's seen,
reusing the same label for repeats — check the golden `.s` files for a program using the same
string twice to see this deduplication in the generated `.data` section.

## Why `char` printing gets a syscall not in the lab plan's own list

The lab plan explicitly lists new syscalls for `double` (`$v0=3`) and `string` (`$v0=4`), but
not `char`. Printing a `char` via the existing int syscall (`$v0=1`) would show its *ordinal
number* (`'x'` → `120`), not the character — which would make `tests/test5.tc`'s
`print c;` (where `c = 'x'`) look wrong when hand-verified against expected output. `$v0=11`
(SPIM's print-character syscall, value in `$a0`) is added here specifically so a `char` prints
as the character itself — a small, well-motivated addition beyond the letter of the lab plan.

## Why `CHAR` is word-aligned (4 bytes), not packed to 1 byte

`SymbolTable.getSizeOfType(CHAR)` returns 4, not 1 — found necessary by actually running
generated code: a 1-byte `char` slot pushes whatever's declared after it onto a
non-word-aligned offset, and SPIM rejects any `lw`/`sw` at a misaligned address outright
("Unaligned address in store/fetch"). Real C would pack a `char` into 1 byte; this course
trades that space efficiency for keeping every load/store this week a plain word-sized
`lw`/`sw`, with no separate byte-addressing (`lb`/`sb`) logic to write on top of everything
else already new this week.
