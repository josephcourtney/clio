# 🧩 clio — Command-Line I/O for Python Functions

**clio** is a flexible Python utility that connects your plain Python functions to powerful command-line interfaces — with automatic support for multiple input and output types.

Whether you're building a CLI tool, script, or microservice, `clio` helps you handle input from:

- 📂 files
- 📥 stdin/pipe
- 🧠 clipboard
- 📡 environment variables
- ⌨️ command-line arguments
- 🔔 POSIX signals

And output to:

- 📝 files
- 📤 stdout/pipe
- 🧠 clipboard
- 📡 environment variables

---

## 🚀 Installation

```bash
pip install clio
```

Or if you're hacking locally:

```bash
git clone https://github.com/josephcourtney/clio.git
cd clio
pip install -e .
```

---

## ✨ Key Features

- 🔄 Auto-convert input to: `str`, `bytes`, `Path`, `TextIO`, `BufferedIO`
- 🚀 Route output from any Python type to any CLI sink
- 🔀 Supports pipe-based workflows (stdin/stdout)
- 🧪 100% matrix-tested input/output behavior
- 📋 Clipboard support (via `pyperclip`)
- ⚡ Signal-based triggers (e.g. wait for `SIGUSR1` to continue)

---

## 🧠 Example: Connect Python to CLI

```python
from clio.input import get_input
from clio.output import write_output

data = get_input("env", name="MY_INPUT", as_type="str")
# do something...
write_output(data.upper(), dest="file", name="output.txt")
```

Now run:

```bash
export MY_INPUT="hello from env"
python myscript.py
cat output.txt
# → HELLO FROM ENV
```

---

## 🛠 Input Sources

Use `get_input(source, *, name=..., as_type=...)` with:

| Source        | `name`              | Notes                  |
| ------------- | ------------------- | ---------------------- |
| `"env"`       | env var name        | Value or file path     |
| `"arg"`       | CLI arg index       | As string or file path |
| `"file"`      | path to file        | Reads the file         |
| `"pipe"`      | none                | Reads from stdin       |
| `"clipboard"` | none                | Uses system clipboard  |
| `"signal"`    | POSIX signal number | Waits until received   |

---

## 📤 Output Destinations

Use `write_output(data, dest=..., name=...)` with:

| Destination   | `name` required? | Behavior                  |
| ------------- | ---------------- | ------------------------- |
| `"file"`      | ✅ filename      | Writes content            |
| `"pipe"`      | ❌               | Writes to stdout          |
| `"env"`       | ✅ var name      | Sets environment variable |
| `"clipboard"` | ❌               | Copies to clipboard       |

---

## 🧪 Example CLI Integration

```python
import argparse
from clio.input import get_input
from clio.output import write_output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", help="Path or env var name")
    parser.add_argument("--outfile", help="Where to write result")
    args = parser.parse_args()

    data = get_input("env", name=args.infile, as_type="str")
    result = data.upper()
    write_output(result, dest="file", name=args.outfile)
```

Run it:

```bash
export DATA_PATH="myfile.txt"
python script.py --infile DATA_PATH --outfile result.txt
```

---

## 🧩 Example: Using `@command_with_io` Decorator

You can simplify CLI creation by decorating your function with `@command_with_io`.

```python
from clio.click_utils import command_with_io

@command_with_io
def shout(text: str) -> str:
    """Receives input and returns it uppercased."""
    return text.upper()
```

Save it as `shout.py` and run:

```bash
echo "hello from stdin" | python shout.py
# → HELLO FROM STDIN
```

Or use other sources:

```bash
export MESSAGE="hello from env"
python shout.py --input-source env --input-name MESSAGE
# → HELLO FROM ENV
```

---

## 🔧 Tip: Customize Your CLI

- Add more CLI flags via `click` decorators above `@command_with_io`
- The decorator supports all clio I/O options automatically
