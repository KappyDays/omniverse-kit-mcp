try:
    from .extension import LoadRigExtension  # needs omni.ext (Kit runtime)
except Exception:  # plain CPython (headless / unit tests): omni.* absent
    LoadRigExtension = None
