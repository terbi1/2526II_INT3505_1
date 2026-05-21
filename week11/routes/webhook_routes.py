import hmac
import hashlib
import json
import threading
import time
import urllib.request
import urllib.error
from flask import Blueprint, request, jsonify
from week11.models.database import webhooks_db, webhook_deliveries, new_id, now
from week11.routes.event_routes import subscribe, publish_event

webhook_bp = Blueprint('webhook', __name__)

SUPPORTED_EVENTS = {
    "order.created",
    "order.paid",
    "order.shipped",
    "order.delivered",
    "order.cancelled",
    "product.created",
    "product.updated",
    "product.deleted",
    "payment.succeeded",
    "payment.failed",
}

@webhook_bp.route('', methods=['POST'])
def register_webhook():
    data   = request.get_json()
    url    = data.get('url')
    events = data.get('events', [])

    if not url:
        return jsonify({"error": "Thiếu 'url'"}), 422

    # Validate event types
    invalid_events = set(events) - SUPPORTED_EVENTS
    if invalid_events:
        return jsonify({
            "error":            "invalid_events",
            "invalid":          list(invalid_events),
            "supported_events": list(SUPPORTED_EVENTS)
        }), 422

    secret = hashlib.sha256(f"{url}{now()}".encode()).hexdigest()[:32]
    wid    = new_id()

    webhook = {
        "id":          wid,
        "url":         url,
        "events":      events,
        "secret":      secret,
        "active":      True,
        "description": data.get('description', ''),
        "created_at":  now(),
        "stats": {
            "total_deliveries":   0,
            "successful":         0,
            "failed":             0,
            "last_delivery_at":   None,
        }
    }
    webhooks_db[wid] = webhook

    for event_type in events:
        subscribe(event_type, lambda e, w=webhook: _deliver_webhook(w, e))

    _deliver_webhook(webhook, {
        "id":        new_id(),
        "type":      "webhook.ping",
        "data":      {"webhook_id": wid, "message": "Webhook registered successfully"},
        "timestamp": now(),
    })

    return jsonify({
        "webhook":       webhook,
        "signing_secret": f"whsec_{secret}",
        "note":          "Lưu signing_secret để verify payload signature"
    }), 201


@webhook_bp.route('', methods=['GET'])
def list_webhooks():
    """GET /api/v1/webhooks - Danh sách webhooks đã đăng ký"""
    webhooks = []
    for w in webhooks_db.values():
        wh = dict(w)
        wh['secret'] = f"whsec_...{w['secret'][-4:]}"
        webhooks.append(wh)

    return jsonify({"data": webhooks})


@webhook_bp.route('/<webhook_id>', methods=['GET'])
def get_webhook(webhook_id):
    w = webhooks_db.get(webhook_id)
    if not w:
        return jsonify({"error": "not_found"}), 404
    wh = dict(w)
    wh['secret'] = f"whsec_...{w['secret'][-4:]}"
    return jsonify(wh)


@webhook_bp.route('/<webhook_id>', methods=['DELETE'])
def delete_webhook(webhook_id):
    if webhook_id not in webhooks_db:
        return jsonify({"error": "not_found"}), 404

    webhooks_db[webhook_id]['active'] = False
    del webhooks_db[webhook_id]
    return '', 204


@webhook_bp.route('/<webhook_id>/deliveries', methods=['GET'])
def webhook_deliveries_list(webhook_id):
    deliveries = [d for d in webhook_deliveries if d['webhook_id'] == webhook_id]
    deliveries = list(reversed(deliveries))  # newest first
    return jsonify({"data": deliveries})


@webhook_bp.route('/<webhook_id>/test', methods=['POST'])
def test_webhook(webhook_id):
    webhook = webhooks_db.get(webhook_id)
    if not webhook:
        return jsonify({"error": "not_found"}), 404

    test_event = {
        "id":        new_id(),
        "type":      "webhook.test",
        "data":      {"message": "This is a test delivery", "webhook_id": webhook_id},
        "timestamp": now(),
    }
    delivery = _deliver_webhook(webhook, test_event)
    return jsonify({"delivery": delivery})

@webhook_bp.route('/receive', methods=['POST'])
def receive_webhook():
    payload   = request.get_data()
    signature = request.headers.get('X-Webhook-Signature', '')
    event_src = request.headers.get('X-Webhook-Source', 'unknown')

    demo_secret = b"demo-secret-key"

    expected = hmac.new(demo_secret, payload, hashlib.sha256).hexdigest()
    is_valid = hmac.compare_digest(signature, f"sha256={expected}")

    try:
        body = json.loads(payload)
    except Exception:
        return jsonify({"error": "invalid_json"}), 400

    event_type = body.get('type', 'unknown')

    publish_event(
        event_type=f"external.{event_type}",
        data=body,
        source=event_src
    )

    return jsonify({
        "received":         True,
        "signature_valid":  is_valid,
        "event_type":       event_type,
        "note": (
            "Dù signature không hợp lệ, chúng ta vẫn nhận payload "
            "nhưng trong production phải reject nếu signature sai."
        )
    })

@webhook_bp.route('/trigger', methods=['POST'])
def trigger_event():
    
    data       = request.get_json()
    event_type = data.get('event_type', 'test.event')
    event_data = data.get('data', {})

    event = publish_event(event_type, event_data, source='manual_trigger')

    receivers = [
        w for w in webhooks_db.values()
        if w['active'] and event_type in w.get('events', [])
    ]

    return jsonify({
        "event_published": event,
        "webhook_receivers": len(receivers),
        "receivers": [w['id'] for w in receivers]
    })

def _sign_payload(secret: str, payload: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def _deliver_webhook(webhook: dict, event: dict, attempt: int = 1):
    payload_str = json.dumps({
        "id":        event.get('id', new_id()),
        "type":      event.get('type'),
        "data":      event.get('data', {}),
        "timestamp": event.get('timestamp', now()),
        "attempt":   attempt,
    })

    signature = _sign_payload(webhook['secret'], payload_str)

    delivery = {
        "id":           new_id(),
        "webhook_id":   webhook['id'],
        "event_type":   event.get('type'),
        "url":          webhook['url'],
        "attempt":      attempt,
        "payload":      json.loads(payload_str),
        "status":       "pending",
        "response_code": None,
        "delivered_at": now(),
        "headers_sent": {
            "Content-Type":       "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-ID":       webhook['id'],
            "X-Event-Type":       event.get('type', ''),
            "X-Delivery-ID":      new_id(),
        }
    }
    webhook_deliveries.append(delivery)

    def _do_deliver():
        try:
            req = urllib.request.Request(
                webhook['url'],
                data=payload_str.encode(),
                headers={
                    "Content-Type":        "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-ID":        webhook['id'],
                    "X-Event-Type":        event.get('type', ''),
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                delivery['status']        = 'success'
                delivery['response_code'] = resp.status

                webhook['stats']['total_deliveries']  += 1
                webhook['stats']['successful']         += 1
                webhook['stats']['last_delivery_at']   = now()

        except urllib.error.HTTPError as e:
            delivery['status']        = 'failed'
            delivery['response_code'] = e.code
            delivery['error']         = str(e)
            webhook['stats']['failed'] += 1
            webhook['stats']['total_deliveries'] += 1

            if attempt < 4:
                delay = 2 ** attempt  # 2s, 4s, 8s
                print(f"[Webhook] Retry attempt {attempt+1} sau {delay}s "
                      f"cho {webhook['url']}")
                time.sleep(delay)
                _deliver_webhook(webhook, event, attempt + 1)

        except Exception as e:
            delivery['status'] = 'failed'
            delivery['error']  = str(e)
            webhook['stats']['failed'] += 1
            webhook['stats']['total_deliveries'] += 1
            print(f"[Webhook] Delivery failed: {e}")

    thread = threading.Thread(target=_do_deliver, daemon=True)
    thread.start()

    return delivery
