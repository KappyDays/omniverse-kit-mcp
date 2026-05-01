"""Extension lifecycle — registers REST endpoints on omni.services."""

import traceback

import carb
import omni.ext


class ValidationApiExtension(omni.ext.IExt):

    ROUTER_PREFIX = "/validation/v1"

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn("[validation_api] on_startup called")
        self._ext_id = ext_id

        # Import router
        try:
            from .rest_router import router, get_log_capture_service
            carb.log_warn(f"[validation_api] router imported — {len(router.routes)} routes")
        except Exception:
            carb.log_error("[validation_api] FAIL import rest_router:\n" + traceback.format_exc())
            return

        # Register via get_app().include_router()
        try:
            import omni.services.core.main as svc
            app = svc.get_app()
            app.include_router(router, prefix=self.ROUTER_PREFIX)
            carb.log_warn("[validation_api] SUCCESS — routes registered at " + self.ROUTER_PREFIX)
        except Exception:
            carb.log_error("[validation_api] FAIL register:\n" + traceback.format_exc())

        # 2026-04-20 임시 disable — carb log callback 이 MDL resolver loop 시 대량 호출되어
        # Kit main loop 를 경합. GUI drag&drop 이 Extension 기동 Kit 에서 hang 되는 원인 의심.
        self._log_capture = None

    def on_shutdown(self) -> None:
        carb.log_warn("[validation_api] on_shutdown called")
        # Phase D: release the carb log hook so it does not dangle across reloads.
        try:
            cap = getattr(self, "_log_capture", None)
            if cap is not None:
                cap.stop()
        except Exception:
            carb.log_error("[validation_api] FAIL stop log_capture:\n" + traceback.format_exc())
