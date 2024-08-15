from flask import Flask, request, send_file, url_for
from twilio.twiml.messaging_response import MessagingResponse
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Initial prices for products
prices = {"A": 20, "B": 30}
# Stores estimates for each user
user_estimates = {}

def generate_pdf(estimates):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Estimate")
    p.drawString(100, 735, "---------------------")
    total = 0
    y = 720
    for item in estimates:
        product, quantity = item
        price = prices.get(product, 0)
        line_total = price * quantity
        total += line_total
        p.drawString(100, y, f"Product {product}: {quantity} units x ${price} = ${line_total}")
        y -= 15
    p.drawString(100, y, f"Total: ${total}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

@app.route('/sms', methods=['POST'])
def sms_reply():
    msg = request.form.get('Body').strip().lower()
    from_number = request.form.get('From')
    response = MessagingResponse()

    # Check the user's current state
    user_state = user_estimates.get(from_number, {}).get('state', 'start')

    if msg in ['hi', 'hello']:
        response.message("Welcome! How can I assist you today?\n1. Create New Estimate\n2. Tweak Prices")
        user_estimates[from_number] = {'state': 'menu', 'estimates': []}
    elif user_state == 'menu':
        if msg in ['1', 'create new estimate','1. Create New Estimate']:
            response.message("Please enter the product and quantity. For example, 'A 2'.")
            user_estimates[from_number]['state'] = 'creating_estimate'
        elif msg in ['2', 'tweak prices','2. Tweak Prices']:
            response.message("Which product do you want to change the price for? (A/B)")
            user_estimates[from_number]['state'] = 'tweaking_prices'
        else:
            response.message("Invalid option. Please reply with '1' to create a new estimate or '2' to tweak prices.")
    elif user_state == 'creating_estimate':
        try:
            product, quantity = msg.split()
            quantity = int(quantity)
            user_estimates[from_number]['estimates'].append((product.upper(), quantity))
            response.message("Do you want to add another product? (yes/no)")
            user_estimates[from_number]['state'] = 'adding_more'
        except ValueError:
            response.message("Invalid format. Please enter the product and quantity. For example, 'A 2'.")
    elif user_state == 'adding_more':
        if msg == 'yes':
            response.message("Please enter the product and quantity. For example, 'A 2'.")
            user_estimates[from_number]['state'] = 'creating_estimate'
        elif msg == 'no':
            buffer = generate_pdf(user_estimates[from_number]['estimates'])
            pdf_url = url_for('download_pdf', phone_number=from_number, _external=True)
            response.message(f"Estimate generated. Download your PDF from {pdf_url}")
            user_estimates[from_number] = {'state': 'menu', 'estimates': []}
        else:
            response.message("Please reply with 'yes' to add more products or 'no' to finalize the estimate.")
    elif user_state == 'tweaking_prices':
        if msg in ['a', 'b']:
            user_estimates[from_number]['product'] = msg.upper()
            response.message(f"Enter the new price for Product {msg.upper()}:")
            user_estimates[from_number]['state'] = 'setting_price'
        else:
            response.message("Invalid product code. Please enter 'A' or 'B'.")
    elif user_state == 'setting_price':
        try:
            new_price = float(msg)
            product = user_estimates[from_number].get('product')
            prices[product] = new_price
            response.message(f"Prices updated successfully. Product {product}: ${new_price}")
            user_estimates[from_number] = {'state': 'menu', 'estimates': []}
        except ValueError:
            response.message("Invalid price format. Please enter a numeric value.")
    else:
        response.message("Sorry, I didn't understand that. Please try again.")

    return str(response)

@app.route('/download/<phone_number>', methods=['GET'])
def download_pdf(phone_number):
    estimates = user_estimates.get(phone_number, {}).get('estimates', [])
    buffer = generate_pdf(estimates)
    return send_file(buffer, download_name='estimate.pdf', as_attachment=True, mimetype='application/pdf')

@app.route('/')
def home():
    return 'Welcome to the homepage!'

if __name__ == '__main__':
    app.run(debug=True, port=5000)
