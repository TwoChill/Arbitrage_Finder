import asyncio
import os
from datetime import datetime
import aiohttp
from web3 import Web3
import config

# Your Ethereum node URL
NODE_URL = config.INFURA_URL

# Setup Web3 connection
web3 = Web3(Web3.HTTPProvider(NODE_URL))


def construct_abi_url(contract_address):
    return (f"https://api.etherscan.io/api?module=contract&action=getabi&address="
            f"{contract_address}&apikey={config.ETHERSCAN_API_KEY}")


async def fetch_abi(url: str):
    """Fetch ABI from a given URL asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['result'] if 'result' in data else data
            else:
                raise Exception(f"Failed to fetch ABI. Status code: {response.status}")


async def decode_logs(logs, contract_abi):
    decoded_events = []
    contract = web3.eth.contract(abi=contract_abi)
    for log in logs:
        decoded_event = contract.events.Swap().processReceipt({'logs': [log]})
        if decoded_event:
            decoded_events.append(decoded_event[0])
    return decoded_events


async def fetch_transaction_details(tx_hash):
    """Fetch transaction details for a given transaction hash asynchronously."""
    async with aiohttp.ClientSession() as session:

        # Fetch transaction receipt and transaction details
        receipt_response = await session.get(
            f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionReceipt&txhash="
            f"{tx_hash}&apikey={config.ETHERSCAN_API_KEY}")

        # Fetch transaction details
        tx_response = await session.get(
            f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash="
            f"{tx_hash}&apikey={config.ETHERSCAN_API_KEY}")

        # Extracting data from transaction receipt
        if receipt_response.status == 200 and tx_response.status == 200:
            receipt_data = await receipt_response.json()
            tx_data = await tx_response.json()

            # Extracting data from transaction receipt
            status = receipt_data['result']['status']
            block_number = receipt_data['result']['blockNumber']
            gas_used = receipt_data['result']['gasUsed']
            effective_gas_price = receipt_data['result']['effectiveGasPrice']

            # Extracting data from transaction details
            tx_hash = tx_data['result']['hash']
            block_response = await session.get(
                f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={block_number}"
                f"&boolean=true&apikey={config.ETHERSCAN_API_KEY}")

            # Basic error handling to ensure 'result' and 'timestamp' are present
            if block_response.status == 200:
                block_data = await block_response.json()
                if 'result' in block_data and 'timestamp' in block_data['result']:
                    timestamp = int(block_data['result']['timestamp'], 16)
                    print(f"\tTimestamp: {datetime.utcfromtimestamp(timestamp).strftime('%H:%M:%S %d-%m-%Y')}")
                else:
                    print("Error: 'result' or 'timestamp' not found in API response")

            # Extracting data from transaction details
            from_address = tx_data['result']['from']
            to_address = tx_data['result']['to']
            logs_adress = receipt_data['result']['logs'][0]['address']
            logs_event_signature_hash = receipt_data['result']['logs'][0]['topics'][0]

            # Extracting data from transaction receipt
            # This is crucial for understanding the volume of the trade,
            # which can significantly impact your arbitrage strategy by indicating the liquidity depth and potential slippage.
            logs_data = receipt_data['result']['logs'][0]['data']

            print(f"Tx Hash: {tx_hash}")
            print(f"Status: {'Success' if int(status, 16) == 1 else 'Failure'}")
            print(f"Block Number: {int(block_number, 16)}")
            print(f"Gas Used: {int(gas_used, 16)}")
            print(f"Effective Gas Price: {int(effective_gas_price, 16)}")
            print(f"InitiatorAddress : {from_address}")
            print(f"ContractAddress : {to_address}")

            # Knowing which pools are involved in swap events is essential for tracking potential arbitrage paths
            print("\n\t[From logs]")
            print(f"To: {logs_adress}")
            print(f"Event Signature Hash: {logs_event_signature_hash}")

            if len(receipt_data['result']['logs'][0]['topics']) > 1:
                print(f"Event Topic Sender: {receipt_data['result']['logs'][0]['topics'][1]}")
            if len(receipt_data['result']['logs'][0]['topics']) > 2:
                print(f"Event Topic Reciever: {receipt_data['result']['logs'][0]['topics'][2]}")

            print(f"Data: {logs_data}\n")
            # print(f"Token Pair Details

        else:
            raise Exception("Failed to fetch Transaction Details.")

# Define contract addresses (already checksummed)
UNISWAP_ROUTER_ADDRESS = Web3.to_checksum_address(config.UNI_ROUTER)
LIQUIDITY_POOL_ADDRESS = Web3.to_checksum_address(config.LIQUIDIYT_POOL_1)

# Construct ABI URLs for fetching
UNISWAP_ROUTER_ABI_URL = construct_abi_url(UNISWAP_ROUTER_ADDRESS)
LIQUIDITY_POOL_ABI_URL = construct_abi_url(LIQUIDITY_POOL_ADDRESS)


async def listen_for_swaps(contract, address):
    """Listen for swap events on a specified contract and print price details asynchronously."""
    print(f"Listening for swap events on {address}...\n")
    swap_event_filter = contract.events.Swap.create_filter(fromBlock='latest')
    while True:
        await asyncio.sleep(0.1)
        new_entries = swap_event_filter.get_new_entries()
        for event in new_entries:
            os.system('cls' if os.name == "nt" else 'clear')
            await fetch_transaction_details(event['transactionHash'].hex())


async def main():
    # Fetch ABIs asynchronously
    uniswap_router_abi = await fetch_abi(UNISWAP_ROUTER_ABI_URL)
    liquidity_pool_abi = await fetch_abi(LIQUIDITY_POOL_ABI_URL)

    # Create contract instances with the correct addresses and fetched ABIs
    liquidity_pool_contract = web3.eth.contract(address=LIQUIDITY_POOL_ADDRESS, abi=liquidity_pool_abi)

    # Listen for swap events asynchronously
    await asyncio.gather(
        listen_for_swaps(liquidity_pool_contract, LIQUIDITY_POOL_ADDRESS),
    )

if __name__ == '__main__':
    asyncio.run(main())
