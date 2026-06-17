"""JSON Schema for scenario YAML validation."""

from __future__ import annotations

SCENARIO_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/isaacsim/scenario.schema.json",
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
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "external_search"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/externalAssetSearchArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "external_download"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/externalAssetDownloadArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "external_convert"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/externalAssetConvertArgs"}
                        }
                    },
                },
            ],
        },
        "externalAssetSearchArgs": {
            "type": "object",
            "required": ["query"],
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "providers": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1},
            },
        },
        "externalAssetDownloadArgs": {
            "type": "object",
            "required": ["provider", "asset_id"],
            "additionalProperties": False,
            "properties": {
                "provider": {"type": "string", "minLength": 1},
                "asset_id": {"type": "string", "minLength": 1},
                "format_preference": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "externalAssetConvertArgs": {
            "type": "object",
            "required": ["manifest_path"],
            "additionalProperties": False,
            "properties": {
                "manifest_path": {"type": "string", "minLength": 1},
                "output_format": {"type": "string", "enum": ["usd"]},
                "timeout_s": {"type": "number", "minimum": 1},
            },
        },
    },
}
