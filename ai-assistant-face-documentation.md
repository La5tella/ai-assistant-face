# AI Assistant Face Documentation

## Summary

`ai-assistant-face` is currently a small Python and pygame prototype for drawing animated face objects as polygon meshes. The app loads expression data from JSON, creates a fixed pool of `FaceObject` instances, applies the default expression, and then runs a pygame frame loop that updates and renders active objects.

The codebase is not yet the larger robot display system described in the old design document. IPC, socket input, lifecycle state machines, shape resampling, opacity, deployment scripts, and a dedicated renderer draw API are not implemented yet. Pretending otherwise would be bad documentation, and bad documentation is how future you gets ambushed by past you.

## Current File Map

```text
MainLoop.py
  imports Renderer, FaceObject, FaceScene, Transform, Button
  loads dataLibrary/expressions.json
  creates Renderer
  creates FaceObject pool
  creates FaceScene
  applies default expression
  owns pygame event loop
  draws active objects with pygame.draw.polygon

FaceScene.py
  defines Transform
  defines Vert
  defines FaceObject
  defines FaceScene
  imports animation as anim

Renderer.py
  wraps pygame.init()
  creates pygame display surface
  creates font list
  creates pygame clock

UI.py
  defines Button
  handles mouse hover/click state
  draws button rectangle and label

animation.py
  defines Hover animation class

dataLibrary/expressions.json
  defines expression states and default state

dataLibrary/anims.json
  defines intended animation names
  currently not loaded by runtime code
```

## Runtime Flow

The current runtime path starts in `MainLoop.py`.

```text
Python executes MainLoop.py
  -> Renderer is constructed with 720x720 pygame.RESIZABLE display
  -> dataLibrary/expressions.json is loaded
  -> main_loop(5) is called immediately
  -> five FaceObject instances are created and stored in objPool
  -> FaceScene is created with objPool and expression_data
  -> FaceScene.set_expression(default_state, duration=0) is applied
  -> pygame loop starts
      -> clock ticks at 60 FPS target
      -> pygame events are read
      -> screen is cleared to black
      -> FaceScene.update(dt) is called
      -> active objects are drawn as filled polygons
      -> vertex debug labels are drawn when enabled
      -> debug Button is drawn and updated
      -> pygame.display.flip() presents the frame
```

`main_loop(5)` is called at module import time, so importing `MainLoop.py` also starts the application. That is convenient for a quick prototype and lousy for tests or reuse.

## Implemented Architecture

### MainLoop.py

`MainLoop.py` is the real application entry point. It owns global setup and most runtime behavior:

- sets `BASE_DIR` from the file location;
- sets `RESOLUTION` to `[720, 720]`;
- constructs a `Renderer`;
- loads `dataLibrary/expressions.json`;
- stores objects in the global `objPool`;
- stores the active `FaceScene` in the global `face_scene`;
- creates a debug `Button` labeled `Cycle State`;
- creates five `FaceObject` instances;
- applies the default expression from JSON;
- runs the pygame frame loop;
- renders polygons directly with `pygame.draw.polygon`.

The debug button calls `cycle_all_shape_states()`, which cycles each active object through the hardcoded shape states on its `FaceObject`.

`apply_face_state()` is present as a helper for applying the default state, but the normal startup path now uses `face_scene.set_expression(...)`.

### Renderer.py

`Renderer` is a thin pygame wrapper. It stores:

- `RESOLUTION`;
- `OBJBANK`;
- `DISPLAY`;
- `fonts`;
- `screen`;
- `clock`;
- `running`.

It initializes pygame, creates the display surface, creates a default Arial font, and creates the frame clock. It does not currently provide draw methods for face objects. Rendering still happens in `MainLoop.py`.

### UI.py

`Button` is a small pygame UI component used by the debug control in `MainLoop.py`.

It stores a `pygame.Rect`, text, font index, font color, screen reference, hover state, and click callback. On each draw, it:

- reads mouse position;
- checks hover state;
- scans events for mouse button down;
- calls `on_clicked` when clicked;
- draws a rectangle;
- draws its text label.

### FaceScene.py

`FaceScene.py` contains the core face model.

`Transform` stores screen-space placement data:

- `origin_position`;
- `scale`;
- `rotation`.

`Vert` stores a single mesh vertex:

- current `position`;
- `connected_verts`;
- `target_position`.

It can draw its own debug index through `draw_vert_debug()`.

`FaceObject` is the drawable animated shape. It stores identity, visibility, layer, color, transform, aspect ratio, vertex count, debug options, transition timing, and shape state data.

Supported shape states are hardcoded:

```text
Circle
Square
Rectangle
Triangle
```

The shape state methods calculate each vertex target position:

- `circleOrient()`;
- `rectangleOrient()`;
- `triangleOrient()`;
- `orientVertsAlongPolygon()`.

Shape animation is handled by:

- `set_shape_state()`;
- `apply_shape_state()`;
- `update_shape_state()`;
- `update()`;
- `lerp()`;
- `ease_value()`.

Supported easing names are:

```text
linear
ease-in
ease-out
ease
```

`ease` is smoothstep.

`FaceScene` coordinates expression changes across the object pool. It stores:

- `objects`;
- `expression_data`;
- `current_expression`.

Its main command path is:

```text
handle_ai_command(data)
  -> reads data["emotion"], data["duration"], data["easing"]
  -> calls set_expression(...)

set_expression(expression_name, duration, easing)
  -> looks up expression_data["states"][expression_name]
  -> iterates object ids in the expression
  -> calls apply_object_state(...)

apply_object_state(obj, state_data, duration, easing)
  -> applies position to obj.transform.origin_position
  -> applies other JSON fields using setattr()
  -> applies or recalculates shape state
```

### animation.py

`animation.py` currently defines `Hover`.

`Hover` is written as an instance-based animation class. It expects to store:

- target object;
- base y position;
- amplitude;
- speed;
- elapsed time.

Its `update()` method changes the object's y position using a sine wave, then reapplies the object's current shape state so vertex targets follow the new transform.

The runtime does not currently instantiate `Hover` objects. `FaceScene.update()` calls `getattr(anim, "Hover").update(obj, dt=dt)`, which treats `Hover.update()` like a static method even though it depends on instance fields.

## Data Model

### dataLibrary/expressions.json

`expressions.json` is the only JSON file currently loaded by runtime code.

Top-level fields:

```json
{
  "version": 1,
  "default_state": "neutral",
  "states": {}
}
```

`default_state` names the expression applied during startup.

`states` maps expression names to object state dictionaries. Object ids are numeric indexes encoded as strings:

```json
{
  "neutral": {
    "0": {
      "position": [180.0, 360.0],
      "shape_state": "Circle",
      "active": true,
      "anim": "eye_neutral"
    },
    "1": {
      "position": [540.0, 360.0],
      "shape_state": "Circle",
      "active": true,
      "anim": "eye_neutral"
    }
  }
}
```

The current expression library defines:

```text
neutral
happy
sad
excited
thinking
```

Only `neutral` currently contains object state data. The other expressions exist as empty placeholders.

Expression state data can currently set:

- `position`, applied to `obj.transform.origin_position`;
- `shape_state`, applied through `obj.set_shape_state(...)`;
- `active`, or any other attribute, applied through direct `setattr()`.

That direct `setattr()` behavior is flexible, sure, but it is also a foot-cannon. A typo in JSON can silently create the wrong runtime state.

### dataLibrary/anims.json

`anims.json` defines intended animation mappings:

```json
{
  "eye_neutral": ["anim.Hover", "anim.Blink"],
  "eye_thinking": ["anim.Hover", "anim.Think"],
  "eye_look_left": ["anim.Look"],
  "eye_look_right": ["anim.Look"]
}
```

This file is not currently loaded or used by the runtime. It also references animation classes or functions that do not exist yet: `Blink`, `Think`, and `Look`.

## Rendering Behavior

Rendering is currently immediate-mode pygame drawing inside `MainLoop.py`.

For each active object:

```text
points = [vert.position for vert in obj.verts]
pygame.draw.polygon(ren.screen, obj.color, points)
```

If `vert_debug` is enabled, every vertex draws its numeric index using the renderer font list.

Coordinates are screen-space values. The current implementation does not use a center-origin world coordinate system, camera transform, opacity, stroke style, draw modes, or layer sorting.

## Shape Animation Behavior

Each `FaceObject` owns a fixed list of `Vert` instances. `vert_count` is set when the object is constructed. In the current startup path, every object gets `32` vertices.

When a shape state is applied:

1. the target state name is validated against `shape_state_lib`;
2. target positions are recalculated from the object's transform;
3. if duration is `0`, current positions snap to targets;
4. otherwise, `in_transition` is set to `True`;
5. each update lerps current vertex positions toward target positions;
6. movement stops when all vertices are close enough to their targets.

During transitions, `debug_movement()` changes the object color toward red/green. Once settled, the object becomes green.

## Current Limitations

The current implementation does not include:

- IPC or socket command input;
- ROS integration;
- object spawn/despawn lifecycle states;
- actual runtime object allocation and release;
- shape data loaded from JSON;
- arbitrary authored mesh states;
- shape resampling;
- nearest-neighbor vertex mapping;
- opacity;
- stroke rendering;
- layer sorting;
- fullscreen robot deployment;
- watchdog behavior;
- logging to `logs`;
- automated tests.

The code does preallocate five `FaceObject` instances, so there is an object pool in the loose sense. There is not yet a full object pooling lifecycle with inactive, spawning, active, and despawning states.

## Areas of improvement

- Fix the animation system. `FaceScene.update()` currently calls `Hover.update()` as if it were static, while `Hover` expects instance state such as `time`, `base_y`, `amplitude`, and `speed`.
- Wire up or remove `dataLibrary/anims.json`. It currently references `anim.Blink`, `anim.Think`, and `anim.Look`, which do not exist.
- Resolve animation naming drift. Expression data uses `"anim"`, `FaceObject` has `curr_anim`, and neither path currently drives animation.
- Move polygon rendering out of `MainLoop.py` and into `Renderer`, so rendering and application control are not tangled together.
~~- Guard startup with `if __name__ == "__main__":` so importing `MainLoop.py` does not launch the pygame app.~~
- Replace broad `setattr()` from JSON with explicit validation for supported expression fields.
- Fix default mutable constructor arguments such as `origin_position=[540,540]`, `aspect_ratio=[1,1]`, and UI rect defaults.
- Clarify object pooling. The code preallocates objects, but spawn/despawn lifecycle behavior is not implemented.
- Add tests for expression application, shape state transitions, invalid shape states, and animation update behavior.
- Clean up stale design claims as implementation changes, especially around IPC, deployment, and renderer responsibilities.

## Practical Next Steps

The next useful implementation pass should fix the animation contract before adding more features. A reasonable order is:

1. Add an explicit animation instance registry on each `FaceObject` or in `FaceScene`.
2. Load or delete `anims.json`, instead of leaving it as misleading configuration.
3. Move object drawing into `Renderer`.
4. ~~ Add a `__main__` guard.~~
5. Add focused tests around expression application and shape transitions.

After that, the project can decide whether the next milestone is richer local animation, JSON-authored shape meshes, or external command input. Right now the foundation is a prototype polygon face renderer, and that is fine, as long as the documentation says so plainly.
