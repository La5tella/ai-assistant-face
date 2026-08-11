class ThinkingManager:
    """Temporarily repurpose the eye objects as a sequenced thinking indicator."""

    def __init__(
        self,
        role_objects,
        apply_object_state,
        animation_name="thinking",
        sequence_delay=0.2,
    ):
        self.role_objects = dict(role_objects)
        self.apply_object_state = apply_object_state
        self.animation_name = animation_name
        self.default_sequence_delay = sequence_delay
        self.active = False
        self.controlled_objects = []

    def activate(
        self,
        role_states,
        duration=0.25,
        easing="ease",
        sequence_delay=None,
    ):
        """Move controlled objects into dot positions and stagger their animations."""
        delay_step = (
            self.default_sequence_delay
            if sequence_delay is None
            else sequence_delay
        )
        if delay_step < 0:
            raise ValueError("sequence_delay must be zero or greater")

        prepared_roles = []
        seen_sequences = set()

        for role, state_data in role_states.items():
            if role not in self.role_objects:
                raise ValueError(f"No thinking object is assigned to role: {role}")

            sequence = state_data.get("sequence")
            if not isinstance(sequence, int) or sequence < 0:
                raise ValueError(
                    f"Thinking role '{role}' requires a non-negative integer sequence"
                )
            if sequence in seen_sequences:
                raise ValueError(f"Duplicate thinking sequence number: {sequence}")

            seen_sequences.add(sequence)
            object_state = {
                key: value
                for key, value in state_data.items()
                if key not in {"controller", "sequence"}
            }
            prepared_roles.append(
                (sequence, self.role_objects[role], object_state)
            )

        self.deactivate()
        self.controlled_objects = []

        for sequence, obj, object_state in sorted(prepared_roles):
            obj.curr_anim = None
            self.apply_object_state(obj, object_state, duration, easing)
            obj.active = True
            obj.curr_anim = self.animation_name
            obj.anim.start_delay = sequence * delay_step
            self.controlled_objects.append(obj)

        self.active = True

    def deactivate(self, preserve_visual_position=False):
        """Stop the thinking animation and release every repurposed object."""
        for obj in self.controlled_objects:
            if preserve_visual_position:
                obj.preserve_animation_offset()
            obj.curr_anim = None
            obj.active = False

        self.controlled_objects = []
        self.active = False
