# AI Assistant Face Documentation

## Summary

`ai-assistant-face` is a Python/Pygame prototype that renders an animated assistant face from polygon meshes. The runtime creates a fixed pool of reusable `FaceObject` instances, assigns semantic roles to selected objects, applies JSON-authored state, advances shape and ambient animations, and sends drawable meshes to the renderer each frame.

The scene model now has three distinct layers of responsibility:

| Layer | Source | Responsibility |
| --- | --- | --- |
| Display mode | `dataLibrary/face_states.json` | Chooses visible roles, positions, controller ownership, ambient animation, and the default reset expression. |
| Appearance | `dataLibrary/expressions.json` | Chooses shape, scale, and rotation for the normal mouth and eyes. |
| Motion | `dataLibrary/anims.json` | Defines reusable action queues such as eye blinking and the thinking-dot hop. |

`ThinkingManager` is the controller-specific handoff for thinking mode. It temporarily repurposes the two eye objects, adds a third pooled object, and runs a staggered three-dot animation. Returning to a normal face state stops that controller and rebuilds the visible face from the current expression and face-state data.

The project also has a mouth/viseme manager, a local TCP command path, Pygame audio playback, a Tkinter debugger, ElevenLabs timing helpers, and focused automated tests for the thinking-state and gaze-command flows. It remains a prototype: several schemas are only minimally validated, some role behavior is still index-dependent, and test coverage is narrow outside those paths.

## Current File Map

```text
Scripts/MainLoop.py
  Application entry point and frame loop.
  Loads expressions, animations, and face states.
  Creates FaceScene and AudioPlayer.
  Dispatches commands on the Pygame thread.

Scripts/display/FaceScene.py
  Owns the object pool and semantic role map.
  Coordinates expression, display-mode, and normalized gaze changes.
  Hands thinking roles to ThinkingManager.
  Rebuilds the drawable list each frame.

Scripts/display/ThinkingManager.py
  Validates thinking-role configuration.
  Repositions, activates, and staggers the three dots.
  Stops and releases controlled objects on deactivation.

Scripts/display/Geometry.py
  Defines Transform, Vert, and FaceObject.
  Owns polygon generation, shape transitions, easing, animation selection,
  and local-to-screen conversion.

Scripts/display/animation.py
  Defines Animation.
  Executes static, hover, blink, look, think, and consonant-close actions.

Scripts/display/MouthManager.py
  Loads mouth_shapes.json.
  Converts speech timing entries into shape transitions and held actions.

Scripts/display/Renderer.py
  Creates the Pygame display.
  Draws meshes and applies pixelation plus CRT post-processing.

Scripts/display/RendererContract.py
  Defines DrawableMesh, the scene-to-renderer data contract.

Scripts/display/UI.py
  Defines the Pygame debug Button helper.

Scripts/aiIntegration/CommandListener.py
  Background TCP server for newline-delimited JSON commands.

Scripts/aiIntegration/CommandClient.py
  Client helper for sending commands to the local listener.

Scripts/aiIntegration/AudioPlayer.py
  Decodes base64 MP3 data and plays it through pygame.mixer.music.

Scripts/aiIntegration/ElevenLabsClient.py
  Produces audio and converts alignment data into mouth-shape timing.

Scripts/aiIntegration/LLMAgentClient.py
  Early LLM/TTS/command orchestration sketch; not in the live startup path.

Scripts/clientSideDebugger/llm_response_debugger.py
  Tkinter client for exercising expression, speech, gaze, and voice workflows.

dataLibrary/face_states.json
  Display modes, role placement, visibility intent, and controller metadata.

dataLibrary/expressions.json
  Named appearance data for semantic face roles.

dataLibrary/anims.json
  Named ambient animation queues.

dataLibrary/mouth_shapes.json
  Mouth shapes, per-shape actions, and hold scaling.

tests/test_thinking_manager.py
  Unit tests for ThinkingManager and Animation.think().
  Integration test for FaceScene thinking ownership and restoration.

tests/test_eye_look.py
  Command, debugger, and scene integration tests for gaze movement.

tests/test_default_reset.py
  Manager-flush and seamless/immediate default reset tests.
```

## Startup and Runtime Flow

Run from the repository root:

```powershell
python -m Scripts.MainLoop
```

The normal startup path is:

```text
Scripts.MainLoop import
  -> create Renderer with a 720x720 resizable display
  -> load dataLibrary/expressions.json
  -> load dataLibrary/anims.json
  -> load dataLibrary/face_states.json

main_loop(5)
  -> create FaceScene with five FaceObject instances
  -> set default expression: neutral
  -> set default face state: default
  -> create AudioPlayer
  -> start local CommandListener
  -> enter the Pygame frame loop
```

The expression is applied before the face state because those files answer different questions. The expression establishes the current appearance. The face state then decides which roles should be active, where those roles live, whether the expression is allowed, and whether a specialized controller owns any objects.

Each frame:

1. `ren.clock.tick(60)` produces `dt` in seconds.
2. Pygame events are collected.
3. Commands already queued by the TCP listener are drained and handled.
4. `FaceScene.update(dt)` advances active objects and rebuilds `face_scene.drawables`.
5. The screen is cleared.
6. `Renderer.draw_drawables()` draws each mesh.
7. `Renderer.post_processing()` applies pixelation and the CRT overlay.
8. Debug buttons are drawn after post-processing.
9. `pygame.display.flip()` presents the frame.

`MainLoop.py` has an `if __name__ == "__main__":` guard. Module-style startup is the intended package launch path and avoids the import problems caused by executing a nested display module directly.

## FaceScene.py

### Construction and object pool

`FaceScene` accepts four pieces of configuration plus the resolution:

```text
anim_library
expression_data
face_state_data
objCount
RESOLUTION
```

It creates `objCount` inactive `FaceObject` instances. Every object starts as a cyan 32-vertex circle and receives the same animation library. The constructor then creates a `Roles` map, a `MouthManager`, and a `ThinkingManager`.

The current semantic role mapping is:

```text
mouth_id       = 0
left_eye_id    = 1
right_eye_id   = 2
dot_left_id    = 1
dot_middle_id  = 2
dot_right_id   = 3
```

The first two thinking dots deliberately reuse the normal eye objects. The third dot uses object 3. `MainLoop` creates five objects, so object 4 is currently unassigned.

Centralizing these values in `Roles` is better than exposing numeric JSON keys, but it is not a dynamic role registry. The mapping is still hardcoded in `FaceScene.py`; runtime mouth dispatch now resolves through `roles.mouth_id`.

### Expression flow

The expression path is:

```text
handle_ai_command(data)
  -> read emotion, duration, and easing
  -> set_expression(expression_name, duration, easing)

set_expression(...)
  -> look up expression_data["states"][expression_name]
  -> save current_expression
  -> inspect the current face state's uses_expression flag
  -> resolve each semantic role through Roles
  -> apply shape_state, scale, and rotation
  -> activate each configured expression object
```

An unknown expression prints an error and returns `False`. A known expression returns `True`.

When the current face state has `uses_expression: false`, the method still saves the requested expression name but does not mutate the controlled objects. This is intentional for thinking mode: an expression change can be remembered while the dots are visible, then applied when a normal face state takes ownership again.

### Face-state flow

The display-mode path is:

```text
set_face_state(face_state_name, duration, easing)
  -> look up face_state_data["states"][face_state_name]
  -> route the configured default state through reset_to_default(...)
  -> save current_face_state
  -> collect roles whose controller is "thinking"
  -> deactivate an existing ThinkingManager session
  -> hide every pooled object
  -> reapply current_expression when uses_expression is true
  -> apply all non-thinking role data
  -> activate configured non-thinking objects
  -> pass thinking roles to ThinkingManager when present
```

This rebuild-from-data approach is the key ownership boundary. `FaceScene` decides the mode and hands specialized roles to a controller. The configured default state has a stricter lifecycle: `reset_to_default()` captures visible offsets, flushes speech/thinking/action state, applies neutral geometry and authored positions as transition targets, centers gaze, restarts `eye_neutral`, and shrinks non-default objects before deactivating them. When either default or speaking takes ownership directly from thinking, `FaceScene` asks `MouthManager` to create a collapsed mouth at the visible center of the thinking dots; the normal shape and placement transitions then grow and move it into the authored mouth pose.

Normal default commands use the supplied duration and easing. A command containing `"debug": "reset"` forces shape, placement, gaze, retirement, and animation transition timers to zero.

`controller: "thinking"` transfers role ownership to `ThinkingManager`. `controller: "eye"` identifies the normal eye roles eligible for gaze commands. The `mouth` controller value remains descriptive metadata.

### Object-state application

`apply_object_state()` recognizes these fields:

```text
scale        -> obj.transform.scale
rotation     -> obj.transform.rotation
position     -> direct placement, or obj.set_origin_position(...) during default reset and mouth entry
active       -> obj.active
ambient_anim -> obj.curr_anim
shape_state  -> obj.set_shape_state(...)
```

During the coordinated default reset, position changes preserve the currently rendered origin and ease its offset to the authored destination. Other face states retain direct placement behavior except for the mouth's thinking-to-speaking entry. If `shape_state` is absent, the method reapplies the object's current shape. That recalculates target vertices after scale or rotation changes without changing the named shape.

Other metadata such as `controller` and `sequence` is not applied to the object. `ThinkingManager` strips those keys before calling this callback. Non-thinking controller metadata simply passes through the loop without a matching case.

The old broad `setattr()` behavior is gone. That removes one class of accidental object mutation, although the JSON payloads still do not have formal schema validation.

### Per-frame update

`FaceScene.update(dt)` clears and rebuilds the `drawables` list. The role-mapped mouth is advanced through `MouthManager`; when no syllable is active, the manager still advances `FaceObject.update(dt)` so state-driven mouth shape and placement transitions can finish. Every other active object calls `FaceObject.update(dt)` directly. Retiring non-default objects remain drawable until their shrink transition completes. Each remaining active object is then converted to a `DrawableMesh`.

There is still a method named `drawables()` in the class, but the instance list `self.drawables` shadows it. The live runtime uses the list. The method is dead and also incorrectly assumes `self.objects` has a `.values()` method even though it is a list.

## ThinkingManager.py

### Responsibility

`ThinkingManager` owns a temporary animation session. It does not load JSON, know about expressions, or decide when thinking mode should start. `FaceScene` provides:

- a mapping from thinking role names to pooled objects;
- the `apply_object_state()` callback;
- the state-authored role payload;
- the transition duration and easing;
- an optional sequence delay.

The manager defaults to animation name `thinking` and a sequence delay of 0.2 seconds.

### Activation validation

`activate()` validates all manager-specific configuration before deactivating the current session or mutating objects:

- `sequence_delay` must be zero or greater;
- every configured role must exist in `role_objects`;
- every role must have a non-negative integer `sequence`;
- sequence numbers must be unique.

These checks reject invalid ownership data early. They do not require sequences to be contiguous or to start at zero.

### Activation sequence

After validation, activation performs these steps in ascending sequence order:

1. Stop any previous controlled-object session.
2. Clear the object's current ambient animation.
3. Apply position, shape, scale, and other object-state fields through the scene callback.
4. Force the object active.
5. Assign `curr_anim = "thinking"`.
6. Set `obj.anim.start_delay = sequence * delay_step`.
7. Record the object in `controlled_objects`.

For the checked-in state data, delays are:

```text
dot_left    sequence 0 -> 0.0 seconds
dot_middle  sequence 1 -> 0.2 seconds
dot_right   sequence 2 -> 0.4 seconds
```

`Animation.update()` consumes the delay before updating the action. If a frame crosses the end of the delay, the unused portion of that frame's `dt` is applied to the hop instead of being discarded.

### Deactivation

`deactivate()` sets `curr_anim` to `None` and `active` to `False` for every controlled object, clears `controlled_objects`, and marks the manager inactive. Its default-reset path first transfers the current hop offset into the placement channel so releasing the manager does not cause a visible snap.

Clearing `curr_anim` also resets the object's action queue, action index, current animation action, start delay, and animation offset. `FaceScene.set_face_state()` is responsible for applying whichever state should appear next.

## Thinking Animation

The `thinking` entry in `anims.json` contains one conditional `think` action:

```json
{
  "action": "think",
  "count": 1,
  "type": "conditional",
  "transition_time": 0.6,
  "amplitude": 18
}
```

`Animation.think(dt)` interprets `transition_time` as the duration of one hop cycle. It advances a phase around `math.tau` and writes a vertical offset between `0` and `-amplitude` using a cosine curve.

The action always returns `False`. It is an ambient loop, not a self-completing animation. `ThinkingManager.deactivate()` is the explicit stop condition.

The three objects run the same phase function. Their different `start_delay` values create the traveling-dot effect.

## Data Library

### Ownership boundary

The current data split is deliberate:

```text
face_states.json
  owns: role presence, position, active intent, controller, ambient_anim,
        uses_expression, default expression selection, thinking sequence metadata

expressions.json
  owns: shape_state, scale, rotation for the normal face roles

anims.json
  owns: named reusable action queues and their animation parameters

mouth_shapes.json
  owns: speech-shape geometry, per-shape action selection, hold_scale
```

Putting a field in the wrong file may produce no visible error. For example, controller metadata is not expression data, and expression scale must be applied through `obj.transform` rather than attached directly to `FaceObject`.

### `face_states.json`

Top-level structure:

```json
{
  "version": 2,
  "default_state": "default",
  "states": {}
}
```

Current state names:

```text
default
speaking
thinking
```

`default` and `speaking` use the same normal-face role positions, but their runtime behavior differs:

- both set `uses_expression` to `true`;
- mouth is placed at `[360, 540]`;
- eyes are placed at `[180, 360]` and `[540, 360]`;
- the eyes receive `eye_neutral` as their ambient animation.
- `default` explicitly selects `neutral` and flushes manager/animation state;
- `speaking` retains the current expression and does not perform a coordinated reset.

The runtime does not automatically switch to `speaking` when speech starts. Callers remain responsible for sending the desired state commands.

`thinking` has `uses_expression: false` and a top-level `sequence_delay` of 0.2. Its three roles are placed at x positions 300, 360, and 420 with y 420, use a 20-by-20 circle shape, declare `controller: "thinking"`, and carry sequences 0, 1, and 2.

Although role entries include `active`, the current controller paths force every configured role active after applying its state. An authored `active: false` would therefore be overwritten for both normal configured roles and thinking roles. In the checked-in data all configured values are `true`, so this mismatch is latent rather than visible.

### `expressions.json`

Top-level structure:

```json
{
  "version": "2",
  "default_state": "neutral",
  "states": {}
}
```

Current expression names:

```text
neutral
happy
```

Both expressions use semantic keys:

```text
mouth
left_eye
right_eye
```

Each role can set `shape_state`, `scale`, and `rotation`. `neutral` uses circular eyes; `happy` uses half-circle eyes. Both currently use the same half-circle mouth rotated 180 degrees.

Version 2 removed numeric object ids, positions, active flags, and ambient animation assignment from expression data. Those fields moved to `face_states.json`. This prevents appearance changes from silently taking ownership of placement or controller behavior.

The version metadata is not type-consistent across the two version-2 files: `face_states.json` uses the number `2`, while `expressions.json` uses the string `"2"`.

### `anims.json`

Configured animation names:

```text
default
eye_neutral
thinking
eye_look_left
eye_look_right
anim_test
```

`eye_neutral` runs `hover` and then `blink`. The hover action completes after two full sine cycles, so with the default animation speed it can take about 12.57 seconds before the blink starts.

`thinking` runs the continuous `think` hop described above.

`eye_look_left` and `eye_look_right` select `look` with target offsets of `[-30, 0]` and `[30, 0]`. Both named actions use the same gaze lerp as command-fed look targets.

`default` is currently configured as:

```json
["static"]
```

That does not match the action-dictionary contract expected by `Animation.update_curr_action()`. It should not be assigned through `FaceObject.curr_anim` until the data is corrected.

Implemented action names are:

```text
static
hover
blink
look
think
constanant_close
```

The `constanant_close` spelling is incorrect English but is currently part of the code/data contract. Renaming it requires changing both `animation.py` and every JSON producer/consumer in the same pass.

### `mouth_shapes.json`

Current entries:

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
wait
```

Most speech entries contain:

- a `shape_state.state` name;
- a `shape_state.scale` pair;
- an `anim` action dictionary;
- a `hold_scale` pair.

Most mouth shapes now use `static` rather than reusing the eye-style `blink` action. The `m` shape uses `constanant_close`, which closes and reopens across two halves of the supplied transition time.

`MouthManager` adds runtime-owned fields to a copy of the selected action:

```text
hold_on_complete = true
hold_range       = [0.5, 1.0]
hold_scale       = value from mouth_shapes.json
hold_speed       = 7.5
transition_time  = speech item's transition time
time             = speech item's total time
```

`wait` is an empty sentinel entry. `MouthManager` checks for that name before looking up shape data, advances its timer without updating mouth geometry, and then carries frame overshoot into the next syllable.

`smile` is not shaped like a complete normal speech entry: its shape-state object is empty and its animation payload only supplies time. It should not be passed through the standard speech-shape path.

## Animation Action Contract

`FaceObject.curr_anim = <name>` looks up `anim_dict["anims"][name]`, replaces the object's action queue, resets the action index, and loads the first action into its attached `Animation` object.

Common action fields include:

```text
action
type
count
time
transition_time
amplitude
hold_on_complete
hold_range
hold_scale
hold_speed
```

Current action behavior:

- `static`: completes after the object's shape transition ends.
- `hover`: applies a vertical sine offset and completes after two cycles.
- `blink`: closes vertices to the horizontal centerline and reopens them over `transition_time`.
- `look`: lerps a separate gaze offset, reports completion, and can run without interrupting hover or blink actions.
- `think`: applies a continuous upward hop and relies on its manager for cancellation.
- `constanant_close`: closes and reopens the mouth over two half transitions.

The animation object also supports an action-level `start_delay`. Thinking mode is the current consumer.

## MouthManager and Speech Timing

`MouthManager` owns the speech queue for the role-mapped mouth object. `MainLoop.listen_for_input()` converts wire-format speech items into dictionaries shaped like:

```json
{
  "syllable": "a",
  "time": 0.05,
  "total_time": 0.22
}
```

`time` is the transition time for entering the shape. `total_time` is the audio time owned by that speech item. Those values must stay separate; changing one does not imply the same change to the other.

`activate_speak()` prepares the queue, activates the mouth, and starts the first item. It appends a short neutral item to close out the sequence.

`transition_check()` advances only when total time has elapsed and the current animation is done or holding. Any frame overshoot is passed to the next item instead of being discarded.

At the end of the queue, `MouthManager` deactivates the mouth. It does not reapply the current face state, even though the checked-in `default` state declares the mouth active. That lifecycle mismatch is still present.

## Commands and Audio

`CommandListener` listens on `127.0.0.1:6001` and accepts one newline-delimited JSON object per command. It verifies only that the payload is an object and that `type` is one of the known names.

Current commands:

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

Look targets are normalized directions. `[0, 0]` centers the gaze, each axis ranges from `-1` to `1`, and out-of-range vectors are normalized to the unit circle. `FaceScene.set_look_target()` converts the direction to an offset equal to 30 percent of the current eye radius and hands animation data to both active `controller: "eye"` roles. Thinking mode rejects gaze commands because those objects are temporarily owned as dots.

A normal default command performs a blended reset and stops active audio after the scene accepts it. The `debug: "reset"` form uses the same cleanup order but makes every reset transition immediate. The debugger exposes that form as `Reset Default (No Blend)`.

Command effects:

```text
expression  -> FaceScene.set_expression(...)
face_state  -> FaceScene.set_face_state(...)
look        -> FaceScene.set_look_target(...)
speak       -> MouthManager.activate_speak(...)
play        -> AudioPlayer.play_base64_audio(...)
stop_speech -> stop mouth timing and pygame.mixer.music
```

The speech consumer expects every syllable item to have exactly three values: name, transition time, and total time. The listener does not validate this nested shape. A malformed or old two-value payload can therefore pass the listener and fail during main-thread unpacking.

`AudioPlayer` decodes base64 data into an in-memory file and asks `pygame.mixer.music` to load it as MP3. Mixer initialization or playback errors are printed and disable or skip playback rather than crashing construction.

## Rendering Behavior

`FaceObject` keeps vertices in local coordinates. `local_to_screen()` adds the transform origin and the animation offset. `to_drawable()` packages screen-space points into a `DrawableMesh`.

The current draw path is:

```text
FaceScene.update(dt)
  -> face_scene.drawables list
  -> Renderer.draw_drawables(drawable)
  -> pygame.draw.polygon(...)
  -> Renderer.post_processing()
       -> pixelate()
       -> apply_crt()
  -> debug button drawing
  -> pygame.display.flip()
```

Layer and opacity values exist in the drawable contract, but the current loop does not sort by layer and the polygon draw call does not use opacity.

## Tests

Run the test suite from the repository root:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
```

The current suites cover:

1. thinking-dot positioning, sequencing, animation, and ownership release;
2. gaze interpolation, target replacement, named looks, and face-state ownership;
3. seamless default placement/shape retirement and zero-duration debug reset;
4. mouth position/shape entry from thinking into default and speaking;
5. speech, animation, gaze, and expression flushing during default reset;
6. listener, AI-client, and debugger payload generation and validation;
7. debugger directional presets and selected host/port routing.

The tests stub `pygame` because the covered manager and scene-state behavior does not need a live window.

## Current Limitations

- `Roles` centralizes ids, but it remains a fixed index map rather than a validated registry.
- Object 4 is allocated but has no semantic role.
- Speech does not change face state automatically.
- Configured role objects are forced active, so authored `active: false` is overwritten.
- Leaving speech deactivates the mouth without restoring the current face-state visibility.
- `FaceScene.drawables` shadows a broken method with the same name.
- JSON files have no schema validator, and version metadata types are inconsistent.
- The `default` animation payload does not match the action-dictionary contract.
- The misspelled `constanant_close` name is embedded in both code and data.
- Listener validation stops at the top-level command type; nested payload errors reach the main loop.
- Layer sorting and opacity rendering are not active.
- Audio depends on the local Pygame mixer and MP3 support.
- Automated coverage includes thinking, gaze, and default reset behavior; mouth timing, audio, rendering, and data schemas still lack comprehensive tests.
- `LLMAgentClient.py` remains a design sketch.

## Practical Next Steps

The highest-value cleanup is at the state boundary, not in additional animation features:

1. Decide whether role presence or the `active` field owns visibility, then enforce one contract.
2. Restore the current face state when speech finishes, or explicitly define speech as a face-state transition.
3. Remove or rename the shadowed `drawables()` method.
4. Add schema validation for all four data-library files and normalize version types.
5. Repair or remove the malformed `default` animation entry.
6. Add command-payload tests for speech triplets, play, and stop behavior.
7. Expand integration tests before adding more controllers.

The current implementation has a coordinated default lifecycle, a working thinking controller, and independent gaze motion. The remaining problems are mostly contract enforcement and automatic speech-state handoff; the documentation should continue to describe those limits plainly rather than presenting the prototype as a finished scene framework.
