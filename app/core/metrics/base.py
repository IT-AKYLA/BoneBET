from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMetric(ABC):
    """Abstract base class for metrics."""
    
    name: str = "base"
    description: str = "Base metric"
    
    @abstractmethod
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metric from input data."""
        pass
    
    @abstractmethod
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate that required data is present."""
        pass
    
    def get_required_fields(self) -> List[str]:
        """Return list of required fields."""
        return []