from flask import Flask, jsonify, request
import datetime
import hashlib
import json
import requests
from uuid import uuid4
from urllib.parse import urlparse
import os

AMOUNT = 0
RECEIVER = "Node 5004"
PORT = 5004


class CryptoCoin:

    def __init__(self) -> None:
        self.chain = []
        self.transactions = []
        self.create_block(proof=1, previous_hash="0")
        self.nodes = set()

    def create_block(self, proof, previous_hash):
        block = {
            "index": len(self.chain) + 1,
            "timestamp": str(datetime.datetime.now()),
            "proof": proof,
            "previous_hash": previous_hash,
            "transactions": self.transactions,
        }
        self.transactions = []
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof) -> int:
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(
                str(new_proof**2 - previous_proof**2).encode()
            ).hexdigest()
            if hash_operation[:4] == "0000":
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block) -> str:
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain) -> bool:
        previous_block = chain[0]  # previous block
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]  # current block
            if block["previous_hash"] != self.hash(previous_block):
                return False
            previous_proof = previous_block["proof"]  # previous proof
            proof = block["proof"]  # current proof
            hash_operation = hashlib.sha256(
                str(proof**2 - previous_proof**2).encode()
            ).hexdigest()
            if hash_operation[:4] != "0000":
                return False
            previous_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount):
        self.transactions.append(
            {"sender": sender, "receiver": receiver, "amount": amount}
        )
        previous_block = self.get_previous_block()
        return previous_block["index"] + 1

    def add_node(self, address) -> None:
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self) -> bool:
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f"http://{node}/get_chain")
            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    app = Flask(__name__)
    node_address = str(uuid4()).replace("-", "")
    crypto_coin = CryptoCoin()


@app.route("/", methods=["GET"])
def index():
    return "Welcome to the crypto_coin!", 200


@app.route("/is_valid", methods=["GET"])
def is_valid():
    result = crypto_coin.is_chain_valid(crypto_coin.chain)
    match result:
        case True:
            response = {"message": "Perfect! The crypto_coin is valid."}
        case False:
            response = {"message": "Oops! The crypto_coin is not valid!"}
    return jsonify(response), 200


@app.route("/mine_block", methods=["GET"])
def mine_block():
    previous_block = crypto_coin.get_previous_block()
    previous_proof = previous_block["proof"]
    previous_hash = crypto_coin.hash(previous_block)
    proof = crypto_coin.proof_of_work(previous_proof)

    # Gather transactions from other nodes and append them to the block's transactions
    block_transactions = []
    for node in crypto_coin.nodes:
        try:
            transactions_response = requests.get(f"http://{node}/get_transactions")
            if transactions_response.status_code == 200:
                transactions = transactions_response.json().get("transactions", [])
                if transactions:
                    for transaction in transactions:
                        block_transactions.append(transaction)
        except requests.RequestException as e:
            print(f"Error getting transactions from node {node}: {e}")

    # Add local transactions
    block_transactions.extend(crypto_coin.transactions)

    # Create the block
    block = crypto_coin.create_block(proof, previous_hash)
    block["transactions"] = block_transactions

    # Reset local transactions
    for node in crypto_coin.nodes:
        try:
            requests.delete(f"http://{node}/reset_transactions")
        except requests.RequestException as e:
            print(f"Error deleting transactions for node {node}: {e}")

    # Broadcast the new block to other nodes
    for node in crypto_coin.nodes:
        try:
            requests.get(f"http://{node}/replace_chain")
        except requests.RequestException as e:
            print(f"Error replacing chain for node {node}: {e}")

    response = {
        "message": "Congratulations, you just mined a block!",
        "index": block["index"],
        "timestamp": block["timestamp"],
        "proof": block["proof"],
        "previous_hash": block["previous_hash"],
        "transactions": block["transactions"],
    }
    return jsonify(response), 200


@app.route("/get_chain", methods=["GET"])
def get_chain():
    response = {"chain": crypto_coin.chain, "length": len(crypto_coin.chain)}
    return jsonify(response), 200


@app.route("/get_transactions", methods=["GET"])
def get_transactions():
    response = {
        "transactions": crypto_coin.transactions,
        "length": len(crypto_coin.transactions),
    }
    return jsonify(response), 200


@app.route("/reset_transactions", methods=["DELETE"])
def reset_transactions():
    crypto_coin.transactions = []
    response = {
        "message": "Transactions were deleted",
        "length": len(crypto_coin.transactions),
    }
    return jsonify(response), 200


@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    json = request.get_json()
    transaction_keys = ["sender", "receiver", "amount"]
    if not all(key in json for key in transaction_keys):
        return "Some elements are missing!", 400
    next_block_index = crypto_coin.add_transaction(
        json["sender"], json["receiver"], json["amount"]
    )
    response = {
        "message": f"This transaction will be added to Block {next_block_index}"
    }
    return jsonify(response), 201


@app.route("/connect_node", methods=["POST"])
def connect_node():
    json = request.get_json()
    nodes = json.get("nodes")
    if nodes is None:
        return "No node", 400
    for node in nodes:
        crypto_coin.add_node(node)
    response = {
        "message": "All the nodes are now connected. The crypto_coin now contains the following nodes:",
        "total_nodes": list(crypto_coin.nodes),
    }
    return jsonify(response), 201


@app.route("/replace_chain", methods=["GET"])
def replace_chain():
    result = crypto_coin.replace_chain()
    match result:
        case True:
            response = {
                "message": "The chain was replaced by the longest one.",
                "new_chain": crypto_coin.chain,
            }
        case False:
            response = {
                "message": "All good. The chain is the longest one.",
                "actual_chain": crypto_coin.chain,
            }
    return jsonify(response), 200


app.run(host="0.0.0.0", port=PORT)
