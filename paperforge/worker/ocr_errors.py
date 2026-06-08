from __future__ import annotations


class OCRRecoverableError(Exception):
    pass


class OCRFatalError(Exception):
    pass


class OCRNetworkError(OCRRecoverableError):
    pass


class OCRAPISchemaError(OCRRecoverableError):
    pass


class OCRPDFResolveError(OCRFatalError):
    pass


class OCRPostprocessError(OCRFatalError):
    pass


class OCRArtifactIntegrityError(OCRFatalError):
    pass


def classify_ocr_error(exc: Exception, *, stage: str) -> dict:
    retryable = isinstance(exc, OCRRecoverableError)
    return {
        "status": "retryable_error" if retryable else "fatal_error",
        "error_type": exc.__class__.__name__,
        "error_stage": stage,
        "retryable": retryable,
        "last_error": str(exc),
    }


def normalize_ocr_status_for_reader(status: str) -> str:
    if status in {"retryable_error", "fatal_error"}:
        return "error"
    if status == "done_degraded":
        return "done"
    return status
