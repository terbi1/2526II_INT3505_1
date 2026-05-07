from flask import jsonify
import datetime

def success_response(data: dict, meta: dict = None) -> dict:
    """Response thành công chuẩn hóa."""
    response = {
        "status": "success",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "data": data
    }
    if meta:
        response["meta"] = meta
    return response

def error_response(
    code: str,
    message: str,
    details: dict = None,
    http_status: int = 400
) -> tuple:
    """Response lỗi chuẩn hóa."""
    response = {
        "status": "error",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        response["error"]["details"] = details
    return response, http_status