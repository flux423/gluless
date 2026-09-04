from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

class SideEffectType(str, Enum):
    NONE = "none"
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXTERNAL_MESSAGE = "external_message"
    FINANCIAL = "financial"
    PRIVILEGE_CHANGE = "privilege_change"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"

class UtilityType(str, Enum):
    READ = "read"
    MUTATION = "mutation"
    STREAM = "stream"

@dataclass
class UtilityTransport:
    type: str  # e.g., "openapi"
    method: str  # GET, POST, etc.
    path: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Utility:
    id: str  # e.g., "GasCity.cities.list"
    name: str  # e.g., "cities.list"
    namespace: str  # e.g., "GasCity"
    description: str
    type: UtilityType
    side_effects: SideEffectType
    transport: UtilityTransport
    auth: List[Dict[str, Any]] = field(default_factory=list)
