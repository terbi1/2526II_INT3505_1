import jwt
import datetime
from flask import Flask, request, jsonify
from functools import wraps
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_duper_secret_key'

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
    
    return jsonify({"msg": "Wrong credentials"}), 401

@app.route('/refresh', methods=['POST'])
def refresh():
    refresh_token = request.json.get('refresh_token')
    try:
        data = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user_id = data['user_id']
        user = users[user_id]
        new_access, _ = create_tokens(user_id, user['role'], user['scopes'])
        return jsonify({"access_token": new_access,"user_id":user_id, "role": user["role"], "scope": user["scope"]})
    except:
        return jsonify({"msg": "Refresh token invalid"}), 401

@app.route('/admin-only')
@authorize(required_role="admin")
def admin_api(current_user):
    return jsonify({"msg": f"Oh hi Admin {current_user}, !"})

@app.route('/write-data')
@authorize(required_scope="write")
def write_api(current_user):
    return jsonify({"msg": f"User {current_user} có quyền Ghi (Scope: write)"})

opaque_token_store = {}

def opaque_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            token = auth_header.split(" ")[1] if " " in auth_header else None

        if not token:
            return jsonify({"msg": "Missing Opaque Token"}), 401

        user_id = opaque_token_store.get(token)
        
        if not user_id:
            return jsonify({"msg": "Opaque Token không tồn tại hoặc đã bị thu hồi"}), 401

        return f(user_id, *args, **kwargs)
    return decorated

# ==========================================
# OPAQUE TOKEN: ENDPOINTS
# ==========================================
@app.route('/login-opaque', methods=['POST'])
def login_opaque():
    auth = request.json
    user = users.get(auth.get('username'))
    
    if user and user['password'] == auth.get('password'):
        opaque_token = secrets.token_hex(32)
        
        opaque_token_store[opaque_token] = auth['username']
        
        return jsonify({
            "token_type": "Bearer",
            "opaque_token": opaque_token,
        })
    
    return jsonify({"msg": "Wrong credentials"}), 401

@app.route('/opaque-data')
@opaque_token_required
def opaque_api(current_user):
    return jsonify({
        "msg": f"Hi {current_user}!"
    })

@app.route('/logout-opaque', methods=['POST'])
@opaque_token_required
def logout_opaque(current_user):
    token = request.headers['Authorization'].split(" ")[1]
    
    if token in opaque_token_store:
        del opaque_token_store[token]
        
    return jsonify({"msg": f"Logged out {current_user} and revoked token!"})