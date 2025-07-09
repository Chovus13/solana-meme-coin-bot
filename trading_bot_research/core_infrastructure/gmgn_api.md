# GMGN API for Solana Token Data

## 1. Introduction

The GMGN API is a free-to-use API that provides a suite of tools for quantitative trading on the Solana blockchain. It offers endpoints for querying swap routes, submitting transactions, and checking transaction status. A key feature of the GMGN API is its support for JITO Anti-MEV, which helps protect trades from front-running.

## 2. Key Features

- **Free to use**: No API key is required.
- **Solana Trading API**: Enables fast quantitative trading on Solana.
- **Anti-MEV Support**: Integrates with JITO Anti-MEV to prevent front-running.
- **Swap Route Query**: Provides an endpoint to find the optimal swap route between token pairs.
- **Transaction Submission**: Allows for the submission of signed Solana transactions.
- **Transaction Status Monitoring**: Offers an endpoint to track the status of submitted transactions.

## 3. Authentication

The GMGN API is free to use and does not require an API key for the Solana trading API.

## 4. API Endpoints

### 4.1. Query Router Endpoint

- **URL**: `https://gmgn.ai/defi/router/v1/sol/tx/get_swap_route`
- **Method**: GET
- **Description**: Retrieves swap routes for token pairs on Solana.

### 4.2. Submit Transaction Endpoint

- **URL**: `https://gmgn.ai/txproxy/v1/send_transaction`
- **Method**: POST
- **Description**: Submits a signed Solana transaction.

### 4.3. Transaction Status Query Endpoint

- **URL**: `https://gmgn.ai/defi/router/v1/sol/tx/get_transaction_status`
- **Method**: GET
- **Description**: Checks the status of a submitted Solana transaction.

## 5. Python Implementation

The following Python code provides an example of how to use the GMGN API to get a swap quote, sign the transaction, submit it, and check its status.

```python
import base64
import time
import requests
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey

# Replace with your private key
private_key_bs58 = "YOUR_PRIVATE_KEY_IN_BS58"
keypair = Keypair.from_base58_string(private_key_bs58)

# --- 1. Get Swap Quote ---
input_token = "So11111111111111111111111111111111111111112"  # SOL
output_token = "7EYnhQoR9YM3N7UoaKRoA44Uy8JeaZV3qyouov87awMs"  # Example Token
amount = 50000000  # 0.05 SOL
slippage = 0.5

quote_url = f"https://gmgn.ai/defi/router/v1/sol/tx/get_swap_route?token_in_address={input_token}&token_out_address={output_token}&in_amount={amount}&from_address={keypair.pubkey()}&slippage={slippage}"

response = requests.get(quote_url)
quote_data = response.json()

if quote_data["code"] != 0:
    print(f"Error getting quote: {quote_data['msg']}")
    exit()

# --- 2. Sign Transaction ---
swap_transaction_b64 = quote_data["data"]["raw_tx"]["swapTransaction"]
swap_transaction_bytes = base64.b64decode(swap_transaction_b64)

transaction = VersionedTransaction.from_bytes(swap_transaction_bytes)
transaction.sign([keypair])

signed_tx = base64.b64encode(bytes(transaction)).decode("utf-8")

# --- 3. Submit Transaction ---
submit_url = "https://gmgn.ai/txproxy/v1/send_transaction"
headers = {"content-type": "application/json"}
payload = {"chain": "sol", "signedTx": signed_tx}

response = requests.post(submit_url, json=payload, headers=headers)
submit_response = response.json()

if submit_response["code"] != 0:
    print(f"Error submitting transaction: {submit_response['msg']}")
    exit()

# --- 4. Check Transaction Status ---
hash = submit_response["data"]["hash"]
last_valid_block_height = quote_data["data"]["raw_tx"]["lastValidBlockHeight"]

while True:
    status_url = f"https://gmgn.ai/defi/router/v1/sol/tx/get_transaction_status?hash={hash}&last_valid_height={last_valid_block_height}"
    response = requests.get(status_url)
    status_data = response.json()

    print(status_data)

    if status_data.get("data", {}).get("success") or status_data.get("data", {}).get("expired"):
        break

    time.sleep(1)

```

## 6. Best Practices

- **Error Handling**: Implement robust error handling to manage potential issues with the API, such as failed transactions or invalid responses.
- **Slippage**: Carefully consider the slippage parameter to avoid unexpected losses due to price fluctuations.
- **Anti-MEV**: Take advantage of the JITO Anti-MEV feature to protect your trades from front-running.
