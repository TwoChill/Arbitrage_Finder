import asyncio
import json
import requests
from web3 import Web3
import config

# Your Ethereum node URL
NODE_URL = config.INFURA_URL

# Setup Web3 connection
web3 = Web3(Web3.HTTPProvider(NODE_URL))

# Ensure the router addresses are checksummed
UNISWAP_ROUTER_ADDRESS = Web3.to_checksum_address(config.UNI_ROUTER)
LIQUIDIYT_POOL_ADDRESS = Web3.to_checksum_address(config.LIQUIDIYT_POOL_1)


def fetch_abi(url: str):
    """Fetch ABI from a given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['abi'] if 'abi' in data else json.loads(data['result'])
    else:
        raise Exception(f"Failed to fetch ABI. Status code: {response.status_code}")


# Load the ABIs
UNISWAP_ROUTER_ABI = fetch_abi('https://unpkg.com/@uniswap/v2-core@1.0.0/build/IUniswapV2Pair.json')
LIQUIDITY_POOL_ABI = fetch_abi(
    f"https://api.etherscan.io/api?module=contract&action=getabi&address="
    f"{LIQUIDIYT_POOL_ADDRESS}&apikey={config.ETHERSCAN_API_KEY}")

# Create contract instances
ROUTER_CONTRACT = web3.eth.contract(address=UNISWAP_ROUTER_ADDRESS, abi=UNISWAP_ROUTER_ABI)
LIQUIDITY_POOL_CONTRACT = web3.eth.contract(address=LIQUIDIYT_POOL_ADDRESS, abi=LIQUIDITY_POOL_ABI)


async def listen_for_swaps(contract, address):
    """Listen for swap events on a specified contract and print price details."""
    print(f"Listening for swap events on {address}...\n")
    swap_event_filter = contract.events.Swap.create_filter(fromBlock='latest')
    while True:
        await asyncio.sleep(0.1)  # Polling interval
        new_entries = swap_event_filter.get_new_entries()
        for event in new_entries:
            tx_hash = event['transactionHash'].hex()
            print(f"TxHash: {tx_hash}")


async def main():
    """ Main function. """

    await asyncio.gather(
        listen_for_swaps(LIQUIDITY_POOL_CONTRACT, LIQUIDIYT_POOL_ADDRESS),
    )

if __name__ == '__main__':
    asyncio.run(main())
