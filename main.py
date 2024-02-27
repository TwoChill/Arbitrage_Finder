import asyncio
import json
from web3 import Web3
import aiohttp
import requests
import config

# Setup Web3 connection
NODE_URL = config.INFURA_URL
web3 = Web3(Web3.HTTPProvider(NODE_URL))

# Starting with a flash loan amount in ETH
flash_loan_amount = web3.to_wei(1, 'ether') / 10**18  # 1 ETH in Wei then converted back to ETH for simplicity

# In-memory cache for ABIs to avoid hitting the rate limit
abi_cache = {}


async def fetch_abi(url: str):
    """Fetch ABI from a given URL asynchronously, with caching."""
    if url in abi_cache:
        return abi_cache[url]

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                abi = data['result'] if 'result' in data else data
                # Cache the ABI for future use
                abi_cache[url] = abi
                return abi
            else:
                raise Exception(f"Failed to fetch ABI. Status code: {response.status}")


async def get_token_addresses(pool_address):
    """Get token addresses for a given pool address."""
    abi_url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={pool_address}&apikey={config.ETHERSCAN_API_KEY}"
    abi = await fetch_abi(abi_url)
    pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=abi)
    token0_address = pool_contract.functions.token0().call().lower()
    token1_address = pool_contract.functions.token1().call().lower()
    return token0_address, token1_address


async def get_token_symbol(address):
    """Get token symbol by address."""
    for key in config.CONSOLIDATED_DICT.keys():
        for k, v in config.CONSOLIDATED_DICT[key].items():
            if v.lower() == address.lower():
                return k
    return "Unknown Token"


async def fetch_pool_reserves(pool_contract):
    """Fetch pool reserves asynchronously."""
    reserves = pool_contract.functions.getReserves().call()
    reserve_token0, reserve_token1 = reserves[:2]
    return reserve_token0, reserve_token1


def calculate_exchange_rate(reserve_a, reserve_b):
    """Calculate the exchange rate from Token A to Token B."""
    return reserve_b / reserve_a


async def get_exchange_rate_for_pool(pool_address):
    """Get exchange rate for a given pool."""
    LP_ABI = await fetch_abi(f"https://api.etherscan.io/api?module=contract&action=getabi&address={pool_address}&apikey={config.ETHERSCAN_API_KEY}")
    LP_CONTRACT_INSTANCE = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=LP_ABI)

    token0, token1 = await get_token_addresses(pool_address)
    token0_name = await get_token_symbol(token0)
    token1_name = await get_token_symbol(token1)

    if token1_name == "WETH":
        token0_name, token1_name = token1_name, token0_name
        reserve_token1, reserve_token0 = await fetch_pool_reserves(LP_CONTRACT_INSTANCE)
    else:
        reserve_token0, reserve_token1 = await fetch_pool_reserves(LP_CONTRACT_INSTANCE)

    return token0_name, reserve_token0, token1_name, reserve_token1


async def main():
    # Define your pools here
    pools = [
        config.CONSOLIDATED_DICT['LQ_POOL']['WETH/BEAM'],
        config.CONSOLIDATED_DICT['LQ_POOL']['FLOKI/WETH'],
        config.CONSOLIDATED_DICT['LQ_POOL']['WETH/SPYRO']
    ]

    tasks = [get_exchange_rate_for_pool(pool) for pool in pools]
    results = await asyncio.gather(*tasks)

    current_amount = flash_loan_amount
    for i, (token0_name, reserve_token0, token1_name, reserve_token1) in enumerate(results, start=1):
        exchange_rate = calculate_exchange_rate(reserve_token0, reserve_token1)
        amount_received = current_amount * exchange_rate
        print(f"Step {i}: Swap {current_amount:.6f} {token0_name} for {amount_received:.6f} {token1_name} at an exchange rate of {exchange_rate:.6f} {token1_name}/{token0_name}")
        current_amount = amount_received

    profit_or_loss = current_amount - flash_loan_amount

    # Check if the operation resulted in a profit or loss and print accordingly
    profit_or_loss_word = "Profit" if profit_or_loss > 0 else "Loss"
    print(f"\nArbitrage Result: In {profit_or_loss_word}\n\nStarted with {flash_loan_amount:.6f} ETH\n"
          f"Ended with {current_amount:.6f} ETH\n")

asyncio.run(main())
