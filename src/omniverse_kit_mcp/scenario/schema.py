"""JSON Schema for scenario YAML validation."""

from __future__ import annotations

SCENARIO_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["apiVersion", "kind", "metadata", "spec"],
    "additionalProperties": False,
    "properties": {
        "apiVersion": {"const": "isaacsim.validation/v1"},
        "kind": {"const": "Scenario"},
        "metadata": {
            "type": "object",
            "required": ["id", "name"],
            "additionalProperties": False,
            "properties": {
                "id": {"type": "string", "pattern": "^[a-zA-Z0-9_.-]+$"},
                "name": {"type": "string", "minLength": 1},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
        "spec": {
            "type": "object",
            "required": ["assert"],
            "additionalProperties": False,
            "properties": {
                "defaults": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "stepTimeoutSeconds": {"type": "number", "minimum": 1},
                        "failFast": {"type": "boolean"},
                    },
                },
                "variables": {"type": "object", "additionalProperties": True},
                "arrange": {"$ref": "#/$defs/stepList"},
                "act": {"$ref": "#/$defs/stepList"},
                "assert": {"$ref": "#/$defs/stepList"},
                "cleanup": {"$ref": "#/$defs/stepList"},
            },
        },
    },
    "$defs": {
        "stepList": {"type": "array", "items": {"$ref": "#/$defs/step"}},
        "step": {
            "type": "object",
            "required": ["id", "module", "action", "args"],
            "additionalProperties": False,
            "properties": {
                "id": {"type": "string"},
                "module": {
                    "type": "string",
                    "enum": [
                        "stage",
                        "viewport",
                        "lakehouse",
                        "extension",
                        "simulation",
                        "robot",
                        "job",
                        "asset",
                        "character",
                        "window",
                        "navigation",
                        "sensor",
                        "physics",
                        "lighting",
                        "material",
                        "replicator",
                        "omnigraph",
                        "content",
                    ],
                },
                "action": {"type": "string"},
                "args": {"type": "object"},
                "timeoutSeconds": {"type": "number", "minimum": 1},
                "continueOnFailure": {"type": "boolean"},
                "idempotent": {"type": "boolean"},
                "retries": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "maxAttempts": {"type": "integer", "minimum": 1},
                        "initialBackoffSeconds": {"type": "number", "minimum": 0},
                        "maxBackoffSeconds": {"type": "number", "minimum": 0},
                    },
                },
            },
        },
    },
}
