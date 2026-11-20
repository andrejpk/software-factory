# BRD: `tally`, a tiny word-count CLI

## Business problem

Writers on the team want a quick way to see how long a text file is and which words they overuse,
without installing anything beyond Python.

## Users

Team members who run Python 3.12 on Windows, macOS or Linux.

## Scope

* FR-1: `python -m tally FILE` prints three lines: `lines: N`, `words: N`, `chars: N` for the file.
  Words are whitespace-separated tokens. Exit code 2 with a clear message if the file does not exist.
* FR-2: `python -m tally FILE --top N` additionally prints the N most frequent words
  (case-insensitive, punctuation stripped from word edges) as `word: count`, highest first,
  ties broken alphabetically. `--top` requires an integer >= 1.

## Out of scope

Packaging to PyPI, directories, stdin, non-UTF-8 files, a GUI.

## Acceptance criteria

* AC-1: Running FR-1 on a file containing `a b\nc\n` prints `lines: 2`, `words: 3`, `chars: 6`.
* AC-2: A missing file exits with code 2 and prints an error to stderr.
* AC-3: `--top 2` on `The cat. the dog, THE cat` prints `the: 3` then `cat: 2`.
* AC-4: Tests run with `pytest` in a GitHub Actions workflow named `CI` on every pull request.

## Constraints

Python 3.12 standard library only (pytest for tests). Source in `tally/`, tests in `tests/`.

## Open questions

None.
