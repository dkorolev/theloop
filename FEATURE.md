# Feature: Division Math Invariant Example

## Summary

Add a `divide` example to `example/math/` that follows the same directory-invariant pattern as the existing `add`, `subtract`, and `multiply` examples. The directory holds three numeric text files (`a.txt`, `b.txt`, `c.txt`) and a `DIVIDE-INVARIANT.md` file describing the constraint that `c` must equal `a` divided by `b`, with `b` forbidden from being zero.

## Rationale

The `add`, `subtract`, and `multiply` examples demonstrate that directory invariants can encode mathematical relationships between files. Division is the natural fourth arithmetic operation, but unlike the other three it is a partial function — undefined when the divisor is zero. The simplest invariant-friendly approach is to make `b = 0` a violation of the invariant (rather than defining a sentinel value for the undefined case), keeping the invariant statement clean and unambiguous.

## Implementation Outline

1. **`example/math/divide/DIVIDE-INVARIANT.md`** — human-readable invariant definition; specifies the three-file constraint and explicitly states that `b.txt` must not contain `0`.
2. **`example/math/divide/a.txt`** — dividend; initial value `10`.
3. **`example/math/divide/b.txt`** — divisor; initial value `5` (non-zero by construction).
4. **`example/math/divide/c.txt`** — quotient; initial value `2` (= 10 / 5).
5. **`ai-invariants.yml`** — extended to include the path `example/math/divide/DIVIDE-INVARIANT.md` so the pre-commit harness picks up the new invariant automatically.

## How to Rebuild

To reconstruct this feature from scratch:

- Create directory `example/math/divide/`.
- Write `DIVIDE-INVARIANT.md` with the text:
  > This directory must contain exactly three files: `a.txt`, `b.txt`, and `c.txt`. Each file must contain a single number. The value in `b.txt` must not be zero. The value in `c.txt` must equal the value in `a.txt` divided by the value in `b.txt`.
- Write `a.txt` containing `10`, `b.txt` containing `5`, `c.txt` containing `2`.
- Append `- example/math/divide/DIVIDE-INVARIANT.md` to `ai-invariants.yml`.

A correct implementation satisfies: `c == a / b` for whatever numeric values are stored, with `b != 0` enforced as a hard invariant violation.
