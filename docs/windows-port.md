# Native Windows port — investigation

**Question:** can we ship a native Windows bundle of the game the way
`release.yml` ships Linux/macOS bundles?

**Answer today:** no. The blocker is not the game (it is portable `.brainrot`
and PNG/OGG assets) — it is the **`brainrot` interpreter**, which has no native
Windows build. This is why `release.yml` has no `windows` matrix entry and why
`Brainrotlang/brainrot`'s own `release.yml` explicitly omits Windows. This doc
scopes what the port actually takes, based on reading the interpreter source.

## The POSIX surface (what actually blocks Windows)

The surface is smaller and more contained than "it's all POSIX" suggests — it
is four spots, not a rewrite:

| # | Where | POSIX thing | Windows equivalent | Notes |
|---|-------|-------------|--------------------|-------|
| 1 | `stdrot.c` | `dlopen("libstdrot.so")` to load core builtins | — | **Already solved.** See "The big one" below. |
| 2 | `stdrot/registry.c` + `lib/module_path.c` | `dlopen`/`dlsym` + hardcoded `.so` for `#cooked <name>` native modules | `LoadLibraryW` / `GetProcAddress`, `.dll` | **This is the real work for THIS game** — raylib is a native module. |
| 3 | `lib/module_path.c` | `libgen.h` (`dirname`/`basename`), `sys/stat.h`, `unistd.h`, `/` separators | `_splitpath_s`, `GetFileAttributes`, `\` | Path plumbing; mechanical. |
| 4 | `stdrot/ragequit.c` | `sleep()` from `<unistd.h>` | `Sleep()` (millis) | One-line shim. |

Everything else (lexer, parser, AST, semantic analyzer, tree-walking
interpreter) is portable C.

### The big one is already half-done: `STDROT_STATIC`

The interpreter's hardest Windows blocker — dlopen'ing `libstdrot.so` at
startup — already has a compile-time escape hatch. The **wasm** build defines
`-DSTDROT_STATIC` (`make wasm`, `Makefile`), which compiles every builtin
directly into the binary instead of loading a `.so`. Under `STDROT_STATIC`:

- `stdrot.c` skips the `dlopen`/`dlfcn.h` path entirely (`#ifndef STDROT_STATIC`).
- `lib/module_path.c` compiles out the native-`.so` resolver (`#ifndef STDROT_STATIC`).

So a `STDROT_STATIC` Windows build of the interpreter would **run pure-Brainrot
programs natively today** with only items #3 and #4 above (path helpers + the
`sleep` shim) to fix. That is a genuinely small port.

### But this game needs item #2

`STDROT_STATIC` removes dynamic module loading — which is exactly what
`#cooked <raylib>` relies on. So a static Windows interpreter runs the test
suite and pure-logic `.brainrot` but **cannot load raylib**, i.e. cannot run
the game. To run *this* game on Windows you need one of:

- **(A) Win32 native-module loading.** Teach `registry.c` + `module_path.c` to
  `LoadLibraryW`/`GetProcAddress` a `raylib.dll` (raylib builds cleanly on
  Windows via MSYS2/MinGW-w64 or MSVC). This is the general, correct fix — it
  unlocks *any* future native module on Windows, not just raylib.
- **(B) Bake raylib into a special static interpreter.** Skip the loader work
  by statically linking rayrot + raylib into a bespoke `brainrot.exe`. Faster
  to a demo, but a one-off that doesn't generalize and forks the build.

Recommend **(A)** — it is the same capability the Linux/macOS bundles already
depend on, just with the Win32 loader calls behind the existing seam.

## Build toolchain on Windows

The interpreter is C + Flex + Bison. The realistic CI path is **MSYS2 /
MinGW-w64** (`gcc`, `flex`, `bison`, `make`, and a `raylib` package all exist
there), runnable on a `windows-latest` GitHub runner. `-fsanitize=address,
undefined` support is thin on Windows — fine, since `make release` already
builds sanitizer-free. `.so` output names become `.dll`; the Makefile needs a
platform branch for that and for the `-rpath` flags (Windows resolves DLLs from
the executable's directory, so a bundle with everything side-by-side needs no
rpath fixup at all — simpler than Linux/macOS).

## Staged plan

1. **Upstream, interpreter core (`Brainrotlang/brainrot`).** Add a Windows/
   MinGW branch to the Makefile; fix `lib/module_path.c` path helpers (#3) and
   the `ragequit` `sleep` shim (#4); get a `STDROT_STATIC` `brainrot.exe`
   passing the test suite on a `windows-latest` runner. *Deliverable: pure
   Brainrot runs natively on Windows.*
2. **Upstream, native modules (#2).** Add `LoadLibraryW`/`GetProcAddress` +
   `.dll` resolution behind the existing `registry.c`/`module_path.c` seam.
   Build `raylib.dll` in CI. *Deliverable: `#cooked <raylib>` works on Windows.*
3. **Here (game).** Add a `windows/amd64` entry to `release.yml`'s matrix,
   swap `.so`→`.dll` and drop the rpath step for that leg, ship a `play.bat`
   (or keep `play.sh` for the MSYS2 shell). *Deliverable: Windows bundle.*

Steps 1–2 are upstream and gate everything; step 3 here is small once they land.
Until then, the honest Windows story is **WSL** (run the Linux bundle), which
needs no code changes but is not a native app.
