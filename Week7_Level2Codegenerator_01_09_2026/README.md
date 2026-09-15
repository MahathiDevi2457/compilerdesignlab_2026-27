# Week 7 — Three-Address Code and MIPS Code Generation for Mixed Types


 **3AC generation** for `RelOp`/`Cast`/`Ternary` (new triple types carrying type information, since a mixed-type program)
 **MIPS generation** for all of it — floating-point registers and instructions, int↔double conversion, and branch-based codegen for both comparisons and the ternary operator. By the end, the full L2 pipeline runs end to end on real SPIM.

## What we're trying to do this week

1. Extend `tac_generator.py`: three new `gen_*` cases (`RelOp`→`RelOpTriple`,
   `Cast`→`CastTriple`, `Ternary`→`SelectTriple`), each carrying the type information Week 6's
   checker already resolved.
2. Extend `tac_to_mips.py`: a second register pool for `double` (`$f0`–`$f30`, even-indexed
   pairs), type-aware `load`/`store`, and per-triple codegen for all three new triple types —
   including implementing the ternary operator as a branch-based MIPS sequence

## Current file contents

### What's already provided (do not modify)

- **`tinycstr_lexer.py`, `tinycstr_parser.py`, `ast_nodes.py`, `Program.py`, `type_rules.py`** —
  unchanged from Week 6.
- **`SymbolTable.py`** — **changed this week**: `CHAR`'s size is now 4 bytes, not 1 — found
  necessary by actually running generated code (a 1-byte `char` misaligns whatever's declared
  after it, and SPIM rejects misaligned `lw`/`sw` outright).
- **`type_checker.py`** — **changed this week**, small addition: `check_expr()` now stamps
  `node.result_type` on every node it returns, not just returning it transiently. This is what
  lets `tac_generator.py` read a node's resolved type directly instead of re-deriving it.
- **`three_address_code.py`** — **changed this week**: `BinOpTriple` gained a `result_type`
  field; two new triple types, `RelOpTriple` and `CastTriple`; one more, `SelectTriple`, for the
  ternary operator — deliberately still a single flat triple at the 3AC level, with branching
  pushed entirely into `tac_to_mips.py`. `is_literal()` is also fixed this week to recognize floating-point
  literals.
- **`Function.py`** — **changed this week**, small: `compile()` now passes the full triple list
  into `MIPSGenerator`, needed to resolve a `TripleRef` operand's type.
- **`main.py`** — `-3ac`/`-compile`  for Level 2 constructs.

### What you need to do

- **`tac_generator.py`** — three TODOs: `gen_relop()`, `gen_cast()`, `gen_ternary()`. Level 1's
  covering (`Assign`/`Print`/`Var`/`Const`/`BinOp`) is complete and marked "do not modify."
- **`tac_to_mips.py`** — the bulk of the week. TODOs: `load()`, `store_to_var()`, `gen_binop()`,
  `gen_relop()`, `gen_cast()`, `gen_select()`, `gen_assign()`, `gen_print()`. Register
  allocation, label generation, string-literal `.data` handling, type resolution, and the
  prologue/epilogue are all provided — your work is entirely instruction *selection*: given an
  already-typed triple, which MIPS instructions does it become?

### Documentation

- **`docs/typed_3ac_reference.md`** — why triples need types now, what each new triple type
  carries and why, and why `Ternary` stays one flat triple instead of branch/label triples.
- **`docs/mips_fp_reference.md`** — the complete MIPS floating-point picture: register pairing,
  every instruction table you need, int↔double conversion, the comparison-synthesis table for
  all six relational operators on doubles, and a fully worked trace of the ternary pattern
  against Example 3's actual numbers — all verified directly on real SPIM before being written
  down.

### Tests

Six programs, all SPIM-verified end-to-end before being shipped as goldens: `test4`–`test7`
(carried over from Weeks 5–6), plus two new ones — `test8.tc` (nested ternary, chained cast) and
`test9.tc` (all six relational operators). `test_errors.tc` (from Week 6) still correctly gates
at the type-check stage, never reaching codegen.

## Step by step

1. Read `docs/typed_3ac_reference.md`, then implement `tac_generator.py`'s three TODOs. Test:
   ```bash
   python main.py -3ac tests/test6.tc
   diff tests/test6.tc.3ac tests/test6.3ac.expected.txt
   ```
2. Read `docs/mips_fp_reference.md` in full — it's long, but every instruction and pattern you
   need is in it, verified.
3. Implement `load()`/`store_to_var()`, then `gen_binop()` — test against `test4.tc` (pure
   int/double, no comparisons/casts/ternary yet) before moving on.
4. Implement `gen_relop()` — test against `test9.tc` (all six operators).
5. Implement `gen_cast()` — test against `test8.tc`'s chained cast.
6. Implement `gen_select()` last — the hardest part. Test against `test6.tc` (Example 3) and
   `test8.tc` (nested ternary).
7. **Run every test program on real SPIM**, not just diff the generated `.s`:
   ```bash
   python main.py -compile tests/test6.tc
   spim -file tests/test6.tc.spim
   ```
   Check the last printed line against `tests/test6.spim_output.expected.txt` (`1.25`). Repeat
   for all six.
8. Take-home: compile and verify `test4`–`test7` end-to-end on SPIM (already covered above, but
   write them up explicitly per the deliverable), and write a short note on one floating-point
   pitfall you personally hit and how you found/fixed it.

## Getting unstuck

If you're still stuck, post in the Week 7 GitHub Issues

