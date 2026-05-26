try:
    from .extension import SdgDatasetGenExtension  # needs omni.ext (Kit runtime)
except Exception:  # plain CPython (headless / unit tests): omni.* absent
    SdgDatasetGenExtension = None
