import jwt
import datetime
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bi_mat_quoc_gia_123'

users = {
    "admin_user": {"password": "123", "role": "admin", "scopes": ["read", "write", "delete"]},
    "guest_user": {"password": "456", "role": "user", "scopes": ["read"]}
}

def create_tokens(user_id, role, scopes):
    access_payload = {
        "user_id": user_id,
        "role": role,
        "scopes": scopes,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    }
    access_token = jwt.encode(access_payload, app.config['SECRET_KEY'], algorithm="HS256")

    refresh_payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    refresh_token = jwt.encode(refresh_payload, app.config['SECRET_KEY'], algorithm="HS256")
    
    return access_token, refresh_token

def authorize(required_role=None, required_scope=None):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                token = auth_header.split(" ")[1] if " " in auth_header else None

            if not token:
                return jsonify({"msg": "Missing Bearer Token"}), 401

            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                
                if required_role and data.get('role') != required_role:
                    return jsonify({"msg": f"Yêu cầu vai trò {required_role}"}), 403
                
                # Kiểm tra Scope (Ví dụ: phải có quyền 'write')
                if required_scope and required_scope not in data.get('scopes', []):
                    return jsonify({"msg": f"Thiếu quyền: {required_scope}"}), 403
                
                current_user = data['user_id']
            except Exception as e:
                return jsonify({"msg": "Token không hợp lệ hoặc hết hạn", "error": str(e)}), 401

            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

@app.route('/login', methods=['POST'])
def login():
    auth = request.json
    user = users.get(auth.get('username'))
    
    if user and user['password'] == auth.get('password'):
        access, refresh = create_tokens(auth['username'], user['role'], user['scopes'])
        return jsonify({
            "token_type": "Bearer",
            "access_token": access,
            "refresh_token": refresh
        })
    
    return jsonify({"msg": "Sai tài khoản"}), 401

@app.route('/refresh', methods=['POST'])
def refresh():
    refresh_token = request.json.get('refresh_token')
    try:
        data = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user_id = data['user_id']
        user = users[user_id]
        new_access, _ = create_tokens(user_id, user['role'], user['scopes'])
        return jsonify({"access_token": new_access})
    except:
        return jsonify({"msg": "Refresh token không hợp lệ"}), 401

@app.route('/admin-only')
@authorize(required_role="admin")
def admin_api(current_user):
    return jsonify({"msg": f"Chào Admin {current_user}, bạn có quyền tối cao!"})

@app.route('/write-data')
@authorize(required_scope="write")
def write_api(current_user):
    return jsonify({"msg": f"User {current_user} có quyền Ghi (Scope: write)"})