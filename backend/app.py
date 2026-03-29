from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests (for local testing)

# In-memory storage
transactions = []

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    return jsonify(transactions)

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.get_json()
    description = data.get('description')
    amount = data.get('amount')
    if description is None or amount is None:
        return jsonify({'error': 'Missing description or amount'}), 400
    transactions.append({'description': description, 'amount': amount})
    return jsonify(transactions[-1]), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
