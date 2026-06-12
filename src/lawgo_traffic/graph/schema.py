from enum import StrEnum


class NodeType(StrEnum):
    DOCUMENT = "Document"
    ARTICLE = "Article"
    CLAUSE = "Clause"
    POINT = "Point"
    VIOLATION = "Violation"
    PENALTY = "Penalty"
    VEHICLE_TYPE = "VehicleType"
    AUTHORITY = "Authority"
    RIGHT = "Right"
    PROCEDURE = "Procedure"
    CONDITION = "Condition"
    LEGAL_CONCEPT = "LegalConcept"


class EdgeType(StrEnum):
    HAS_ARTICLE = "HAS_ARTICLE"
    HAS_CLAUSE = "HAS_CLAUSE"
    HAS_POINT = "HAS_POINT"
    REGULATES = "REGULATES"
    HAS_PENALTY = "HAS_PENALTY"
    HAS_ADDITIONAL_PENALTY = "HAS_ADDITIONAL_PENALTY"
    APPLIES_TO = "APPLIES_TO"
    HAS_CONDITION = "HAS_CONDITION"
    HAS_AUTHORITY = "HAS_AUTHORITY"
    HAS_RIGHT = "HAS_RIGHT"
    HAS_PROCEDURE = "HAS_PROCEDURE"
    REFERENCES = "REFERENCES"
    AMENDS = "AMENDS"
    REPLACES = "REPLACES"
