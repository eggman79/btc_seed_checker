#!/usr/bin/env python3
"""
Check BTC balance for a BIP39 24‑word seed and optional passphrase.

Usage example:
    python check_btc_balance.py "abandon abandon ..." -p "myPassphrase"
"""

import argparse
import sys

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes, Bip84, Bip84Coins
import requests
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Address:
    native: str
    segwit: str

def derive_address(mnemonic: str, passphrase: str = "", account: int = 0, change: Bip44Changes = Bip44Changes.CHAIN_EXT, address_index: int = 0) -> Address:
    """Derive a Bitcoin legacy (P2PKH) address from a mnemonic.

    The derivation follows BIP44: m/44'/0'/account'/change/address_index.
    """
    # Generate seed from mnemonic and passphrase
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate(passphrase)

    def get_address(seed_bytes, native) -> str:
        coins = Bip44Coins.BITCOIN if native else Bip84Coins.BITCOIN
        bip_module = Bip44 if native else Bip84
        bip_mst = bip_module.FromSeed(seed_bytes, coins)
        bip_acc = bip_mst.Purpose().Coin().Account(account)
        bip_chg = bip_acc.Change(change)
        addr = bip_chg.AddressIndex(address_index).PublicKey().ToAddress()
        return addr

    return Address(get_address(seed_bytes, True), get_address(seed_bytes, False))


def get_balance(address: str) -> dict:
    """Query Blockstream's API for confirmed and mempool balances (in satoshis)."""
    url = f"https://blockstream.info/api/address/{address}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    confirmed = (
        data.get('chain_stats', {}).get('funded_txo_sum', 0)
        - data.get('chain_stats', {}).get('spent_txo_sum', 0)
    )
    mempool = (
        data.get('mempool_stats', {}).get('funded_txo_sum', 0)
        - data.get('mempool_stats', {}).get('spent_txo_sum', 0)
    )
    return {"address": address, "confirmed_sat": confirmed, "mempool_sat": mempool}


def sat_to_btc(sat: int) -> float:
    return sat / 1e8


def main():
    parser = argparse.ArgumentParser(description="Check Bitcoin balance from a BIP39 24‑word seed.")
    parser.add_argument("mnemonic", help="24‑word BIP39 seed phrase (enclose in quotes).")
    parser.add_argument("-p", "--passphrase", default="", help="Optional BIP39 passphrase.")
    parser.add_argument("-i", "--index", type=int, default=0, help="Address index to check (default 0).")
    args = parser.parse_args()

    # Basic validation of word count
    if len(args.mnemonic.split()) not in (12, 15, 18, 21, 24):
        sys.exit("Error: mnemonic must be 12, 15, 18, 21 or 24 words.")

    address = derive_address(args.mnemonic, args.passphrase, address_index=args.index)

    def print_balance(address):
        balance = get_balance(address)

        print(f"Address  : {balance['address']}")
        print(f"Confirmed: {sat_to_btc(balance['confirmed_sat']):.8f} BTC ({balance['confirmed_sat']} sat)")
        print(f"Mempool  : {sat_to_btc(balance['mempool_sat']):.8f} BTC ({balance['mempool_sat']} sat)")

    print('===============================================')
    print('Legacy')
    print('===============================================')
    print_balance(address.native)
    print('===============================================')
    print('Segwit')
    print('===============================================')
    print_balance(address.segwit)


if __name__ == "__main__":
    main()

