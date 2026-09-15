# Typed Three-Address Code Reference (Week 7)

## Why triples need types now

Through Week 6, a triple's operands were just names/literals/refs — nothing about a triple
itself said whether it was working with an `int` or a `double`. That was fine while everything
was `int`. Now that `RelOp`/`Cast`/`Ternary` exist and variables can be `double`/`char`/
`string`, `tac_to_mips.py` needs to know, for every single triple, which MIPS instruction
*family* to use — `add` vs `add.d`, `$t` registers vs `$f` register pairs. Rather than
re-deriving this at the MIPS-generation stage, **Week 6's type checker already resolved every
expression's type** — this week just carries that information one step further, onto the
triples themselves.

## Where the type comes from: `node.result_type`

Week 6's `check_expr()` now stamps `node.result_type` on every expression node it returns,
whether that's a bare `Const`, a freshly-inserted `Cast`, or a full `BinOp` subtree. By the time
`tac_generator.py` walks the (already-checked) AST, every node it visits already knows its own
type — nothing needs to be re-inferred. This is why `gen_binop`'s TODO can just read
`node.result_type` directly instead of comparing `node.left`'s and `node.right`'s types itself —
Week 6 already did that comparison and promotion; Week 7 only needs to *act* on the answer.

## The new triple types

| Triple | Carries | Why |
|---|---|---|
| `RelOpTriple(op, arg1, arg2, operand_type)` | the **operands'** type, not the comparison's result type | Comparing two `double`s needs `c.lt.d`, comparing two `int`s needs `blt` — but a comparison's own *value* is always `INT` (0 or 1), regardless of what was compared. Mixing these up is the single easiest mistake this week — see `docs/pitfalls_faq.md`. |
| `CastTriple(source_type, target_type, arg)` | both the type being converted *from* and *to* | `int → double` and `double → int` need completely different instruction sequences (`mtc1`+`cvt.d.w` vs `cvt.w.d`+`mfc1`) — the direction matters, not just the destination type. |
| `SelectTriple(cond, cond_type, then_val, else_val, result_type)` | the condition's type separately from the result's type | Testing whether a `double` condition is truthy needs an FPU comparison against zero; testing an `int` condition just needs `bne $reg, $zero, ...`. The *result* type (which register family holds the final answer) is a separate question from how the condition was tested. |

## Why `Ternary` compiles to ONE triple, not several

It would be reasonable to expect a ternary to become a handful of branch/label/goto triples at
the 3AC level, mirroring what the actual MIPS output looks like. This deliberately does **not**
happen here. `gen_ternary()` builds exactly one `SelectTriple` — the branching only appears once
`tac_to_mips.py`'s `gen_select()` expands it into real MIPS labels and jumps.

This is a deliberate scope boundary, not an oversight: general branch/label 3AC (needed for
`if`/`while`) is Week 8's own subject. Introducing it piecemeal here — just enough for
`Ternary`, in a shape that wouldn't necessarily match what Week 8 designs for `if`/`while` — would
either preempt that week's teaching moment or need to be redesigned later. Keeping the 3AC layer
"one triple per source-level operation" for *everything*, `Ternary` included, means Week 8 can
introduce branch/label 3AC once, cleanly, without Week 7 having already done a smaller,
possibly-incompatible version of it.

## Why string/char `Const` operands are wrapped in quotes

`tac_generator.py`'s `Const` handling returns `f'"{node.value}"'` for a `STRING` constant and
`f"'{node.value}'"` for a `CHAR` constant — quote characters included in the operand text
itself, not just in the source code. This looks unusual next to `Num`/`Const` for `int`/`double`
(plain `"5"`, `"3.14"`, no wrapping) but it's necessary: an `int`/`double` literal's text is
*self-evidently* numeric (`is_literal()`/`literal_kind()` can recognize it by shape alone), but
`"hello"` and `x` (a char's raw value) are indistinguishable from a variable name by inspection
— nothing about the text `hello` says "this is a literal," unlike `3.14`. Wrapping in quotes
gives `tac_to_mips.py`'s `literal_kind()` the same kind of shape-based recognition for strings
and chars that numbers already had for free.

## Golden files

`tests/*.3ac.expected.txt` shows the exact triple-form text for every test program, including
the type annotation each triple carries (`: DOUBLE`, `: cmp INT`, etc.) — useful for confirming
your `tac_generator.py` is choosing the right type for each triple before you even get to
`tac_to_mips.py`.
