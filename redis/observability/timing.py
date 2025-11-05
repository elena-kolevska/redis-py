"""
Timing utilities for OpenTelemetry metrics collection.

This module provides context managers and helpers for measuring operation durations
with minimal performance overhead.
"""

import time
from typing import Callable, Optional


class Timer:
    """
    Simple timer for measuring operation duration.
    
    Usage:
        timer = Timer()
        timer.start()
        # ... do work ...
        duration = timer.stop()
    """
    
    def __init__(self):
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
    
    def start(self) -> None:
        """Start the timer."""
        self._start_time = time.monotonic()
    
    def stop(self) -> float:
        """
        Stop the timer and return elapsed time.
        
        Returns:
            Elapsed time in seconds
        """
        self._end_time = time.monotonic()
        if self._start_time is None:
            return 0.0
        return self._end_time - self._start_time
    
    def elapsed(self) -> float:
        """
        Get elapsed time without stopping the timer.
        
        Returns:
            Elapsed time in seconds since start
        """
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time
    
    def reset(self) -> None:
        """Reset the timer."""
        self._start_time = None
        self._end_time = None


class TimingContext:
    """
    Context manager for timing operations and recording metrics.
    
    Usage:
        with TimingContext(callback=lambda duration: print(f"Took {duration}s")):
            # ... do work ...
    
    Args:
        callback: Function to call with duration when context exits
        on_error: Optional function to call if an exception occurs
    """
    
    def __init__(
        self,
        callback: Optional[Callable[[float], None]] = None,
        on_error: Optional[Callable[[Exception, float], None]] = None,
    ):
        self.callback = callback
        self.on_error = on_error
        self.timer = Timer()
        self.exception: Optional[Exception] = None
    
    def __enter__(self):
        """Enter the timing context."""
        self.timer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the timing context and record duration."""
        duration = self.timer.stop()
        
        if exc_val is not None:
            self.exception = exc_val
            if self.on_error is not None:
                try:
                    self.on_error(exc_val, duration)
                except Exception:
                    # Don't let metric recording errors mask the original exception
                    pass
        elif self.callback is not None:
            try:
                self.callback(duration)
            except Exception:
                # Don't let metric recording errors crash the application
                pass
        
        # Don't suppress the original exception
        return False


class ConnectionTimingContext:
    """
    Specialized timing context for connection lifecycle tracking.
    
    Tracks:
    - Connection acquisition time (wait time)
    - Connection use time (from acquisition to release)
    
    Usage:
        ctx = ConnectionTimingContext()
        ctx.start_wait()
        # ... wait for connection ...
        ctx.end_wait()
        # ... use connection ...
        ctx.end_use()
        
        wait_time = ctx.get_wait_time()
        use_time = ctx.get_use_time()
    """
    
    def __init__(self):
        self._wait_start: Optional[float] = None
        self._wait_end: Optional[float] = None
        self._use_end: Optional[float] = None
    
    def start_wait(self) -> None:
        """Start timing connection wait/acquisition."""
        self._wait_start = time.monotonic()
    
    def end_wait(self) -> None:
        """End timing connection wait/acquisition."""
        self._wait_end = time.monotonic()
    
    def end_use(self) -> None:
        """End timing connection use."""
        self._use_end = time.monotonic()
    
    def get_wait_time(self) -> Optional[float]:
        """
        Get connection wait time in seconds.
        
        Returns:
            Wait time in seconds, or None if not measured
        """
        if self._wait_start is None or self._wait_end is None:
            return None
        return self._wait_end - self._wait_start
    
    def get_use_time(self) -> Optional[float]:
        """
        Get connection use time in seconds.
        
        Returns:
            Use time in seconds, or None if not measured
        """
        if self._wait_end is None or self._use_end is None:
            return None
        return self._use_end - self._wait_end
    
    def reset(self) -> None:
        """Reset all timings."""
        self._wait_start = None
        self._wait_end = None
        self._use_end = None

