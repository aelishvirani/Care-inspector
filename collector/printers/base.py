from abc import ABC, abstractmethod
from typing import Any, Dict


class PrinterDriver(ABC):
    """
    Common interface for every Care-Inspector printer source.

    Implementations:
    - SimulatorPrinter
    - HitachiModbusPrinter
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the printer or simulator."""
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect cleanly."""
        raise NotImplementedError

    @abstractmethod
    async def read_measurement(self) -> Dict[str, Any]:
        """
        Read one normalized measurement.

        All printer drivers should return the same structure so the backend
        does not need to know whether data came from a simulator or real printer.
        """
        raise NotImplementedError
