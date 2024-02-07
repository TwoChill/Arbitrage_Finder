import asyncio
import aiohttp
import pandas as pd


async def fetch_tokens_list(network_id):
    """ Fetches the list of tokens for a given network from Paraswap API. """
    url = f"https://apiv5.paraswap.io/tokens/{network_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                tokens = await response.json()
                return tokens
            else:
                print(f"Failed to fetch tokens list: HTTP {response.status}")
                return None


async def main():
    """ Main function that fetches the list of tokens for Ethereum Mainnet. """
    network_id = '1'  # Example: '1' for Ethereum Mainnet. Adjust as needed for different networks.
    response = await fetch_tokens_list(network_id)
    if response and 'tokens' in response:  # Check if 'tokens' key exists in the response
        tokens_list = response['tokens']  # Access the list of tokens using the 'tokens' key
        df = pd.DataFrame(tokens_list, columns=['symbol', 'address'])
        print("Fetched Tokens List From Paraswap:\n")
        print(df)
    else:
        print("Could not fetch tokens list.")


if __name__ == '__main__':
    asyncio.run(main())
