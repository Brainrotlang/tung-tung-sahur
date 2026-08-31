# Native Windows port — investigation

> **Status: DONE.** All three stages below landed upstream in
> `Brainrotlang/brainrot` (#337 stages 1–3, plus #342 for the raylib module),
> and `release.yml`'s `windows-native` job now ships a real
> `tung-tung-sahur-<tag>-windows-amd64.zip`. The WSL stopgap has been removed.
> The rest of this doc is kept as the record of what the port took and why.

**Question:** can we ship a native Windows bundle of the game the way
`release.yml` ships Linux/macOS bundles?

**Answer (now yes; originally no).** The blocker was never the game (it is
portable `.brainrot` and PNG/OGG assets) — it was the **`brainrot` interpreter**,
which had no native Windows build. That has since been implemented upstream
(see the status note above), so `release.yml` now has a `windows-native` job.
This doc scopes what the port took, based on reading the interpreter source.

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

## Staged plan — as executed

1. **Upstream, interpreter core (`Brainrotlang/brainrot` #337 Stage 1).** ✅
   A Windows/MinGW branch in the Makefile (`make windows`), portable
   `lib/module_path.c` path helpers and the `ragequit` `sleep` shim, and a
   `STDROT_STATIC` `brainrot.exe` smoke-tested on a `windows-latest` runner.
   *Pure Brainrot runs natively on Windows.*
2. **Upstream, native modules (`brainrot` #337 Stage 2, + #342).** ✅
   `LoadLibraryA`/`GetProcAddress` + `.dll` resolution behind the existing
   `stdrot.c`/`lib/module_path.c` seam (guarded by `MODULE_NATIVE_LOADER`), and
   `make rayrot` now emits `raylib.dll` on Windows (#342). *`#cooked <raylib>`
   works on Windows.*
3. **Here (game).** ✅ `release.yml`'s `windows-native` job builds
   `brainrot.exe` + `raylib.dll` under MSYS2, vendors `libraylib.dll` (+ any
   MinGW runtime DLLs), and ships a `.zip` with a `play.bat`. No rpath step is
   needed — Windows resolves a DLL from the loading binary's own directory.

The self-contained `brainrot.exe` (`-static`) also means, unlike the Linux/macOS
bundles, there is no `libstdrot.so` to carry — the core standard library is
compiled in; only the raylib module and its `libraylib.dll` are separate files.
