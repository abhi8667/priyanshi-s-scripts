class InductionSystemError(Exception):
    """Base exception for the application."""
    pass

class ValidationError(InductionSystemError):
    """Raised when incoming data fails validation checks."""
    pass

class DuplicateDataError(InductionSystemError):
    """Raised when conflicting or duplicate records are found."""
    pass

class AllocationError(InductionSystemError):
    """Raised when group or venue allocation fails."""
    pass

class CapacityExceededError(AllocationError):
    """Raised when total student load exceeds total venue capacity."""
    def __init__(self, message: str, required_capacity: int, available_capacity: int):
        super().__init__(message)
        self.required_capacity = required_capacity
        self.available_capacity = available_capacity

class BackupError(InductionSystemError):
    """Raised during database backup or restore failure."""
    pass

class ExportError(InductionSystemError):
    """Raised when file export fails."""
    pass
