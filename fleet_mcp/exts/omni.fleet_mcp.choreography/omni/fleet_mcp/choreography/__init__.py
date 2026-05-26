try:
    from .extension import FleetChoreographyExtension  # needs omni.ext (Kit runtime)
except Exception:  # plain CPython (headless / unit tests): omni.* absent
    FleetChoreographyExtension = None
