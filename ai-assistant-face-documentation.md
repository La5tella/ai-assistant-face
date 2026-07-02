# AI Assistant Face Documentation

## Summary

`ai-assistant-face` is a Python/Pygame prototype for drawing an animated assistant face from polygon meshes. The program creates a fixed pool of `FaceObject` instances, applies expression data from JSON, updates shape and animation state each frame, and renders active objects as filled polygons.

The current implementation is not just a static face renderer anymore. It now has:

- a Pygame render loop;
- data-driven expressions;
- reusable animation action queues;
- a mouth/viseme playback manager;
- a local TCP command listener;
- a small TCP command client;
- a Tkinter debug sender;
- an ElevenLabs alignment helper that maps text/audio alignment into mouth-shape timing.

It is still a prototype. Audio playback, robust command validation, proper object role mapping, test coverage, and a clean renderer API are not finished.

## Current File Map

```text
Scripts/MainLoop.py
  Application entry point.
  Creates the renderer and face scene.
  Loads expression and animation JSON.
  Starts the local command listener.
  Owns the Pygame event/update/draw loop.

Scripts/display/Renderer.py
  Thin Pygame wrapper.
  Creates the display surface, font list, clock, and CRT overlay.

Scripts/display/RendererContract.py
  Defines DrawableMesh, the data object passed from scene objects to rendering.

Scripts/display/UI.py
  Defines a simple Pygame Button helper for debug controls.

Scripts/display/Geometry.py
  Defines Transform, Vert, and FaceObject.
  Owns polygon shape-state generation, vertex transitions, easing, and object-local animation updates.

Scripts/display/FaceScene.py
  Coordinates expression changes across the object pool.
  Owns the object list and routes the mouth object through MouthManager.

Scripts/display/MouthManager.py
  Loads mouth shape data.
  Converts syllable queues into mouth shape and animation actions.
  Activates/deactivates the mouth object during speech playback.

Scripts/display/animation.py
  Defines Animation.
  Executes action payloads such as static, hover, blink, look, and hold-on-complete mouth motion.

Scripts/aiIntegration/CommandListener.py
  Background TCP server for newline-delimited JSON commands.

Scripts/aiIntegration/CommandClient.py
  Client helper for sending commands to the local listener.

Scripts/aiIntegration/ElevenLabsClient.py
  Text/audio-alignment helper.
  Converts character alignment into mouth-shape timing commands.

Scripts/aiIntegration/LLMAgentClient.py
  Early sketch of an LLM/TTS/command orchestration client.
  Not wired into the running app.

Scripts/clientSideDebugger/llm_response_debugger.py
  Tkinter GUI for sending expression and speech commands to the running renderer.

dataLibrary/expressions.json
  Named expression states.

dataLibrary/anims.json
  Named animation action queues.

dataLibrary/mouth_shapes.json
  Mouth shape, timing, and hold-scale data.
```

## Runtime Flow

The normal runtime starts in `Scripts/MainLoop.py`.

```text
python Scripts\MainLoop.py
  -> Renderer is constructed with a 720x720 resizable Pygame display
  -> dataLibrary/expressions.json is loaded
  -> dataLibrary/anims.json is loaded
  -> FaceScene is created with five FaceObject instances
  -> default expression is applied
  -> local command listener starts on the default host/port
  -> Pygame frame loop begins
```

Each frame:

1. The clock ticks at a 60 FPS target.
2. Pygame events are read.
3. The screen is cleared.
4. Commands from the listener queue are drained and applied.
5. `FaceScene.update(dt)` advances active objects.
6. Active objects are converted into `DrawableMesh` instances.
7. Meshes are drawn with `pygame.draw.polygon`.
8. Debug buttons are drawn and updated.
9. `Renderer.apply_crt()` overlays the CRT effect.
10. `pygame.display.flip()` presents the frame.

`MainLoop.py` now has an `if __name__ == "__main__":` guard. Importing the module should not immediately start the app.

## MainLoop.py

`MainLoop.py` owns global application setup and the live frame loop.

It currently:

- sets `BASE_DIR` from the repository path;
- sets `RESOLUTION` to `[720, 720]`;
- creates `Renderer`;
- loads expression and animation data;
- creates `FaceScene`;
- applies the default expression;
- creates two debug buttons;
- starts `CommandListener`;
- drains queued commands every frame;
- draws scene meshes directly with Pygame;
- applies the renderer CRT overlay.

The two debug buttons are:

```text
Cycle State
Toggle Mouth
```

`Cycle State` cycles active objects through their shape states. `Toggle Mouth` starts the mouth manager with a sample syllable queue.

Command handling currently supports these runtime effects:

```text
expression     -> FaceScene.set_expression(...)
speak          -> MouthManager.activate_speak(...)
stop_speech    -> MouthManager.stfu()
```

The listener accepts a `play` command type, and the ElevenLabs helper can produce one, but `MainLoop.py` does not currently handle audio playback.

## Renderer.py

`Renderer` is still a thin wrapper around Pygame. It stores:

- `RESOLUTION`;
- `OBJBANK`;
- `DISPLAY`;
- `fonts`;
- `screen`;
- `clock`;
- `running`;
- `crt_overlay`.

It creates the Pygame display surface and a default Arial font. It also creates a simple CRT overlay made from scanlines plus a greenish additive fill.

Rendering of face meshes still happens in `MainLoop.py`, not through a renderer draw method. That is workable for a prototype, but it keeps application flow and drawing policy tangled together.

## FaceScene.py

`FaceScene` coordinates high-level expression state across a fixed list of objects.

During construction, it creates `objCount` `FaceObject` instances with:

- object ids from `0` upward;
- default `Circle` shape state;
- cyan color;
- 32 vertices;
- inactive state;
- an initial transform spread across the screen.

The mouth is currently hardcoded as `objects[0]`:

```text
self.mouth_manager = MouthManager(self.objects[0])
```

That is a brittle role assignment. The code works because the current scene is small, but future face parts should use explicit roles or stable ids instead of assuming list index `0` always means mouth.

Expression flow:

```text
handle_ai_command(data)
  -> reads emotion/duration/easing
  -> calls set_expression(...)

set_expression(expression_name, duration, easing)
  -> looks up expression_data["states"][expression_name]
  -> iterates object ids in the expression
  -> calls apply_object_state(...)

apply_object_state(obj, state_data, duration, easing)
  -> applies transform fields to obj.transform
  -> assigns anim to obj.curr_anim
  -> applies remaining fields with setattr()
  -> starts or reapplies the target shape state
```

The broad `setattr()` path is flexible, but it is also weak validation. A misspelled JSON field can create bad runtime state without a clear error.

`FaceScene.update(dt)` rebuilds `self.drawables` each frame. The mouth object is updated through `MouthManager`; other active objects call `FaceObject.update(dt)` directly.

There is also a `drawables()` method in the class, but the instance attribute `self.drawables` uses the same name. That naming collision is not fatal in the current path because the code treats `drawables` as a list, but it is sloppy and should be cleaned up.

## Geometry.py

`Geometry.py` owns the mesh object model.

### Transform

`Transform` is a dataclass with:

```text
origin_position
scale
rotation
rotation_radians
```

`rotation` is stored in degrees. `rotation_radians` converts it for math functions.

### Vert

`Vert` is a dataclass with:

```text
local_position
target_position
```

Vertices are stored in object-local coordinates. `FaceObject.local_to_screen()` adds the object origin and animation offset when generating drawable screen points.

### FaceObject

`FaceObject` stores:

- id;
- active state;
- layer;
- color;
- transform;
- opacity;
- aspect ratio;
- vertex count;
- vertex list;
- shape-state transition timing;
- debug flag;
- current animation name;
- animation action queue;
- animation offset;
- `Animation` instance.

Supported shape states:

```text
Circle
Square
Rectangle
Triangle
Half-Circle
```

Shape-state methods:

```text
circleOrient()
halfCircleOrient()
rectangleOrient()
triangleOrient()
orientVertsAlongPolygon()
set_shape_state()
apply_shape_state()
update_shape_state()
```

`set_shape_state()` recalculates target positions. If the duration is `0`, the vertices snap to the targets. Otherwise, `update_shape_state()` interpolates `local_position` toward `target_position` using the configured easing curve.

Supported easing names:

```text
linear
ease-in
ease-out
ease
```

`ease` is smoothstep.

`to_drawable()` returns a `DrawableMesh` containing screen-space vertex tuples. That is the object passed to `MainLoop.py` for rendering.

## animation.py

`animation.py` now defines a single `Animation` class attached to each `FaceObject`.

The animation object reads action dictionaries from `obj.action_queue`. Actions use fields such as:

```text
action
type
count
time
hold_on_complete
hold_range
hold_scale
hold_speed
```

Implemented action names in code:

```text
static
hover
blink
look
```

Current behavior:

- `static` completes when the object's shape transition is no longer active.
- `hover` changes `obj.anim_offset[1]` using a sine wave.
- `blink` closes vertices toward y=0, waits for that transition, then reopens the current shape.
- `look` currently only prints a message; it does not move the object.
- hold-on-complete keeps the final mouth pose alive and applies a repeated scale pulse by writing to `local_position`.

The hold path caches max and min local vertex positions and interpolates between them with a sine wave. `MouthManager` currently injects `hold_speed = 7.5` into mouth actions.

## MouthManager.py

`MouthManager` owns speech playback for the mouth object.

It loads `dataLibrary/mouth_shapes.json` and stores:

- `mouth`;
- `mouth_lib`;
- `syllable_queue`;
- `curr_syllable`;
- elapsed syllable time;
- a sample syllable queue used by the debug button.

`activate_speak()` accepts a syllable queue like:

```json
[
  {"syllable": "a", "time": 0.2},
  {"syllable": "m", "time": 0.1}
]
```

If no queue is provided, it uses the built-in sample queue.

The method inserts a brief neutral syllable at the start and appends a neutral syllable at the end. It then activates the mouth object and starts the first syllable.

`start_syllable()`:

1. Pops the next syllable.
2. Looks up the matching mouth shape data.
3. Applies the mouth transform scale.
4. Starts the requested shape state transition.
5. Copies the mouth animation payload.
6. Adds hold settings.
7. Replaces the mouth action queue with that one action.
8. Updates the attached `Animation`.

`transition_check()` advances to the next syllable only when both the syllable duration has elapsed and the mouth animation is done or holding.

`stfu()` clears the queue and deactivates the mouth.

## Command Listener and Client

`CommandListener.py` implements a background TCP server for local commands. It listens on the default host and port defined in the module and accepts newline-delimited JSON.

Expected command examples:

```json
{"type": "expression", "name": "happy"}
{"type": "speak", "syllables": [["a", 0.22], ["m", 0.12]]}
{"type": "stop_speech"}
```

`parse_command_line()` only performs minimal validation:

- payload must be JSON;
- payload must be an object;
- `type` must be one of `expression`, `speak`, `play`, or `stop_speech`.

It does not deeply validate expression names, syllable structure, durations, or audio payloads.

`CommandClient.py` provides `send_commands()`, which opens a socket connection and sends each command as one JSON line. It is used by the Tkinter debug client and can also be used by small scripts or tests.

## ElevenLabsClient.py

`ElevenLabsClient.py` turns text-to-speech alignment data into renderer commands.

Important functions:

```text
create_speak_command(text, debug)
process_audio(audio_data)
characters_to_syllables(characters)
timing_processing(start, end)
merge_syllable_timings(syllables, timings)
create_elevenlabs_audio(text)
normalize_audio_response(audio)
build_debug_audio()
```

`characters_to_syllables()` is a rough character-to-mouth-shape mapper. It maps input characters into the shape names currently present in `mouth_shapes.json`:

```text
a
d
e
f
m
o
r
s
wo
neutral
```

`merge_syllable_timings()` combines adjacent identical mouth shapes and merges very short durations into the previous item when possible.

`create_speak_command()` returns both a `speak` command and a `play` command. The renderer currently uses the `speak` command and ignores `play`, because audio playback is not implemented in `MainLoop.py`.

## Debug Client

`Scripts/clientSideDebugger/llm_response_debugger.py` is a Tkinter application for manually testing the command path.

It can:

- select a renderer host and port;
- select an expression from `expressions.json`;
- enter text representing an LLM response;
- send expression plus speak commands;
- send a stop-speech command;
- run in debug ElevenLabs mode using local sample alignment data.

The debug client sends commands through `CommandClient.send_commands()`.

## LLMAgentClient.py

`LLMAgentClient.py` is not part of the working runtime path. It sketches the intended orchestration:

```text
user text
  -> LLM response
  -> parse expression and spoken text
  -> send expression command
  -> create speech/mouth cues
  -> send speak command
```

The class references behavior that is not implemented in the file, such as parsing the LLM response. Treat it as a design stub, not production code.

## Data Model

### expressions.json

`expressions.json` has this top-level shape:

```json
{
  "version": 1,
  "default_state": "neutral",
  "states": {}
}
```

Current expression names:

```text
neutral
happy
sad
excited
thinking
test_state
```

`neutral`, `happy`, `sad`, and `test_state` contain object state data. `excited` and `thinking` currently exist as empty placeholders.

Object state data can set:

- `transform.origin_position`;
- `transform.rotation`;
- `transform.scale`;
- `shape_state`;
- `active`;
- `anim`;
- other direct object attributes via `setattr()`.

### anims.json

`anims.json` defines named queues of animation action dictionaries.

Current names:

```text
default
eye_neutral
eye_thinking
eye_look_left
eye_look_right
anim_test
```

The runtime does load this file. Assigning `obj.curr_anim` looks up the named action queue and feeds the current action into the object's `Animation` instance.

Some configured actions are ahead of the implementation. For example, `eye_thinking` contains an action named `think`, but `Animation.update()` does not currently handle `think`.

### mouth_shapes.json

`mouth_shapes.json` defines mouth presets used by `MouthManager`.

Current mouth entries:

```text
a
d
e
f
m
o
r
s
wo
neutral
smile
```

Most entries contain:

- a shape state name;
- a transform scale;
- an animation action payload;
- a `hold_scale` pair.

`smile` is present but does not have the same complete structure as the active syllable entries, so it should not be assumed to work as a normal speech syllable.

## Rendering Behavior

Rendering is immediate-mode Pygame drawing in `MainLoop.py`.

Current draw path:

```text
face_scene.update(dt)
  -> face_scene.drawables is rebuilt
  -> MainLoop iterates drawables
  -> pygame.draw.polygon(ren.screen, drawable.color, drawable.verts)
  -> optional vertex debug labels are drawn
  -> debug buttons are drawn
  -> CRT overlay is applied
  -> display flips
```

`DrawableMesh.verts` are already screen-space points. `FaceObject` keeps vertex data in local space and converts to screen space only when creating the drawable.

Layer values exist on `DrawableMesh`, but the current main draw loop does not sort by layer. It draws in the order `FaceScene.update()` appends active objects.

Opacity is stored on `FaceObject` and `DrawableMesh`, but the current polygon draw call uses only RGB color and does not apply opacity.

## Current Limitations

- Object roles are hardcoded; the mouth is assumed to be `objects[0]`.
- Expression state validation is weak because most fields are applied through direct `setattr()`.
- `FaceScene` has a naming collision between the `drawables` list attribute and `drawables()` method.
- Rendering still lives in `MainLoop.py` instead of a renderer draw API.
- Layer sorting is not active in the main render path.
- Opacity is stored but not rendered.
- The listener accepts `play` commands, but the renderer does not play audio.
- `look` is only a print stub.
- `think` appears in `anims.json`, but the animation system does not implement it.
- The LLM agent client is only a sketch.
- There are no automated tests.

## Practical Next Steps

The next useful implementation work should reduce ambiguity before adding features:

1. Replace `objects[0]` mouth ownership with an explicit role map or named object id.
2. Rename either `FaceScene.drawables` or `FaceScene.drawables()` to remove the collision.
3. Add explicit validation for expression state fields.
4. Move polygon drawing into `Renderer`.
5. Decide whether unsupported configured actions like `think` should be implemented or removed.
6. Add focused tests for expression application, animation action selection, mouth queue playback, and command parsing.

The program is now a working local face-renderer prototype with command-driven expression and mouth playback. It is not yet a complete robot display stack, and the documentation should not pretend otherwise.
