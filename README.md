# Fog-of-War-Chess-Assistant
An assistant for fog of war chess.
### A fork of [Fog-of-War-Chess-Assistant](https://github.com/Maggiebat/Fog-of-War-Chess-Assistant)

## Windows

1. Install Python 3.10 or later with Tkinter.
2. Put the [Fairy-Stockfish 14 Windows executable](https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_14/fairy-stockfish_x86-64-bmi2.exe) in the project directory.
3. Open a terminal in the project directory and run:

   ```powershell
   python -m pip install -r requirements.txt
   python main.py
   ```

## macOS (Apple Silicon)

1. Install Python 3.10 or later with Tkinter and run these commands in the project directory:

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

2. Download the [Fairy-Stockfish 14 source](https://github.com/fairy-stockfish/Fairy-Stockfish/tree/fairy_sf_14).
   With the Xcode Command Line Tools installed, run
   `make -j4 build ARCH=apple-silicon COMP=clang nnue=no` in the engine's `src` directory.
   If Apple Clang rejects `-fexperimental-new-pass-manager`, remove that flag
   from the engine's Makefile and rebuild. This build uses classical evaluation.
   Copy the resulting `src/stockfish` executable to `bin/fairy-stockfish` in this project.
3. Double-click `Launch Game.command`, or run `./"Launch Game.command"` in the terminal.

On either platform, set `FAIRY_STOCKFISH_PATH` to use a specific engine, or put
`fairy-stockfish` (`fairy-stockfish.exe` on Windows) on PATH.

Choose **Play Game**, enter both player names (blank uses defaults), and choose
**No** at the bias prompt to start a game without custom biases.
