from flask import Blueprint, request, jsonify
from week11.models.database import notifications_db, new_id, now
from week11.routes.event_routes import subscribe, publish_event
from week11.routes.webhook_routes import webhooks_db, _deliver_webhook

notification_bp = Blueprint('notification', __name__)

notification_prefs = {}

@notification_bp.route('/preferences', methods=['POST'])
def set_preferences():
    data    = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "Thiếu user_id"}), 422

    channels = data.get('channels', {})
    prefs = {
        "user_id":    user_id,
        "channels":   channels,
        "created_at": now(),
    }
    notification_prefs[user_id] = prefs

    webhook_channel = channels.get('webhook', {})
    if webhook_channel.get('url'):
        webhook = _register_user_webhook(
            user_id=user_id,
            url=webhook_channel['url'],
            events=webhook_channel.get('events', [])
        )
        prefs['webhook_id'] = webhook['id']

    return jsonify(prefs), 201


def _register_user_webhook(user_id, url, events):
    import hashlib
    secret = hashlib.sha256(f"{user_id}{url}{now()}".encode()).hexdigest()[:32]
    wid = new_id()

    webhook = {
        "id":          wid,
        "url":         url,
        "events":      events,
        "secret":      secret,
        "active":      True,
        "description": f"Auto-created for user {user_id}",
        "created_at":  now(),
        "user_id":     user_id,
        "stats": {"total_deliveries": 0, "successful": 0, "failed": 0,
                  "last_delivery_at": None},
    }
    webhooks_db[wid] = webhook

    for event_type in events:
        subscribe(event_type, lambda e, w=webhook: _deliver_webhook(w, e))

    return webhook

@notification_bp.route('', methods=['GET'])
def get_notifications():
    user_id  = request.args.get('user_id')
    unread_only = request.args.get('unread', 'false').lower() == 'true'

    notifs = list(notifications_db)

    if user_id:
        notifs = [n for n in notifs if n.get('user_id') == user_id]
    if unread_only:
        notifs = [n for n in notifs if not n.get('read', False)]

    return jsonify({
        "data":         list(reversed(notifs)),
        "unread_count": sum(1 for n in notifs if not n.get('read', False))
    })


@notification_bp.route('/<notification_id>/read', methods=['POST'])
def mark_read(notification_id):
    """POST /api/v1/notifications/:id/read - Đánh dấu đã đọc"""
    notif = next((n for n in notifications_db if n['id'] == notification_id), None)
    if not notif:
        return jsonify({"error": "not_found"}), 404

    notif['read']    = True
    notif['read_at'] = now()
    return jsonify(notif)

@notification_bp.route('/demo/full-flow', methods=['POST'])
def demo_full_flow():
    data     = request.get_json() or {}
    user_id  = data.get('user_id', 'u001')
    order_id = data.get('order_id', 'o001')

    steps = []

    steps.append({
        "step":   1,
        "action": "User thanh toán đơn hàng",
        "pattern": "REST API (CRUD/HATEOAS)",
        "detail": f"POST /api/v1/orders/{order_id}/pay"
    })

    event = publish_event(
        event_type='order.paid',
        data={"order_id": order_id, "user_id": user_id, "amount": 999.0},
        source='notification_demo'
    )
    steps.append({
        "step":    2,
        "action":  "Phát event vào Event Store",
        "pattern": "Event-driven",
        "detail":  f"Event ID: {event['id']}, Type: order.paid"
    })

    in_app_notif = _create_in_app_notification(
        user_id=user_id,
        event=event,
        message="Thanh toán thành công! Đơn hàng của bạn đang được xử lý."
    )
    steps.append({
        "step":    3,
        "action":  "Notification Handler tạo in-app notification",
        "pattern": "Event-driven (subscriber)",
        "detail":  f"Notification ID: {in_app_notif['id']}"
    })

    webhook_receivers = [
        w for w in webhooks_db.values()
        if w['active'] and 'order.paid' in w.get('events', [])
    ]
    steps.append({
        "step":    4,
        "action":  f"Webhook delivery tới {len(webhook_receivers)} subscribers",
        "pattern": "Webhook",
        "detail":  [w['url'] for w in webhook_receivers]
    })

    steps.append({
        "step":    5,
        "action":  "Subscriber nhận webhook, gửi email xác nhận",
        "pattern": "Webhook consumer",
        "detail":  "Subscriber tự xử lý: gửi email, update DB, fulfill order..."
    })

    return jsonify({
        "demo_complete": True,
        "flow":          steps,
        "event":         event,
        "notification":  in_app_notif,
        "summary": (
            "Toàn bộ luồng: REST API → Event Store → Event Bus → "
            "Notification + Webhook Delivery → Subscriber xử lý"
        )
    })


def _create_in_app_notification(user_id, event, message):
    notif = {
        "id":         new_id(),
        "user_id":    user_id,
        "event_id":   event.get('id'),
        "event_type": event.get('type'),
        "message":    message,
        "read":       False,
        "created_at": now(),
    }
    notifications_db.append(notif)
    return notif

def _auto_subscribe_notifications():
    event_messages = {
        "order.paid":      "Đơn hàng #{order_id} đã được thanh toán",
        "order.shipped":   "Đơn hàng #{order_id} đang trên đường giao",
        "order.delivered": "Đơn hàng #{order_id} đã giao thành công",
        "order.cancelled": "Đơn hàng #{order_id} đã bị hủy",
    }

    for event_type, msg_template in event_messages.items():
        def make_handler(et, msg_tpl):
            def handler(event):
                # Tạo notification cho user liên quan
                order_id = event['data'].get('order_id') or event['data'].get('id', '')
                user_id  = event['data'].get('user_id', 'system')
                message  = msg_tpl.replace('{order_id}', str(order_id))
                _create_in_app_notification(user_id, event, message)
                print(f"[Notification] {et} → {message}")
            return handler

        subscribe(event_type, make_handler(event_type, msg_template))

_auto_subscribe_notifications()
