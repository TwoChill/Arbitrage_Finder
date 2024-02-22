import asyncio
import os
from datetime import datetime
import aiohttp
import requests
from web3 import Web3
import config
from decimal import Decimal, getcontext

# Your Ethereum node URL
NODE_URL = config.INFURA_URL

# Setup Web3 connection
web3 = Web3(Web3.HTTPProvider(NODE_URL))

# Ensure the router/pool addresses are correct
POOL_1_ADRESS = config.CONSOLIDATED_DICT['LQ_POOL']['WETH/BEAM']

# Define contract addresses (already checksummed)
LIQUIDITY_POOL_ADDRESS = Web3.to_checksum_address(POOL_1_ADRESS)


def construct_abi_url(contract_address):
    etherscan_api_key = config.ETHERSCAN_API_KEY
    return f"https://api.etherscan.io/api?module=contract&action=getabi&address={contract_address}&apikey={etherscan_api_key}"

# Construct ABI URLs for fetching
LIQUIDITY_POOL_ABI_URL = construct_abi_url(POOL_1_ADRESS)


async def fetch_abi(url: str):
    """Fetch ABI from a given URL asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['result'] if 'result' in data else data
            else:
                raise Exception(f"Failed to fetch ABI. Status code: {response.status}")


async def get_eth_price():
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                eth_price = data['ethereum']['usd']
                return eth_price
            else:
                raise Exception(f"Failed to fetch ETH price. Status code: {response.status}")


async def fetch_pool_reserves(pool_contract):
    # Aanname: pool_contract is een Web3 Contract object geïnitialiseerd met de juiste ABI en adres
    reserves = pool_contract.functions.getReserves().call()
    reserve_token0, reserve_token1, timestamp = reserves

    return reserve_token0, reserve_token1, timestamp

async def get_token_addresses(pool_address):
    # Fetch the ABI for the pool (you need to replace this URL with the actual ABI URL for the pool)
    abi_url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={pool_address}&apikey={config.ETHERSCAN_API_KEY}"
    abi = await fetch_abi(abi_url)

    # Create the contract instance
    pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=abi)


    # Fetch Token0 and Token1 addresses
    token0_address = pool_contract.functions.token0().call().lower()
    token1_address = pool_contract.functions.token1().call().lower()

    # Sort the token addresses
    token0, token1 = sorted([token0_address, token1_address])

    return token0, token1


def print_swap_information(logs):
    # Define known event signature hashes
    transfer_event_sig = Web3.keccak(text="Transfer(address,address,uint256)").hex()
    swap_event_sig = Web3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()

    for log in logs:
        if log['topics'][0] == transfer_event_sig:
            # Handle transfer event
            pass
        elif log['topics'][0] == swap_event_sig:
            # Handle swap event
            if len(log['topics']) >= 3:
                # Assuming first topic is the event signature hash
                event_signature = log['topics'][0]

                # Assuming second topic is the sender address
                sender_address = log['topics'][1]

                # Assuming third topic is the receiver address
                receiver_address = log['topics'][2]

                # Print event details
                print(f"Event Signature: {event_signature}")
                print(f"Sender Address: {sender_address}")
                print(f"Receiver Address: {receiver_address}")

                if len(log['topics']) >= 4:
                    # Assuming third topic is the transfer amount
                    transfer_amount = Web3.to_int(hexstr=log['topics'][3])

                    # Assuming fifth topic is additional data
                    additional_data = log['topics'][4]

                    print(f"Transfer Amount: {Web3.from_wei(transfer_amount, 'ether')} tokens")
                    print(f"Additional Data: {additional_data}")
            else:
                print("Error: Incomplete swap event data.\n")


async def get_address_name(address):
    for key in config.CONSOLIDATED_DICT.keys():
        for k, v in config.CONSOLIDATED_DICT[key].items():
            if v == address:
                return k
    return address


def find_triangular_arbitrage_opportunity(token0, token1, token2, rates, pools):
    """
    :param token0: The initial token to start the arbitrage loop.
    :param token1: The second token in the arbitrage loop.
    :param token2: The third token to complete the arbitrage loop back to token0.
    :param rates: A dictionary with exchange rates between the tokens.
    :param pools: A dictionary indicating which pools or DEXes to use for each trade.
    """
    rate_0_to_1 = rates[(token0, token1)]
    rate_1_to_2 = rates[(token1, token2)]
    rate_2_to_0 = rates[(token2, token0)]

    # Calculate if you end up with more token0 after completing the loop
    start_amount = 1  # Starting with 1 unit of token0 for simplicity
    after_first_trade = start_amount * rate_0_to_1
    after_second_trade = after_first_trade * rate_1_to_2
    after_third_trade = after_second_trade * rate_2_to_0

    if after_third_trade > start_amount:
        print("Arbitrage opportunity found!")
        print(f"Trade through {pools[(token0, token1)]}, {pools[(token1, token2)]}, and {pools[(token2, token0)]}")
        # Add logic here to execute trades
    else:
        print("No arbitrage opportunity.")


async def ETH_USD():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd") as response:
            if response.status == 200:
                data = await response.json()
                return data['ethereum']['usd']
            else:
                raise Exception(f"Failed to fetch ETH price. Status code: {response.status}")


async def decode_data(data_hex, token0_address, token1_address):
    # Ensure data_hex is long enough (at least 132 characters: '0x' + 64 chars per token)
    if len(data_hex) >= 2 + 64 * 2:
        decoded_value_token0 = Web3.to_int(hexstr=data_hex[:66])  # First 32 bytes for Token0
        # Correct slicing for Token1, ensuring the start index is correct and there's enough data
        decoded_value_token1 = Web3.to_int(hexstr="0x" + data_hex[66:66+64])  # Next 32 bytes for Token1
    else:
        raise ValueError("data_hex does not contain enough data for decoding")

    # Placeholder for token prices
    price_token0 = "Price calculation required"
    price_token1 = "Price calculation required"

    print(f"Token0: {token0_address}")
    print(f"Token0 Amount: {decoded_value_token0}")
    print(f"Token0 Price: {price_token0}")
    print("\n")
    print(f"Token1: {token1_address}")
    print(f"Token1 Amount: {decoded_value_token1}")
    print(f"Token1 Price: {price_token1}")


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

        #
        if receipt_response.status == 200 and tx_response.status == 200:
            receipt_data = await receipt_response.json()
            tx_data = await tx_response.json()

            # Extracting data from TRANSACTION RECEIPT
            status = receipt_data['result']['status']
            block_number = receipt_data['result']['blockNumber']
            gas_used = int(receipt_data['result']['gasUsed'], 16)
            effective_gas_price = int(receipt_data['result']['effectiveGasPrice'], 16)
            # Check to see if this is correct
            transaction_fee_eth_2 = Decimal("0.03")
            eth_usd_rate = await ETH_USD()
            eth_usd_rate_decimal = Decimal(str(eth_usd_rate))

            transaction_fee_wei = gas_used * effective_gas_price
            transaction_fee_eth = Web3.from_wei(transaction_fee_wei, 'ether')
            transaction_fee_usd = transaction_fee_eth * eth_usd_rate_decimal

            # Extracting timestamp from block
            block_response = await session.get(
                f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={block_number}"
                f"&boolean=true&apikey={config.ETHERSCAN_API_KEY}")
            if block_response.status == 200:
                block_data = await block_response.json()
                if 'result' in block_data and 'timestamp' in block_data['result']:
                    timestamp = int(block_data['result']['timestamp'], 16)
                    print(f"\tTimestamp: {datetime.utcfromtimestamp(timestamp).strftime('%H:%M:%S %d-%m-%Y')}")
                else:
                    print("Error: 'result' or 'timestamp' not found in API response")

            # Extracting data from swap details
            tx_hash = tx_data['result']['hash']
            from_address = tx_data['result']['from']
            to_address = tx_data['result']['to']
            logs = receipt_data['result']['logs']
            logs_adress = receipt_data['result']['logs'][0]['address']
            logs_event_signature_hash = receipt_data['result']['logs'][0]['topics'][0]
            logs_data = receipt_data['result']['logs'][0]['data']

            # print(f'DEBUG: This is Log:\n{receipt_data["result"]["logs"]}\n')

            # After fetching transaction details successfully
            print(f"Gas Used: {gas_used} units")
            print(f"Effective Gas Price: {effective_gas_price} wei")
            print(f"\nTransaction Fees: {transaction_fee_wei} wei.")
            print(f"Transaction Fee ETH: {transaction_fee_eth}")
            print(f"Transaction Fee ETH 2: {transaction_fee_eth_2}")
            print(f"Transaction Fee USD: {transaction_fee_usd}")
            print(f"Total Fee: [CALCULATE ALL FEES IN SAME UNIT!]\n")
            print_swap_information(logs)

        else:
            raise Exception("Failed to fetch Transaction Details.")


# async def get_pair_address(token0, token1):
#     factory_contract = web3.eth.contract(address=FACTORY_CONTRACT_ADDRESS, abi=FACTORY_CONTRACT_ABI)
#     pair_address = factory_contract.functions.getPair(token0, token1).call()
#     print(f"Pair address for {token0} and {token1}: {pair_address}")
#     return pair_address

async def listen_for_swaps(liquidity_pool_instance, liquidity_pool_address):
    """Listen for swap events on a specified contract and print price details asynchronously."""
    for k, v in config.CONSOLIDATED_DICT['LQ_POOL'].items():
        if v.lower() == liquidity_pool_address.lower():
            print(f"Listening for swap events on {k} Liquidity Pool...\n")

    # Swap event filter for swap events on the specified liquidity pool
    swap_event_filter = liquidity_pool_instance.events.Swap.create_filter(fromBlock='latest')
    while True:
        await asyncio.sleep(0.1)
        new_entries = swap_event_filter.get_new_entries()
        for event in new_entries:
            await fetch_transaction_details(event['transactionHash'].hex())

            # Name of tokens
            token0, token1 = await get_token_addresses(POOL_1_ADRESS)
            token0 = await get_address_name(token0)
            token1 = await get_address_name(token1)

            # Liquidity Pool Reserves
            reserve_token0, reserve_token1, timestamp = await fetch_pool_reserves(liquidity_pool_instance)

            # Get ETH price
            eth_price = await get_eth_price()

            # Fetch ABIs asynchronously (This is just to make code work, this is not efficient)
            LIQUIDITY_POOL_ABI = await fetch_abi(LIQUIDITY_POOL_ABI_URL)
            LIQUIDITY_POOL_INSTANCE = web3.eth.contract(address=LIQUIDITY_POOL_ADDRESS, abi=LIQUIDITY_POOL_ABI)

            print(f"\nReserves for {token0}/{token1} pool:")
            print(f"{token0} Reserve: {reserve_token0}, {token1} Reserve: {reserve_token1}")
            print(f"{token0}'s Decimal's: {LIQUIDITY_POOL_INSTANCE.functions.decimals().call()}")
            print(f"{token1}'s Decimal's: {LIQUIDITY_POOL_INSTANCE.functions.decimals().call()}")
            # If one of the tokens is WETH, convert the other token's reserve to WETH for price calculation.
            if token0 == 'WETH' or token1 == 'WETH':
                token_price_in_eth = reserve_token1 / reserve_token0 if token0 == 'WETH' else reserve_token0 / reserve_token1
                print(f"Price of {token1 if token0 == 'WETH' else token0} in WETH: {token_price_in_eth}")
                print(f"Price of {token1 if token0 == 'WETH' else token0} in USD: {token_price_in_eth * eth_price}")



async def main():
    # Fetch ABIs asynchronously
    LIQUIDITY_POOL_ABI = await fetch_abi(LIQUIDITY_POOL_ABI_URL)

    # Create contract instances with the correct addresses and fetched ABIs
    LIQUIDITY_POOL_INSTANCE = web3.eth.contract(address=LIQUIDITY_POOL_ADDRESS, abi=LIQUIDITY_POOL_ABI)


    # Listen for swap events asynchronously (add to this, 3 more diffrecn pools, calulation fucntions seperate becuase of workings async?)
    await asyncio.gather(
        listen_for_swaps(LIQUIDITY_POOL_INSTANCE, LIQUIDITY_POOL_ADDRESS),
    )

# Run the main function
if __name__ == '__main__':
    asyncio.run(main())
