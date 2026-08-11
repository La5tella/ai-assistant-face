# ai-assistant-face

`ai-assistant-face` is a Python/Pygame prototype for rendering an animated assistant face from polygon meshes. A fixed pool of reusable `FaceObject` instances is driven by JSON-defined display modes, expressions, ambient animations, and mouth shapes. Local TCP commands can change the face mode, change its expression, move its gaze, drive lip sync, and play generated audio.

The current state model separates two concerns:

- `dataLibrary/face_states.json` decides which semantic roles are visible, where they are placed, and which controller owns them.
- `dataLibrary/expressions.json` decides how the normal mouth and eyes look by setting their shape, scale, and rotation.

That split allows the thinking state to temporarily reuse the two eye objects as the first two dots in a three-dot indicator. `ThinkingManager` owns those objects until another face state restores the normal face.

## Project Layout

```text
Scripts/
  MainLoop.py                         Pygame entry point, command dispatch, and frame loop.
  aiIntegration/
    AudioPlayer.py                    Plays base64-encoded MP3 audio through pygame.mixer.
    CommandClient.py                  Sends newline-delimited JSON commands to the renderer.
    CommandListener.py                Local TCP listener used by the renderer.
    ElevenLabsClient.py               Produces audio and mouth-shape timing commands.
    LLMAgentClient.py                 Early integration sketch for LLM/TTS/command flow.
  clientSideDebugger/
    llm_response_debugger.py          Tkinter client for expression, speech, and voice testing.
  display/
    FaceScene.py                      Applies expressions and face states across the object pool.
    ThinkingManager.py                Owns and staggers the temporary thinking dots.
    Geometry.py                       Face objects, transforms, vertices, and shape transitions.
    MouthManager.py                   Speech queue and mouth-shape playback.
    animation.py                      Reusable object animation actions.
    Renderer.py                       Pygame drawing and post-processing.
    RendererContract.py               Drawable mesh data contract.
    UI.py                             Small Pygame button helper.
dataLibrary/
  face_states.json                    Display modes, role placement, and controller ownership.
  expressions.json                    Named appearance states for mouth and eyes.
  anims.json                          Named ambient animation action queues.
  mouth_shapes.json                   Mouth shapes, timing actions, and hold-scale data.
tests/
  test_default_reset.py               Default-state transition and runtime flush tests.
  test_eye_look.py                    Command and scene-integration tests for gaze movement.
  test_thinking_manager.py            Unit and scene-integration tests for thinking mode.
referenceImages/                      Visual reference material.
TODO.txt                              Current project notes.
```

## Runtime Overview

Run the application from the repository root with:

```powershell
python -m Scripts.MainLoop
```

`Scripts/MainLoop.py` loads `expressions.json`, `anims.json`, and `face_states.json`, creates a five-object `FaceScene`, applies the default expression, applies the default face state, creates the audio player, and starts the local command listener.

The current role map is:

```text
mouth       -> object 0
left_eye    -> object 1
right_eye   -> object 2
dot_left    -> object 1 (reuses the left eye)
dot_middle  -> object 2 (reuses the right eye)
dot_right   -> object 3
```

Object 4 is currently created by `main_loop(5)` but has no assigned role.

Each frame:

1. Pygame events are read.
2. Queued TCP commands are dispatched on the main thread.
3. `FaceScene.update(dt)` advances each active object.
4. Active objects are converted to drawable meshes.
5. `Renderer.draw_drawables()` draws the polygons.
6. Pixelation and the CRT overlay are applied.
7. Debug buttons are drawn and the frame is presented.

## Face States and Expressions

`FaceScene.set_expression()` applies one named entry from `expressions.json`. The current expressions are `neutral` and `happy`. Expression data uses semantic role names and owns:

```text
shape_state
scale
rotation
```

`FaceScene.set_face_state()` applies one named display mode from `face_states.json`. The current modes are `default`, `speaking`, and `thinking`. Face-state data owns:

```text
uses_expression
expression
roles
position
active
controller
ambient_anim
sequence_delay
sequence
```

`default` is a coordinated reset state. It flushes speech and thinking ownership, clears stale animation actions, restores the neutral expression, centers gaze, assigns `eye_neutral`, blends objects back to their authored positions, and shrinks non-default objects before hiding them. When leaving thinking, the hidden mouth starts collapsed at the visible center of the thinking dots and eases both its position and shape into the normal face. The same mouth entry handoff is used for thinking-to-speaking. `speaking` keeps the regular face without forcing a neutral expression. `thinking` sets `uses_expression` to `false`, hides the regular mouth, and transfers three dot roles to `ThinkingManager`.

If an expression command arrives during thinking mode, `FaceScene` remembers its name without applying it. Returning specifically to `default` deliberately replaces that remembered value with `neutral`; another expression-enabled state can still apply the remembered expression.

## Thinking Manager

`ThinkingManager` receives a role-to-object map and the scene's object-state callback. On activation it:

1. validates that every role exists;
2. requires a unique, non-negative integer `sequence` for each dot;
3. strips manager-only `controller` and `sequence` metadata;
4. applies each dot's position, shape, and scale;
5. assigns the named `thinking` animation;
6. delays each dot by `sequence * sequence_delay`.

The default delays are `0.0`, `0.2`, and `0.4` seconds. The `think` action runs a continuous cosine-based hop with a 0.6-second cycle and an 18-pixel amplitude. It never completes on its own. A normal default transition captures the current hop offset before releasing `ThinkingManager`, preventing the dots from snapping before they blend into the normal face.

## Commands

The renderer listens on `127.0.0.1:6001` for newline-delimited JSON objects.

```json
{"type": "expression", "name": "happy"}
{"type": "face_state", "name": "thinking"}
{"type": "face_state", "name": "default", "duration": 0.4, "easing": "ease"}
{"type": "face_state", "name": "default", "debug": "reset"}
{"type": "look", "target": [1.0, -0.5], "duration": 0.25, "easing": "ease"}
{"type": "speak", "syllables": [["a", 0.05, 0.22], ["m", 0.05, 0.12]]}
{"type": "play", "audio": "<base64-encoded MP3>"}
{"type": "stop_speech"}
```

Each speech item is `[mouth_shape, transition_time, total_time]`. `transition_time` controls the move into the new shape; `total_time` is the amount of audio time owned by that item.

Sending `default` normally uses the supplied duration/easing and stops active audio after the scene accepts the state. Adding `"debug": "reset"` makes every reset transition zero-duration for an immediate known-state reset. `stop_speech` only clears the mouth queue and stops the Pygame mixer. `CommandClient.send_commands()` can send commands from tests, debug tools, or external scripts.

Look targets are normalized directions. `[0, 0]` centers the eyes, negative X looks left, positive X looks right, negative Y looks up, and positive Y looks down. The renderer bounds the direction to the unit circle and converts it into a gaze offset equal to 30 percent of the current eye radius. Gaze has its own animation channel, so `eye_neutral` hover/blink actions continue during look transitions in both the `default` and `speaking` face states. Thinking mode owns the reused eye objects and ignores look commands.

## Data Files

### `face_states.json`

Defines display-level modes. A role entry can position and activate an object, select its controller, and attach an ambient animation. The default state also selects its reset expression. The thinking state uses `sequence` and top-level `sequence_delay` to stagger the dots.

`controller: "thinking"` transfers object ownership to `ThinkingManager`; `controller: "eye"` identifies roles eligible for gaze commands. The `mouth` controller string remains descriptive metadata.

### `expressions.json`

Defines the appearance of semantic face roles. Version 2 replaced numeric object keys and nested transform objects with role names and direct `shape_state`, `scale`, and `rotation` fields. Position, visibility, controller selection, and ambient animation now belong in `face_states.json`.

### `anims.json`

Defines named object-animation queues. Configured names are:

```text
default
eye_neutral
thinking
eye_look_left
eye_look_right
anim_test
```

Implemented action names are:

```text
static
hover
blink
look
think
constanant_close
```

`look` lerps a separate gaze offset, allowing it to run concurrently with ambient eye actions. `constanant_close` is the implementation's current misspelled action name and must remain spelled that way in JSON until the code and data are migrated together.

### `mouth_shapes.json`

Defines the current mouth presets:

```text
a, d, e, f, m, o, r, s, wo, neutral, smile, wait
```

Most spoken shapes use `static`; `m` uses `constanant_close`. `MouthManager` augments each action at runtime with transition time, total time, hold settings, and hold speed. `wait` is handled as a timing sentinel before any shape lookup. `smile` remains an incomplete non-speech entry.

## Debug Client

Start the Tkinter debug client from the repository root in a separate terminal:

```powershell
python -m Scripts.clientSideDebugger.llm_response_debugger
```

The debugger has separate Speech, Gaze, and Voice Design tabs. The Gaze tab can send a custom normalized X/Y target with duration and easing, or immediately send any of nine directional presets including Center. The Speech tab includes `Reset Default (No Blend)`, which sends the `debug: "reset"` form. These signals use the same host, port, worker-thread, status, and logging path as the other debugger commands.

## Environment Libraries

Use Python 3.10 or newer. Required third-party libraries are:

```text
pygame
elevenlabs
```

`tkinter` is used by the debugger and is included with many Python installations, although some minimal distributions package it separately.

## Tests

Run the test suite from the repository root:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
```

The suite covers seamless and immediate default resets, manager flushing, mouth entry into default/speaking, placement interpolation, debugger payloads, gaze routing/interpolation, and thinking-manager ownership.

## Current Limitations

- Roles are centralized in `Roles`, but their object indices are still fixed.
- Speech commands do not switch face states automatically; callers must send `speaking` or `default` explicitly.
- Configured roles are forced active after their state is applied, so `active: false` is not currently honored as a general per-role visibility switch.
- `FaceScene` has a `drawables` list and a shadowed `drawables()` method with the same name; the method is dead and assumes the object collection is a dictionary.
- JSON files are not schema-validated, and their version fields are not type-consistent (`2` versus `"2"`).
- The `default` animation entry is a string list rather than an action-dictionary queue and should not be assigned through `FaceObject.curr_anim` in its current form.
- Audio playback depends on Pygame mixer support for the provided in-memory MP3 data.
- Thinking and gaze paths have focused tests, but the broader renderer, speech, command, and data-schema paths do not yet have comprehensive coverage.
- `LLMAgentClient.py` remains an integration sketch rather than part of the running application.

## License

This repository includes a `LICENSE` file. See that file for the full license text.

## Disclaimer about the use of Generative AI

This project was coded and designed by @La5tella. Generative AI was used to code one off systems, such as the debugger client, used for general code debugging and suggestions, and to write summarizing documentation. This was not *vibe coded*. I use AI as a tool, not a crutch! ;)
