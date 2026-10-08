from time import perf_counter

from starlette.middleware.base import (
    BaseHTTPMiddleware,
)

from .audit import write_audit_event
from .auth import decode_access_token


IGNORED_GET_PATHS = {
    "/health",
    "/api/auth/me",
    "/api/secure/devices",
    "/api/secure/customers",
    "/api/secure/admin/audit-log",
}

DEDICATED_AUDIT_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
}


class AuditMiddleware(
    BaseHTTPMiddleware
):
    async def dispatch(
        self,
        request,
        call_next,
    ):
        started = perf_counter()

        if request.method == "OPTIONS":
            return await call_next(
                request
            )

        ignore_successful_get = (
            request.method == "GET"
            and request.url.path
            in IGNORED_GET_PATHS
        )

        dedicated_audit_path = (
            request.url.path
            in DEDICATED_AUDIT_PATHS
        )

        actor_email = "ANONYMOUS"
        actor_role = "ANONYMOUS"

        authorization = (
            request.headers.get(
                "authorization"
            )
        )

        if (
            authorization
            and authorization.lower()
            .startswith("bearer ")
        ):
            token = (
                authorization
                .split(" ", 1)[1]
            )

            try:
                payload = (
                    decode_access_token(
                        token
                    )
                )

                actor_email = (
                    payload.get("email")
                    or "UNKNOWN"
                )

                actor_role = (
                    payload.get("role")
                    or "UNKNOWN"
                )

            except Exception:
                actor_email = (
                    "INVALID_TOKEN"
                )

                actor_role = (
                    "ANONYMOUS"
                )

        try:
            response = await call_next(
                request
            )

        except Exception as exc:
            duration_ms = (
                perf_counter()
                - started
            ) * 1000

            write_audit_event(
                actor_email=actor_email,
                actor_role=actor_role,
                category="HTTP",
                action="API_REQUEST",
                outcome="FAILURE",
                request=request,
                status_code=500,
                details=(
                    f"{duration_ms:.1f} ms"
                ),
                error_message=str(exc),
            )

            raise

        if dedicated_audit_path:
            return response

        if (
            ignore_successful_get
            and response.status_code
            < 400
        ):
            return response

        duration_ms = (
            perf_counter()
            - started
        ) * 1000

        write_audit_event(
            actor_email=actor_email,
            actor_role=actor_role,
            category=(
                "SECURITY"
                if response.status_code
                in {401, 403}
                else "HTTP"
            ),
            action=(
                "ACCESS_DENIED"
                if response.status_code
                in {401, 403}
                else "API_REQUEST"
            ),
            outcome=(
                "SUCCESS"
                if response.status_code < 400
                else "FAILURE"
            ),
            request=request,
            status_code=(
                response.status_code
            ),
            details=(
                f"{duration_ms:.1f} ms"
            ),
        )

        return response
