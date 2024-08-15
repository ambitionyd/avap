from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

prices = {"A": 20, "B": 30}

estimates = []


def generate_pdf(estimates):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Estimate")
    p.drawString(100, 735, "---------------------")
    total = 0
    y = 720
    for item in estimates:
        product, quantity = item
        price = prices[product]
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

    if msg == 'hi':
        response.message("Welcome! How can I assist you today?\n1. Create New Estimate\n2. Tweak Prices")
    elif msg == '1':
        response.message("Please enter the product and quantity. For example, 'A 2'.")
    elif msg.startswith('a') or msg.startswith('b'):
        try:
            product, quantity = msg.split()
            quantity = int(quantity)
            estimates.append((product.upper(), quantity))
            response.message("Do you want to add another product? (yes/no)")
        except:
            response.message("Invalid format. Please enter the product and quantity. For example, 'A 2'.")
    elif msg == 'yes':
        response.message("Please enter the product and quantity. For example, 'A 2'.")
    elif msg == 'no':
        buffer = generate_pdf(estimates)
        response.message("Estimate generated. Download your PDF.")
        response.message("http://your-server.com/download")  # Replace with your server's download endpoint
    elif msg == '2':
        response.message("Which product do you want to change price for? (A/B)")
    elif msg in ['a', 'b']:
        product = msg.upper()
        response.message(f"Enter the new price for Product {product}:")
    else:
        try:
            new_price = float(msg)
            prices[product] = new_price
            response.message(f"Prices updated successfully. Product {product}: ${new_price}")
        except:
            response.message("Invalid price format. Please enter a numeric value.")
    return str(response)

@app.route('/download', methods=['GET'])
def download_pdf():
    buffer = generate_pdf(estimates)
    return send_file(buffer, attachment_filename='estimate.pdf', as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)