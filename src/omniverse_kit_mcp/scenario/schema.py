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
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "official_sync_status"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/officialAssetSyncStatusArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "official_search"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/officialAssetSearchArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "official_resolve"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/officialAssetResolveArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "official_get"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/officialAssetGetArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "asset"},
                            "action": {"const": "official_verify"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/officialAssetVerifyArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "viewport"},
                            "action": {"const": "capture"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/viewportCaptureArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "viewport"},
                            "action": {"const": "frame_prims"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/viewportFramePrimsArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "viewport"},
                            "action": {"const": "capture_assert"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/viewportCaptureAssertArgs"}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "module": {"const": "sensor"},
                            "action": {"const": "lidar_get_point_cloud"},
                        },
                        "required": ["module", "action"],
                    },
                    "then": {
                        "properties": {
                            "args": {"$ref": "#/$defs/sensorLidarPointCloudArgs"}
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
        "officialAssetStatus": {
            "type": "string",
            "enum": [
                "failed",
                "stale",
                "discovered",
                "url_validated",
                "inspect_verified",
                "load_verified",
                "assign_verified",
            ],
        },
        "officialAssetSyncStatusArgs": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "app_profile": {"type": "string", "minLength": 1},
            },
        },
        "officialAssetSearchArgs": {
            "type": "object",
            "required": ["query"],
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "kind": {"type": "string", "enum": ["asset", "material"]},
                "app_profile": {"type": "string", "minLength": 1},
                "provider": {"type": "string", "minLength": 1},
                "min_status": {"$ref": "#/$defs/officialAssetStatus"},
                "allow_stale": {"type": "boolean"},
                "limit": {"type": "integer", "minimum": 1},
            },
        },
        "officialAssetResolveArgs": {
            "type": "object",
            "required": ["name_or_id"],
            "additionalProperties": False,
            "properties": {
                "name_or_id": {"type": "string", "minLength": 1},
                "kind": {"type": "string", "enum": ["asset", "material"]},
                "app_profile": {"type": "string", "minLength": 1},
                "prefer_loadable": {"type": "boolean"},
            },
        },
        "officialAssetGetArgs": {
            "type": "object",
            "required": ["asset_id"],
            "additionalProperties": False,
            "properties": {
                "asset_id": {"type": "string", "minLength": 1},
                "app_profile": {"type": "string", "minLength": 1},
            },
        },
        "officialAssetVerifyArgs": {
            "type": "object",
            "required": ["asset_id"],
            "additionalProperties": False,
            "properties": {
                "asset_id": {"type": "string", "minLength": 1},
                "app_profile": {"type": "string", "minLength": 1},
                "timeout_s": {"type": "number", "minimum": 1},
            },
        },
        "viewportCaptureArgs": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "viewport_name": {"type": "string"},
                "camera_prim_path": {"type": ["string", "null"]},
                "renderer": {"type": "string", "enum": ["rtx", "hydra"]},
                "width": {"type": "integer", "minimum": 1},
                "height": {"type": "integer", "minimum": 1},
                "samples_per_pixel": {"type": "integer", "minimum": 1},
                "settle_frames": {"type": "integer", "minimum": 0},
                "output_format": {"type": "string", "enum": ["png", "jpg"]},
                "transparent_background": {"type": "boolean"},
                "warmup_frames": {"type": "integer", "minimum": 0},
                "return_stats": {"type": "boolean"},
            },
        },
        "viewportFramePrimsArgs": {
            "type": "object",
            "required": ["prim_paths"],
            "additionalProperties": False,
            "properties": {
                "prim_paths": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "minLength": 1},
                },
                "viewport_name": {"type": "string"},
                "camera_path": {"type": ["string", "null"]},
                "include_purposes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "margin": {"type": "number", "minimum": 0},
                "fov_deg": {"type": "number", "exclusiveMinimum": 0},
                "view_direction": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {"type": "number"},
                },
                "up": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {"type": "number"},
                },
                "set_camera": {"type": "boolean"},
            },
        },
        "viewportCaptureAssertArgs": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "viewport_name": {"type": "string"},
                "camera_prim_path": {"type": ["string", "null"]},
                "renderer": {"type": "string", "enum": ["rtx", "hydra"]},
                "width": {"type": "integer", "minimum": 1},
                "height": {"type": "integer", "minimum": 1},
                "samples_per_pixel": {"type": "integer", "minimum": 1},
                "settle_frames": {"type": "integer", "minimum": 0},
                "output_format": {"type": "string", "enum": ["png", "jpg"]},
                "transparent_background": {"type": "boolean"},
                "warmup_frames": {"type": "integer", "minimum": 0},
                "min_mean": {"type": "number", "minimum": 0},
                "min_variance": {"type": "number", "minimum": 0},
            },
        },
        "sensorLidarPointCloudArgs": {
            "type": "object",
            "required": ["sensor_prim"],
            "additionalProperties": False,
            "properties": {
                "sensor_prim": {"type": "string", "minLength": 1},
                "max_points": {
                    "oneOf": [
                        {"type": "integer", "minimum": 1},
                        {
                            "type": "string",
                            "pattern": (
                                r"^\$\{variables\.[A-Za-z_][A-Za-z0-9_]*\}$"
                            ),
                        },
                    ]
                },
                "frames_to_wait": {
                    "oneOf": [
                        {"type": "integer", "minimum": 1},
                        {
                            "type": "string",
                            "pattern": (
                                r"^\$\{variables\.[A-Za-z_][A-Za-z0-9_]*\}$"
                            ),
                        },
                    ]
                },
                "min_points": {
                    "oneOf": [
                        {"type": "integer", "minimum": 0},
                        {
                            "type": "string",
                            "pattern": (
                                r"^\$\{variables\.[A-Za-z_][A-Za-z0-9_]*\}$"
                            ),
                        },
                    ]
                },
                "fail_on_warning": {"type": "boolean"},
            },
        },
    },
}
