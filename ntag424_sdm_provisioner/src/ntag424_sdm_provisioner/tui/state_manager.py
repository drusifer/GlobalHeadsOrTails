class StateManager:
    """Manages the state transitions of the TUI application."""

    def __init__(self):
        self.current_state = None

    def transition_to(self, state_name: str):
        """Transition to a new state.

        Args:
            state_name (str): The identifier of the state to switch to.
        """
        self.current_state = state_name
