from flask import Flask, jsonify, request

app = Flask(__name__)

# Mock database
tasks = [
    {"id": 1, "title": "Học API Testing", "done": False}
]

# 1. GET /tasks - Lấy danh sách task
@app.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks), 200

# 2. GET /tasks/<id> - Lấy thông tin 1 task
@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task:
        return jsonify(task), 200
    return jsonify({"error": "Task not found"}), 404

# 3. POST /tasks - Tạo mới task
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    new_id = tasks[-1]['id'] + 1 if tasks else 1
    new_task = {
        "id": new_id,
        "title": data.get('title', 'Untitled'),
        "done": False
    }
    tasks.append(new_task)
    return jsonify(new_task), 201

# 4. PUT /tasks/<id> - Cập nhật task
@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    
    data = request.get_json()
    task['title'] = data.get('title', task['title'])
    task['done'] = data.get('done', task['done'])
    return jsonify(task), 200

# 5. DELETE /tasks/<id> - Xóa task
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    initial_len = len(tasks)
    tasks = [t for t in tasks if t['id'] != task_id]
    
    if len(tasks) < initial_len:
        return '', 204
    return jsonify({"error": "Task not found"}), 404

if __name__ == '__main__':
    app.run(port=5000, debug=True)