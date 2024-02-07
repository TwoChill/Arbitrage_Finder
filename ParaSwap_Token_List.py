import subprocess
import sys
from os import system
from time import sleep


def check_and_install_module(module_name):
    try:
        if module_name in sys.modules:
            __import__(module_name)
    except ImportError:
        user_approval = input(f"\n{module_name} is not installed. Do you want to install it? (y/n): ")
        if user_approval.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            print(f"{module_name} has been successfully installed.")
        else:
            print("Installation aborted by the user.")


check_and_install_module('asyncio')
import asyncio
check_and_install_module('aiohttp')
import aiohttp
check_and_install_module('pandas')
import pandas as pd
check_and_install_module('pyarrow')
import pyarrow


system('cls' if sys.platform == 'win32' else 'clear')


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
        input("\n\nPress Enter to continue...")
    else:
        print("Could not fetch tokens list.")


if __name__ == '__main__':
    asyncio.run(main())
    
    
