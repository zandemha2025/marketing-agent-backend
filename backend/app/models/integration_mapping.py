"""
Integration field mapping model for data transformation between systems.

Manages field mappings and transformation rules for syncing data
between the CDP and external systems like CRMs and data warehouses.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Text, Index, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class MappingDirection(str, Enum):
    """Direction of field mapping."""
    INBOUND = "inbound"       # External -> CDP
    OUTBOUND = "outbound"     # CDP -> External
    BIDIRECTIONAL = "bidirectional"


class TransformationType(str, Enum):
    """Types of field transformations."""
    NONE = "none"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    TRIM = "trim"
    DATE_PARSE = "date_parse"
    DATE_FORMAT = "date_format"
    NUMBER_PARSE = "number_parse"
    BOOLEAN_PARSE = "boolean_parse"
    JSON_PARSE = "json_parse"
    CONCATENATE = "concatenate"
    SPLIT = "split"
    LOOKUP = "lookup"
    CUSTOM = "custom"


class ConflictStrategy(str, Enum):
    """Strategies for resolving data conflicts."""
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    TIMESTAMP_WINS = "timestamp_wins"
    MERGE = "merge"
    MANUAL = "manual"


class IntegrationMapping(Base):
    """
    Field mapping configuration for integration data sync.
    
    Defines how fields map between external systems and the CDP:
    - Source entity/field to target entity/field mapping
    - Transformation rules for data conversion
    - Conflict resolution strategies
    - Validation rules
    """
    
    # Integration reference
    integration_id = Column(String(12), ForeignKey("integrations.id"), nullable=False, index=True)
    
    # Entity mapping
    source_entity = Column(String(100), nullable=False)  # e.g., "Contact", "Lead"
    target_entity = Column(String(100), nullable=False)  # e.g., "customer", "lead"
    
    # Mapping direction
    direction = Column(
        SQLEnum(MappingDirection),
        default=MappingDirection.BIDIRECTIONAL,
        nullable=False
    )
    
    # Field mappings
    # Example: {
    #     "FirstName": "first_name",
    #     "LastName": "last_name",
    #     "Email": "email",
    #     "Company.Name": "company_name",
    #     "Phone": "phone"
    # }
    field_mappings = Column(JSON, default=dict, nullable=False)
    
    # Transformation rules
    # Example: {
    #     "first_name": {
    #         "type": "uppercase",
    #         "params": {}
    #     },
    #     "phone": {
    #         "type": "custom",
    #         "params": {"pattern": "^\\+1[0-9]{10}$"}
    #     }
    # }
    transformation_rules = Column(JSON, default=dict, nullable=False)
    
    # Default values for missing fields
    # Example: {
    #     "source": "salesforce",
    #     "status": "active"
    # }
    default_values = Column(JSON, default=dict, nullable=False)
    
    # Required fields validation
    # Example: ["email", "first_name"]
    required_fields = Column(JSON, default=list, nullable=False)
    
    # Field validation rules
    # Example: {
    #     "email": {"type": "email", "required": true},
    #     "phone": {"type": "phone", "pattern": "^\\+?[0-9]{10,15}$"}
    # }
    validation_rules = Column(JSON, default=dict, nullable=False)
    
    # Conflict resolution strategy
    conflict_strategy = Column(
        SQLEnum(ConflictStrategy),
        default=ConflictStrategy.TIMESTAMP_WINS,
        nullable=False
    )
    
    # Custom conflict resolution logic
    conflict_resolution_script = Column(Text, nullable=True)
    
    # Filter conditions for sync
    # Example: {
    #     "source_filter": "IsActive = true AND CreatedDate > 2024-01-01",
    #     "target_filter": {"status": "active"}
    # }
    filter_conditions = Column(JSON, default=dict, nullable=False)
    
    # Mapping metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # Higher = applied first
    
    # Sync options
    sync_on_create = Column(Boolean, default=True, nullable=False)
    sync_on_update = Column(Boolean, default=True, nullable=False)
    sync_on_delete = Column(Boolean, default=False, nullable=False)  # Dangerous!
    
    # Version control
    version = Column(Integer, default=1, nullable=False)
    previous_version_id = Column(String(12), ForeignKey("integration_mappings.id"), nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    integration = relationship("Integration", back_populates="mappings")
    previous_version = relationship("IntegrationMapping", remote_side=[id])
    
    # Indexes
    __table_args__ = (
        Index('idx_mapping_integration_entity', 'integration_id', 'source_entity', 'target_entity'),
        Index('idx_mapping_direction', 'direction'),
        Index('idx_mapping_active', 'is_active'),
    )
    
    def apply_mapping(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply field mapping to source data.
        
        Args:
            source_data: Raw data from source system
            
        Returns:
            Mapped data with transformations applied
        """
        result = {}
        
        for source_field, target_field in self.field_mappings.items():
            # Get value from source (support nested paths like "Company.Name")
            value = self._get_nested_value(source_data, source_field)
            
            # Apply transformation if configured
            if target_field in self.transformation_rules:
                value = self._apply_transformation(
                    value, 
                    self.transformation_rules[target_field]
                )
            
            # Set value in result (support nested paths)
            self._set_nested_value(result, target_field, value)
        
        # Apply default values
        for field, default_value in self.default_values.items():
            if field not in result or result[field] is None:
                result[field] = default_value
        
        return result
    
    def apply_reverse_mapping(self, target_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply reverse field mapping (CDP -> External).
        
        Args:
            target_data: Data from CDP
            
        Returns:
            Mapped data for external system
        """
        result = {}
        
        # Reverse the mapping
        reverse_mappings = {v: k for k, v in self.field_mappings.items()}
        
        for target_field, source_field in reverse_mappings.items():
            value = self._get_nested_value(target_data, target_field)
            self._set_nested_value(result, source_field, value)
        
        return result
    
    def validate_data(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Validate data against mapping rules.
        
        Args:
            data: Data to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in data or data[field] is None:
                errors.append({
                    "field": field,
                    "error": "Required field is missing",
                    "rule": "required"
                })
        
        # Apply validation rules
        for field, rules in self.validation_rules.items():
            if field in data and data[field] is not None:
                value = data[field]
                
                # Type validation
                if rules.get("type") == "email":
                    if not self._is_valid_email(value):
                        errors.append({
                            "field": field,
                            "error": "Invalid email format",
                            "value": value
                        })
                
                # Pattern validation
                if "pattern" in rules:
                    import re
                    if not re.match(rules["pattern"], str(value)):
                        errors.append({
                            "field": field,
                            "error": f"Value does not match pattern: {rules['pattern']}",
                            "value": value
                        })
        
        return errors
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def _apply_transformation(self, value: Any, rule: Dict[str, Any]) -> Any:
        """Apply transformation rule to value."""
        if value is None:
            return None
        
        transform_type = rule.get("type", TransformationType.NONE)
        params = rule.get("params", {})
        
        if transform_type == TransformationType.UPPERCASE:
            return str(value).upper() if value else value
        elif transform_type == TransformationType.LOWERCASE:
            return str(value).lower() if value else value
        elif transform_type == TransformationType.TRIM:
            return str(value).strip() if value else value
        elif transform_type == TransformationType.DATE_PARSE:
            # Parse date from various formats
            from dateutil import parser
            try:
                return parser.parse(str(value)).isoformat()
            except:
                return value
        elif transform_type == TransformationType.NUMBER_PARSE:
            try:
                return float(value)
            except:
                return value
        elif transform_type == TransformationType.BOOLEAN_PARSE:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        elif transform_type == TransformationType.CONCATENATE:
            separator = params.get("separator", " ")
            fields = params.get("fields", [])
            return separator.join(str(value) for value in fields if value)
        
        return value
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, str(email)))
    
    def record_usage(self) -> None:
        """Record that this mapping was used."""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "integration_id": self.integration_id,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "direction": self.direction.value if self.direction else None,
            "field_mappings": self.field_mappings,
            "transformation_rules": self.transformation_rules,
            "default_values": self.default_values,
            "required_fields": self.required_fields,
            "validation_rules": self.validation_rules,
            "conflict_strategy": self.conflict_strategy.value if self.conflict_strategy else None,
            "filter_conditions": self.filter_conditions,
            "description": self.description,
            "is_active": self.is_active,
            "priority": self.priority,
            "sync_on_create": self.sync_on_create,
            "sync_on_update": self.sync_on_update,
            "sync_on_delete": self.sync_on_delete,
            "version": self.version,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
