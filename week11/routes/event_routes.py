from flask import Blueprint, request, jsonify
from models.database import events_db, event_bus, new_id, now

event_bp = Blueprint('event', __name__)

def publish_event(event_type: str, data: dict, source: str = 'system') -> dict:
    event = {
        "id":         new_id(),
        "type":       event_type,
        "source":     source,
        "data":       data,
        "timestamp":  now(),
        "version":    "1.0",
    }
    events_db.append(event)

    _dispatch(event)

    return event


def subscribe(event_type: str, callback):
    if event_type not in event_bus:
        event_bus[event_type] = []
    event_bus[event_type].append(callback)


def _dispatch(event: dict):
    event_type = event['type']
    parts      = event_type.split('.')

    for pattern, callbacks in event_bus.items():
        if _matches(pattern, parts):
            for cb in callbacks:
                try:
                    cb(event)
                except Exception as e:
                    print(f"[EventBus] Subscriber error for {pattern}: {e}")


def _matches(pattern: str, parts: list) -> bool:
    pattern_parts = pattern.split('.')
    if len(pattern_parts) != len(parts):
        return False
    return all(p == '*' or p == v for p, v in zip(pattern_parts, parts))

@event_bp.route('', methods=['GET'])
def list_events():
    event_type = request.args.get('type')
    source     = request.args.get('source')
    limit      = int(request.args.get('limit', 50))

    events = list(events_db)

    if event_type:
        events = [e for e in events if e['type'] == event_type]
    if source:
        events = [e for e in events if e['source'] == source]

    events = list(reversed(events))[:limit]

    return jsonify({
        "data":  events,
        "total": len(events_db),
        "explanation": (
            "Event Store: immutable log của mọi thứ xảy ra trong hệ thống. "
            "Có thể replay để rebuild state, debug, audit."
        )
    })


@event_bp.route('/<event_id>', methods=['GET'])
def get_event(event_id):
    event = next((e for e in events_db if e['id'] == event_id), None)
    if not event:
        return jsonify({"error": "not_found"}), 404
    return jsonify(event)


@event_bp.route('/publish', methods=['POST'])
def publish_manual():
    data = request.get_json()
    if not data.get('type'):
        return jsonify({"error": "Thiếu 'type'"}), 422

    event = publish_event(
        event_type=data['type'],
        data=data.get('data', {}),
        source=data.get('source', 'manual')
    )
    return jsonify({"published": event}), 201


@event_bp.route('/subscribers', methods=['GET'])
def list_subscribers():
    subs = {
        pattern: [cb.__name__ for cb in callbacks]
        for pattern, callbacks in event_bus.items()
    }
    return jsonify({
        "subscriptions": subs,
        "explanation": (
            "Event Bus: mỗi pattern → danh sách handlers. "
            "Dấu * là wildcard, ví dụ 'order.*' khớp mọi order events."
        )
    })


@event_bp.route('/replay', methods=['POST'])
def replay_events():
    data       = request.get_json() or {}
    from_index = data.get('from_index', 0)
    event_type = data.get('event_type')

    to_replay = events_db[from_index:]
    if event_type:
        to_replay = [e for e in to_replay if e['type'] == event_type]

    replayed = []
    for event in to_replay:
        _dispatch(event)
        replayed.append(event['id'])

    return jsonify({
        "replayed_count": len(replayed),
        "replayed_ids":   replayed,
        "explanation":    (
            "Event Replay: chạy lại các events cũ qua handlers hiện tại. "
            "Dùng khi thêm handler mới cần xử lý data cũ, "
            "hoặc rebuild projection sau khi thay đổi business logic."
        )
    })
