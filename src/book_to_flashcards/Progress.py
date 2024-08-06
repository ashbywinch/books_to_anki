from typing import Any


class Progress:
    """this class lets us separate progress bar initialisation from the code where we discover how many steps there are"""

    bar = None
    num_steps = 0

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        self.bar()
