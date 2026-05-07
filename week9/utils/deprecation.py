from functools import wraps
from flask import jsonify, request
import datetime
import logging

logger = logging.getLogger(__name__)

def deprecated(
    sunset_date: str,
    migration_guide: str,
    successor_version: str = None
):
    """
    Decorator đánh dấu một endpoint là deprecated.
    
    Args:
        sunset_date: Ngày endpoint bị tắt (ISO format: YYYY-MM-DD)
        migration_guide: URL hướng dẫn migration
        successor_version: Phiên bản thay thế (vd: 'v2')
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Tính số ngày còn lại trước khi sunset
            sunset = datetime.date.fromisoformat(sunset_date)
            today = datetime.date.today()
            days_remaining = (sunset - today).days

            # Log cảnh báo
            logger.warning(
                f"DEPRECATED endpoint called: {request.path} | "
                f"Sunset: {sunset_date} | "
                f"Client: {request.remote_addr}"
            )

            # Thực thi handler gốc
            response = f(*args, **kwargs)

            # Nếu response là tuple (data, status_code)
            if isinstance(response, tuple):
                data, status_code = response
            else:
                data, status_code = response, 200

            # Tạo Flask response để thêm headers
            from flask import make_response
            resp = make_response(jsonify(data), status_code)

            # ---- Thêm Deprecation Headers (RFC 8594) ----
            resp.headers["Deprecation"] = f"date=\"{today.isoformat()}\""
            resp.headers["Sunset"] = sunset_date
            resp.headers["Link"] = (
                f'<{migration_guide}>; rel="deprecation"; '
                f'type="text/html"'
            )
            if successor_version:
                base_url = request.base_url
                # Thay v1 → v2 trong URL gợi ý
                new_url = base_url.replace("v1", successor_version)
                resp.headers["X-Migration-URL"] = new_url
            
            resp.headers["X-Days-Until-Sunset"] = str(max(0, days_remaining))
            resp.headers["Warning"] = (
                f'299 - "This API version is deprecated and will be '
                f'removed on {sunset_date}. '
                f'Please migrate to {successor_version}."'
            )

            return resp
        return wrapper
    return decorator