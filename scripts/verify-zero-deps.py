#!/usr/bin/env python3
"""Verify zero external dependencies in doctor.py via AST scan.

Walks the AST of scripts/doctor.py and asserts that every import resolves
to a Python standard-library module. Fails (exit 1) if any third-party
import is found, or if any import cannot be resolved.

Stdlib membership is determined against a curated set of stdlib module names
(valid for Python 3.11+). Relative imports and __future__ are allowed.

Usage:
    python3 scripts/verify-zero-deps.py
"""
import ast
import sys
import os

# Python 3.11+ stdlib top-level module names.
# Source: sys.stdlib_module_names (available 3.10+), curated to remove
# deprecated/removed modules. This is intentionally a superset-safe list.
STDLIB_TOP_LEVELS = {
    "__future__", "_thread", "abc", "aifc", "argparse", "array", "ast",
    "asynchat", "asyncio", "asyncore", "atexit", "audioop", "base64",
    "bdb", "binascii", "binhex", "bisect", "builtins", "bz2", "calendar",
    "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "codeop",
    "collections", "colorsys", "compileall", "concurrent", "configparser",
    "contextlib", "contextvars", "copy", "copyreg", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "ensurepip", "enum", "errno", "faulthandler", "fcntl", "filecmp",
    "fileinput", "fnmatch", "formatter", "fractions", "ftplib",
    "functools", "gc", "genericpath", "getopt", "getpass", "gettext",
    "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac", "html",
    "http", "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
    "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
    "marshal", "math", "mimetypes", "mmap", "modulefinder", "msilib",
    "msvcrt", "multiprocessing", "netrc", "nis", "nntplib", "ntpath",
    "numbers", "opcode", "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
    "platform", "plistlib", "poplib", "posix", "posixpath", "pow", "pprint",
    "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
    "pydoc_data", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtpd",
    "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
    "sre_compile", "sre_constants", "sre_parse", "ssl", "stat", "statistics",
    "string", "stringprep", "struct", "subprocess", "sunau", "symbol",
    "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
    "telnetlib", "tempfile", "termios", "test", "textwrap", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "tomllib", "trace",
    "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types",
    "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
    "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
}


def get_imports(source: str, filename: str = "<source>"):
    """Yield (module_name, lineno) for every import in the source."""
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                yield (top, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Relative import — always allowed (within-package).
                continue
            if node.module is None:
                continue
            top = node.module.split(".")[0]
            yield (top, node.lineno)


def verify_file(path: str) -> list:
    """Return a list of (module, lineno) tuples for non-stdlib imports."""
    with open(path) as f:
        source = f.read()
    violations = []
    for module, lineno in get_imports(source, path):
        if module not in STDLIB_TOP_LEVELS:
            violations.append((module, lineno))
    return violations


def main():
    # The file under test: the single-file doctor.
    target = os.path.join(os.path.dirname(__file__), "doctor.py")
    if not os.path.exists(target):
        print(f"ERROR: {target} not found", file=sys.stderr)
        return 2

    violations = verify_file(target)
    if not violations:
        print(f"OK: {target} imports only stdlib modules (zero external dependencies).")
        return 0

    print(f"FAIL: {target} has non-stdlib imports:", file=sys.stderr)
    for module, lineno in violations:
        print(f"  line {lineno}: {module}", file=sys.stderr)
    print("\nThis violates the zero-dependency constraint.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
