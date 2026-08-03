from abc import ABC, abstractmethod


class Plugin(ABC):
    """Contract implemented by each track-processing module."""

    NAME = None
    VERSION = None

    @abstractmethod
    def needs_processing(self, document, track):
        """Return whether this plugin should process a track document."""

    @abstractmethod
    def process(self, document, track):
        """Update the supplied track document in place."""
