"""Constants of the game itself."""

# The simulation advances 16 steps per second, and ladder and multiplayer games run at the "Faster" speed
# setting, which is 1.4x. One second of real time is therefore 22.4 steps.
STEPS_PER_SECOND = 22.4
SECONDS_PER_STEP = 1 / STEPS_PER_SECOND


def steps_to_seconds(steps: float) -> float:
    """Game steps as seconds of real time."""
    return steps * SECONDS_PER_STEP


def seconds_to_steps(seconds: float) -> float:
    """Seconds of real time as game steps, unrounded."""
    return seconds * STEPS_PER_SECOND
