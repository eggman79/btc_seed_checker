#!/usr/bin/env python3
"""
Check BTC balance for a BIP39 24‑word seed and optional passphrase.

Usage example:
    python check_btc_balance.py "abandon abandon ..." -p "myPassphrase"
"""

import argparse
import sys

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import requests


def derive_address(mnemonic: str, passphrase: str = "", account: int = 0, change: Bip44Changes = Bip44Changes.CHAIN_EXT, address_index: int = 0) -> str:
    """Derive a Bitcoin legacy (P2PKH) address from a mnemonic.

    The derivation follows BIP44: m/44'/0'/account'/change/address_index.
    """
    # Generate seed from mnemonic and passphrase
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate(passphrase)
    # BIP44 for Bitcoin (legacy)
    bip44_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    # Derive the full path
    bip44_acc = bip44_mst.Purpose().Coin().Account(account)

    bip44_chg = bip44_acc.Change(change)
    addr = bip44_chg.AddressIndex(address_index).PublicKey().ToAddress()
    return addr


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
    balance = get_balance(address)

    print(f"Address  : {balance['address']}")
    print(f"Confirmed: {sat_to_btc(balance['confirmed_sat']):.8f} BTC ({balance['confirmed_sat']} sat)")
    print(f"Mempool  : {sat_to_btc(balance['mempool_sat']):.8f} BTC ({balance['mempool_sat']} sat)")


if __name__ == "__main__":
    main()

