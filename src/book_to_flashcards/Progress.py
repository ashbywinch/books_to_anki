# ruff: noqa: N999  # public module name, imported as book_to_flashcards.Progress
from __future__ import annotations

"""Provides a simple wrapper for managing progress bar updates.

This module contains the `Progress` class, designed to decouple the point of
progress bar initialization (which requires knowing the total number of steps)
from the point where progress updates occur. This allows for cleaner integration
of progress bars like `alive_progress` into iterative processes.
"""
from typing import Any, Callable


class Progress:
    """A callable wrapper to manage and advance an externally initialized progress bar.

    This class acts as a placeholder for a possible progress bar instance (e.g., from
    `alive_progress`). The typical usage pattern is:
    1. Create an instance: `prog = Progress()`
    2. At a later point, when the total number of steps is known, set `prog.num_steps`
    3. Initialize `prog.bar` with a configured progress bar object:
       `prog.bar = alive_progress.alive_bar(prog.num_steps, ...)`
    4. In a loop or iterative process, call the instance to advance the bar:
       `prog()`

    This is an ugly workaround for needing to use a global progress bar, meaning
    we have to initialise it long before we know the total number of steps or whether
    it needs to exist at all.
    """

    bar: Callable[[], None] | None = None
    num_steps: int = 0

    def __call__(self, *args: Any, **kwds: Any) -> None:
        """Advances the progress bar if it has been initialized.
        
        This method calls the underlying progress bar object stored in `self.bar`.
        Any arguments or keyword arguments passed to this call are ignored.
        """
        if self.bar:
            self.bar()
