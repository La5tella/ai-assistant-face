# Robot Face Display System — Design Document

## 1. Project Goal

Create a lightweight face display program that runs under Xorg on a Unitree G1 robot. The program receives input from another process and displays an animated face on a screen in real time.

The system should behave conceptually like a simplified 2D animation/compositing engine, similar to After Effects:

- Multiple visual objects/layers
- Mesh-based shapes made from vertices
- Named visual states such as `neutral`, `exclamation`, `circle`, `heart`, `happy`, `alert`, etc.
- Smooth interpolation between states
- Object origins/transforms for movement, scaling, and rotation
- Objects that can appear, disappear, or be reused during real-time animation
- External control through messages from another program

The renderer should be computationally lightweight and reliable. The first version should prioritize correctness, clarity, and testability over premature optimization.

---

## 2. Recommended Technology Stack

### Prototype Stack

Use:

- **Python**
- **pygame**
- **Unix domain socket** or **UDP localhost** for IPC
- **JSON** for message format
- **Xorg fullscreen window** for display

Reasoning:

- Python is fast enough for a 2D face renderer at 30–60 FPS.
- pygame is simple for fullscreen drawing, input handling, frame timing, and polygon rendering.
- JSON messages are easy to debug manually.
- Unix sockets are efficient for local process-to-process communication.
- The system can later be ported to C++/SDL2 if profiling proves Python is too slow.

### Production Candidate Stack

Use:

- **C++**
- **SDL2**
- Same JSON or binary-compatible message format
- Same conceptual data model

Avoid starting with raw Xlib unless there is a very specific requirement. Raw Xlib will slow development without providing meaningful benefit for this project’s first version.

---

## 3. Core Architectural Model

The system is a small 2D scene engine.

```text
FaceApplication
  ├─ IPCServer
  ├─ FaceScene
  │   └─ FaceObject[]
  │       ├─ Mesh
  │       ├─ Transform
  │       ├─ ShapeStates
  │       ├─ AnimationController
  │       └─ LifecycleState
  ├─ Renderer
  └─ MainLoop
```

---

## 4. Core Concepts

## 4.1 Face Scene

The `FaceScene` owns all active visual objects.

Responsibilities:

- Store all face objects
- Route state-change commands to the correct object
- Update all animations each frame
- Ask the renderer to draw objects in layer order
- Maintain global face state if needed

Example:

```text
FaceScene
  - left_eye
  - right_eye
  - mouth
  - left_brow
  - right_brow
  - emotion_symbol
  - cheek_marks
```

---

## 4.2 Face Object

A `FaceObject` is one drawable animated item.

Examples:

- Left eye
- Right eye
- Mouth
- Eyebrow
- Heart symbol
- Exclamation mark
- Blush mark
- UI-style status icon

Each object has:

```text
FaceObject
  - id
  - visible
  - active
  - layer_index
  - transform
  - mesh
  - shape_states
  - current_state
  - target_state
  - animation_controller
  - style
```

---

## 4.3 Mesh

A mesh is a collection of 2D vertices. For the first version, each mesh can be rendered as a filled polygon or polyline.

```text
Mesh
  - vertices: Vec2[]
  - draw_mode: filled_polygon | polyline | points
```

For simple face rendering, start with filled polygons and polylines. Triangulation can be added later if needed.

---

## 4.4 Shape States

A shape state is a named set of vertex positions for a given object.

Example:

```json
{
  "object_id": "left_eye",
  "states": {
    "neutral": [[-20, -5], [20, -5], [20, 5], [-20, 5]],
    "circle": [[0, -20], [14, -14], [20, 0], [14, 14], [0, 20], [-14, 14], [-20, 0], [-14, -14]],
    "closed": [[-20, 0], [20, 0]]
  }
}
```

Important: for clean interpolation, states should usually share the same vertex count and vertex meaning.

Good:

```text
neutral: 32 vertices
happy:   32 vertices
angry:   32 vertices
```

Bad:

```text
neutral: 8 vertices
happy:   31 vertices
angry:   52 vertices
```

Different vertex counts can be supported later using resampling.

---

## 4.5 Transform

Every object has an origin and transform.

```text
Transform
  - position: Vec2
  - origin: Vec2
  - rotation_degrees: float
  - scale: Vec2
  - opacity: float
```

Transforms should be animated separately from mesh deformation.

This gives three animation layers:

1. **Shape animation** — vertex morphing
2. **Transform animation** — position, rotation, scale, opacity
3. **Lifecycle animation** — spawn, despawn, fade, pop, squash

---

## 5. Interpolation System

## 5.1 Basic Vertex Lerp

The core interpolation operation:

```text
current_vertex = lerp(source_vertex, target_vertex, t)
```

Where:

```text
t = 0.0 → source state
t = 1.0 → target state
```

Formula:

```text
lerp(a, b, t) = a + (b - a) * t
```

Each frame:

```text
elapsed += delta_time
t = elapsed / duration
t = clamp(t, 0.0, 1.0)
t = easing(t)
current_vertices[i] = lerp(start_vertices[i], target_vertices[i], t)
```

---

## 5.2 Easing

Do not use only linear interpolation. It will feel robotic and cheap.

Recommended easing functions:

```text
linear
smoothstep
ease_in
ease_out
ease_in_out
ease_out_back
ease_out_elastic
```

Start with:

```text
smoothstep
```

Formula:

```text
smoothstep(t) = t * t * (3 - 2 * t)
```

---

## 5.3 Vertex Correspondence Rule

The most important visual rule:

> Corresponding vertices must represent corresponding parts of the shape.

Example:

```text
vertex 0 = top point
vertex 1 = upper-right contour
vertex 2 = right contour
vertex 3 = lower-right contour
...
```

If vertex 0 means “top of heart” in one state and “left side of exclamation mark” in another, the morph will look bad.

---

## 5.4 Nearest-Neighbor Mapping

A proposed idea was to use “sample nearest” so vertices snap or map to the nearest next-state vertex.

This can be useful, but it should not be the main runtime method.

Nearest-neighbor mapping:

```text
for each source vertex:
    find closest target vertex
    map source_index → target_index
```

Problems:

- Vertices can cross paths.
- Multiple source vertices can choose the same target vertex.
- Silhouettes can collapse.
- Complex shapes can tangle.
- Results can change unpredictably if recomputed during runtime.

Recommended use:

- Use nearest-neighbor as an **authoring/preprocessing helper**.
- Save the resulting mapping.
- Runtime should use deterministic saved mappings, not search every frame.

---

## 5.5 Better Solution: Outline Resampling

For shapes with different vertex counts, use outline resampling.

Process:

```text
1. Take source outline.
2. Take target outline.
3. Resample both outlines to N evenly spaced points.
4. Ensure both outlines use the same winding direction.
5. Choose a consistent starting point.
6. Lerp point[i] to point[i].
```

Example:

```text
circle → 64 points
heart → 64 points
exclamation → 64 points
```

Then morphing becomes stable:

```text
circle_points[i] → heart_points[i]
```

For closed shapes:

```text
sample clockwise around perimeter
normalize starting point
lerp point[i] to point[i]
```

For open shapes, like a mouth curve:

```text
sample left-to-right
lerp point[i] to point[i]
```

---

## 6. Object Lifecycle System

Objects may be created or destroyed for real-time animations.

However, the first implementation should avoid constant allocation/deallocation during animation.

Use an object pool.

Instead of:

```text
create object → animate → destroy object
```

Use:

```text
inactive pooled object → activate → animate in → animate out → mark inactive
```

Benefits:

- Avoids garbage collection spikes
- Avoids runtime allocation jitter
- Makes behavior more predictable
- Easier to debug

Object lifecycle states:

```text
inactive
spawning
active
despawning
```

Spawn animation examples:

```text
scale: 0.0 → 1.0
opacity: 0.0 → 1.0
```

Despawn animation examples:

```text
scale: 1.0 → 0.0
opacity: 1.0 → 0.0
```

---

## 7. IPC / External Control

The face program should receive commands from another program.

Recommended first version:

- Unix domain socket
- JSON messages

Socket path:

```text
/tmp/robot_face.sock
```

Alternative:

- UDP on `127.0.0.1`
- ROS 2 topic if integrating deeply into the robot stack

---

## 7.1 Message Types

### Set Object State

```json
{
  "type": "set_state",
  "target": "mouth",
  "state": "happy",
  "duration": 0.18,
  "easing": "ease_out"
}
```

### Set Full Face Expression

```json
{
  "type": "set_expression",
  "expression": "surprised",
  "duration": 0.25,
  "easing": "ease_out_back"
}
```

### Spawn Symbol

```json
{
  "type": "spawn",
  "object_type": "symbol",
  "state": "heart",
  "position": [200, 100],
  "duration": 0.3
}
```

### Despawn Object

```json
{
  "type": "despawn",
  "target": "emotion_symbol",
  "duration": 0.2
}
```

### Set Transform

```json
{
  "type": "set_transform",
  "target": "left_eye",
  "position": [-100, -40],
  "scale": [1.2, 1.2],
  "rotation": 0,
  "duration": 0.15,
  "easing": "smoothstep"
}
```

---

## 8. Data File Format

The face rig should be described in external JSON files so the art/animation can be changed without rewriting code.

Example file:

```json
{
  "scene": {
    "width": 800,
    "height": 480,
    "background": [0, 0, 0]
  },
  "objects": [
    {
      "id": "left_eye",
      "layer": 10,
      "draw_mode": "filled_polygon",
      "style": {
        "fill": [255, 255, 255],
        "stroke": null,
        "opacity": 1.0
      },
      "transform": {
        "position": [-120, -40],
        "origin": [0, 0],
        "rotation": 0,
        "scale": [1, 1]
      },
      "states": {
        "neutral": [[-30, -8], [30, -8], [30, 8], [-30, 8]],
        "wide": [[-30, -20], [30, -20], [30, 20], [-30, 20]],
        "closed": [[-30, -2], [30, -2], [30, 2], [-30, 2]]
      }
    }
  ],
  "expressions": {
    "neutral": {
      "left_eye": "neutral",
      "right_eye": "neutral",
      "mouth": "neutral"
    },
    "surprised": {
      "left_eye": "wide",
      "right_eye": "wide",
      "mouth": "circle"
    }
  }
}
```

---

## 9. Runtime Loop

The main loop should be simple and predictable.

```text
initialize window
load rig JSON
start IPC server

while running:
    delta_time = clock.tick()

    read pending IPC messages
    apply commands to scene

    scene.update(delta_time)
    renderer.clear()
    renderer.draw(scene)
    renderer.present()
```

Target frame rate:

```text
60 FPS preferred
30 FPS acceptable
```

At 60 FPS, the frame budget is:

```text
16.6 ms per frame
```

This system should comfortably fit inside that if kept simple.

---

## 10. Renderer Requirements

The first renderer should support:

- Fullscreen Xorg window
- Filled polygon drawing
- Polyline drawing
- Layer sorting
- Opacity if available
- Basic transforms
- Screen-space coordinate conversion

Coordinate system:

```text
Scene origin: center of screen
X+: right
Y+: down or up, but choose one and stay consistent
```

Recommended:

```text
Internal coordinates: center-origin, Y up
pygame screen coordinates: top-left origin, Y down
```

Conversion:

```text
screen_x = screen_width / 2 + world_x
screen_y = screen_height / 2 - world_y
```

---

## 11. State Machine

Each object should have an independent animation state.

```text
ObjectAnimation
  - start_vertices
  - target_vertices
  - current_vertices
  - elapsed
  - duration
  - easing
  - active
```

When a new state command arrives:

```text
start_vertices = current_vertices
target_vertices = state_vertices[target_state]
elapsed = 0
duration = command.duration
easing = command.easing
active = true
```

This allows interruptions.

Example:

```text
neutral → happy starts
halfway through, alert command arrives
current halfway shape becomes new start
current → alert begins immediately
```

This is important for realtime robot responsiveness.

---

## 12. Performance Expectations

The face renderer should not be computationally heavy.

Likely costs:

```text
JSON parse: small
IPC read: small
Vertex interpolation: tiny
2D polygon drawing: small
Display refresh: dominant visible latency
```

C may reduce computation time, but it probably will not meaningfully reduce perceived response time at this stage.

The display refresh and animation duration matter more than raw language speed.

Use Python first. Profile before rewriting.

---

## 13. When to Move from Python to C++

Port to C++/SDL2 only if one or more of these becomes true:

- Python process uses too much CPU
- Python stutters during animation
- Startup time is unacceptable
- Garbage collection causes visible hitches
- Deployment dependencies become annoying
- The robot compute environment cannot comfortably run the Python stack
- You need tighter control over rendering and memory

Do not port because of instinct alone. Measure first.

---

## 14. Minimum Viable Prototype

The first milestone should be extremely small.

### MVP Goal

Display one morphing polygon under Xorg.

### MVP Features

- Open a pygame window
- Draw one object
- Define two shape states
- Interpolate between them
- Trigger state change with a keyboard key

Example:

```text
Press 1 → neutral
Press 2 → circle
Press 3 → heart
```

No sockets yet. No object pooling yet. No complex editor.

---

## 15. Implementation Phases

## Phase 1 — Single Object Morph

Build:

- `Vec2`
- `lerp`
- `smoothstep`
- `FaceObject`
- `ShapeState`
- pygame render loop

Success condition:

- One polygon smoothly morphs between two states.

---

## Phase 2 — Multiple Objects

Build:

- `FaceScene`
- Layer sorting
- Multiple face parts
- Basic transforms

Success condition:

- Left eye, right eye, and mouth animate independently.

---

## Phase 3 — Expression Presets

Build:

- Expression dictionary
- `set_expression(expression_name)`

Success condition:

- One command changes multiple objects together.

Example:

```text
neutral → surprised
surprised → happy
happy → thinking
```

---

## Phase 4 — IPC Input

Build:

- Unix socket server
- JSON message parser
- Command router

Success condition:

- External program can send messages that change face state.

Example:

```bash
echo '{"type":"set_expression","expression":"happy","duration":0.2}' | socat - UNIX-CONNECT:/tmp/robot_face.sock
```

---

## Phase 5 — Object Pooling and Spawn Effects

Build:

- Object pool
- Spawn/despawn lifecycle
- Animated symbols

Success condition:

- Heart/exclamation/circle symbols can appear and disappear without new allocation each time.

---

## Phase 6 — Shape Resampling

Build:

- Resample closed outlines to N points
- Resample open curves to N points
- Normalize winding direction
- Normalize starting point

Success condition:

- Different authored shapes can morph cleanly after preprocessing.

---

## Phase 7 — Robot Deployment Hardening

Build:

- Fullscreen launch script
- systemd service
- watchdog behavior
- fallback idle face
- safe error face
- logging
- FPS/CPU monitor

Success condition:

- Face app starts automatically and keeps running on robot boot.

---

## 16. File Structure

Recommended project layout:

```text
robot_face/
  main.py
  face_scene.py
  face_object.py
  animation.py
  renderer_pygame.py
  ipc_server.py
  easing.py
  geometry.py
  object_pool.py
  data/
    rig.json
    expressions.json
  tools/
    send_face_command.py
    resample_shape.py
  tests/
    test_lerp.py
    test_resample.py
```

---

## 17. Key Classes

### Vec2

```text
Vec2
  - x
  - y
```

Operations:

```text
add
subtract
multiply scalar
lerp
length
distance
```

---

### FaceObject

```text
FaceObject
  - id
  - layer
  - visible
  - active
  - transform
  - states
  - current_vertices
  - animation
  - style

methods:
  - set_state(state_name, duration, easing)
  - update(delta_time)
  - get_transformed_vertices()
```

---

### FaceScene

```text
FaceScene
  - objects
  - expressions

methods:
  - update(delta_time)
  - set_object_state(target, state, duration, easing)
  - set_expression(expression, duration, easing)
  - spawn_object(type, state, position)
  - despawn_object(target)
```

---

### IPCServer

```text
IPCServer
  - socket_path
  - pending_messages

methods:
  - poll()
  - get_commands()
```

---

## 18. Design Rules

1. **Same topology first.** Do not start with complex vertex matching.
2. **Animation must be interruptible.** New state changes should start from the current visual shape.
3. **Do not allocate constantly during animation.** Use object pooling for spawned effects.
4. **Keep rendering separate from animation logic.** This makes porting easier.
5. **Keep data external.** Shape states should live in JSON, not hardcoded forever.
6. **Use nearest-neighbor only as preprocessing.** Do not rely on runtime nearest mapping.
7. **Measure before optimizing.** Python is probably fast enough for v1.
8. **Avoid raw Xlib for v1.** It is unnecessary friction.
9. **Keep robot-facing behavior safe.** If input stops, the face should gracefully idle instead of freezing in a broken state.

---

## 19. Immediate Next Coding Task

Start with this exact task:

> Create a Python pygame program that draws one filled polygon and morphs it between `neutral`, `circle`, and `heart` states when number keys are pressed.

Do not start with sockets. Do not start with robot deployment. Do not start with C.

First prove the visual morph system.

Minimum code requirements:

- `main.py`
- hardcoded shape dictionary
- `lerp()` function
- `smoothstep()` function
- animation duration variable
- current/start/target vertex arrays
- keyboard-triggered state changes

Once that works, move to JSON-loaded shapes.

---

## 20. Final Recommendation

Build this as a small 2D animation engine:

```text
Python + pygame prototype
JSON rig/state data
Unix socket control
interruptible vertex morphs
object pooling for temporary symbols
resampling later
C++/SDL2 port only if profiling demands it
```

The main engineering risk is not Xorg overhead or Python speed. The main risk is designing sloppy state data and vertex correspondence. Solve the data model cleanly first.

