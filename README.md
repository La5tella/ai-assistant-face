# ai-assistant-face

`ai-assistant-face` is a Python prototype for rendering a simple animated assistant face with Pygame. The project builds a small pool of polygon-based face objects, drives their expressions from JSON data, and accepts local command messages that can change expressions or trigger mouth animation.

The current face is data-driven: expression state comes from `dataLibrary/expressions.json`, reusable animation actions come from `dataLibrary/anims.json`, and mouth/viseme shapes come from `dataLibrary/mouth_shapes.json`.

## Project Layout

```text
Scripts/
  MainLoop.py                         Main Pygame entry point and frame loop.
  aiIntegration/
    CommandClient.py                  Sends newline-delimited JSON commands to the renderer.
    CommandListener.py                Local TCP listener used by the renderer.
    ElevenLabsClient.py               Converts text/audio alignment into mouth-shape timing commands.
    LLMAgentClient.py                 Early integration sketch for LLM/TTS/command flow.
  clientSideDebugger/
    llm_response_debugger.py          Tkinter debug client for sending expression and speech commands.
  display/
    FaceScene.py                      High-level scene and expression coordinator.
    Geometry.py                       Face object, transform, vertex, and shape-orientation logic.
    MouthManager.py                   Speech syllable queue and mouth-shape playback.
    Renderer.py                       Pygame display setup and CRT overlay pass.
    RendererContract.py               Drawable mesh data contract.
    UI.py                             Small Pygame button helper.
dataLibrary/
  anims.json                          Named animation action sequences.
  expressions.json                    Named face expression states.
  mouth_shapes.json                   Mouth shape, animation, and hold-scale data.
referenceImages/                      Visual reference material.
TODO.txt                              Current project notes.
```

## Runtime Overview

`Scripts/MainLoop.py` is the application entry point. It creates a `Renderer`, loads the JSON libraries, builds a `FaceScene`, applies the default expression, starts a local command listener, then runs the Pygame frame loop.

Each frame:

1. Pygame events are read.
2. Queued local commands are drained from the TCP listener.
3. `FaceScene.update(dt)` advances active objects.
4. Active objects are converted to drawable meshes.
5. Meshes are drawn with `pygame.draw.polygon`.
6. Debug UI buttons are drawn.
7. The renderer applies a CRT overlay before `pygame.display.flip()`.

The mouth is currently owned by `objects[0]` in `FaceScene`. `MouthManager` activates that object during speech, pulls syllables from its queue, applies the matching shape from `mouth_shapes.json`, and assigns a one-action animation payload to the mouth object.

## Commands

The renderer starts a local TCP listener on `127.0.0.1:6001`. Commands are newline-delimited JSON objects.

Supported command types:

```json
{"type": "expression", "name": "happy"}
{"type": "speak", "syllables": [["a", 0.22], ["m", 0.12]]}
{"type": "stop_speech"}
```

`CommandClient.send_commands()` can be used by tests, debug tools, or external scripts to send those commands to the running renderer.

## Debug Client

`Scripts/clientSideDebugger/llm_response_debugger.py` provides a Tkinter GUI for sending expression and speech commands to the renderer. It can run against the local listener and can use the debug ElevenLabs path to generate sample mouth timing data without making an external TTS request.

## ElevenLabs Alignment Path

`Scripts/aiIntegration/ElevenLabsClient.py` contains the text-to-speech alignment helper. Its main job is to convert character timing data into the mouth shape names used by `mouth_shapes.json`.

The mapper is intentionally rough. It maps characters into the currently available mouth shapes:

```text
a, d, e, f, m, o, r, s, wo, neutral
```

The generated speak payload has this shape:

```json
{"type": "speak", "syllables": [["e", 0.1], ["d", 0.3]]}
```

Audio playback is not implemented in the renderer yet. `create_speak_command()` returns a `play` command alongside the `speak` command, but `MainLoop.py` currently handles expression, speak, and stop-speech commands only.

## Data Files

`expressions.json` defines named face states such as `neutral`, `happy`, and `sad`. Each expression can set object transforms, active state, shape state, and animation name.

`anims.json` defines named animation queues. The current implemented animation actions are:

```text
static
hover
blink
look
```

`mouth_shapes.json` defines viseme-like mouth presets. Each entry provides a target shape state, scale, animation settings, and hold-scale values used by the mouth hold motion.

## Environment Libraries

Use Python 3.10 or newer. The code uses modern type syntax and `match` statements.

Required third-party libraries:

```text
pygame
elevenlabs
```

Standard library modules used by the project include:

```text
dataclasses
json
math
pathlib
queue
socket
threading
time
tkinter
typing
```

`tkinter` ships with many Python installs, but some minimal Python distributions require it to be installed separately through the operating system or Python distribution.

## Running

Start the renderer:

```powershell
python Scripts\MainLoop.py
```

Start the debug command client in a separate terminal:

```powershell
python Scripts\clientSideDebugger\llm_response_debugger.py
```

The renderer window includes two debug buttons:

```text
Cycle State
Toggle Mouth
```

## Current Limitations

- Scene object roles are hardcoded in places; the mouth is assumed to be `objects[0]`.
- Several expression states and animation names exist as placeholders or partial implementations.
- The local command listener validates command shape only lightly.
- The renderer does not currently play audio.
- The early `RossbotAgentClient` class sketches an intended LLM/TTS/command pipeline but is not wired into the main runtime.
- Expression transitions, richer dialogue testing, and smoother mouth activation/deactivation are still listed as project TODOs.

## License

This repository includes a `LICENSE` file. See that file for the full license text.

## Disclaimer about the use of Generative AI

This project was coded and designed by @La5tella. Generative AI was used to code one off systems, such as the debugger client, used for general code debugging and suggestions, and to write summarizing documentation. This was not *vibe coded*. I use AI as a tool, not a crutch! ;)
