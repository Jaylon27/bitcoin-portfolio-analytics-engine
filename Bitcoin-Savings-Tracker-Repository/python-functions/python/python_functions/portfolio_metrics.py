from functions.api import function, Date, Integer, String
from ontology_sdk.ontology.objects import BitcoinTransaction
from datetime import timedelta
from typing import Optional, List, Dict, Any
from functions.sources import get_source
import time
import hashlib
import hmac
import base64
import json


# You can test your code in real time using the Live Preview feature, located in the
# Functions tab at the bottom of the screen.


@function
def get_amount_usd(transaction: BitcoinTransaction) -> float:
    return transaction.amount_usd


@function
def get_amount_btc(transaction: BitcoinTransaction) -> float:
    return transaction.amount_btc


@function(sources=["BTCPriceData"])
def get_current_price() -> float:
    btc_source = get_source("BTCPriceData")
    connection = btc_source.get_https_connection()
    base_url = connection.url
    client = connection.get_client()
    full_url = f"{base_url}/0/public/Ticker?pair=XXBTZUSD"
    response = client.get(full_url)
    data = response.json()
    last_trade_price = float(data["result"]["XXBTZUSD"]["c"][0])
    return last_trade_price


@function(sources=["BTCPriceData"])
def get_total_return(transactions: List[BitcoinTransaction]) -> Dict[BitcoinTransaction, float]:
    current_price = get_current_price()  # Fetch once for the whole batch
    results = {}

    for tx in transactions:
        current_value = tx.amount_btc * current_price
        results[tx] = current_value - tx.amount_usd

    return results


@function(sources=["BTCPriceData"])
def get_total_return_percentage(transactions: List[BitcoinTransaction]) -> Dict[BitcoinTransaction, float]:
    current_price = get_current_price()
    results = {}

    for tx in transactions:
        total_return = (tx.amount_btc * current_price) - tx.amount_usd
        results[tx] = (total_return / tx.amount_usd) * 100 if tx.amount_usd != 0 else 0.0

    return results


@function
def total_btc_holdings(transactions: List[BitcoinTransaction]) -> float:
    total_holdings = 0
    for tx in transactions:
        if tx.source == "IBIT" or (tx.source == "Sparrow" and tx.type == "Receive"):
            total_holdings += tx.amount_btc

    return total_holdings


@function(sources=["BTCPriceData"])
def total_profit_coinbase(transactions: List[BitcoinTransaction]) -> float:
    current_price = get_current_price()
    total_profit = 0.0

    for tx in transactions:
        if tx.source == "Coinbase":

            current_value = tx.amount_btc * current_price

            if tx.type == "Buy":
                total_profit += (current_value - tx.amount_usd)
            elif tx.type == "Sell":
                total_profit -= (current_value - tx.amount_usd)

    return total_profit


@function(sources=["BTCPriceData"])
def total_profit_gemini(transactions: List[BitcoinTransaction]) -> float:
    current_price = get_current_price()
    total_profit = 0.0

    for tx in transactions:

        if tx.source == "Gemini":

            current_value = tx.amount_btc * current_price

            if tx.type == "Buy":
                total_profit += (current_value - tx.amount_usd)
            elif tx.type == "Sell":
                total_profit -= (current_value - tx.amount_usd)

    return total_profit


@function(sources=["BTCPriceData"])
def total_profit_exodus(transactions: List[BitcoinTransaction]) -> float:
    current_price = get_current_price()
    total_profit = 0.0

    for tx in transactions:

        if tx.source == "Exodus":

            current_value = tx.amount_btc * current_price

            if tx.type == "Buy":
                total_profit += (current_value - tx.amount_usd)
            elif tx.type == "Sell":
                total_profit -= (current_value - tx.amount_usd)

    return total_profit


@function(sources=["BTCPriceData"])
def total_profit_ibit(transactions: List[BitcoinTransaction]) -> float:
    current_price = get_current_price()
    total_profit = 0.0

    for tx in transactions:

        if tx.source == "IBIT":
            current_value = tx.amount_btc * current_price

            if tx.type == "Buy":
                total_profit += (current_value - tx.amount_usd)
            elif tx.type == "Sell":
                total_profit -= (current_value - tx.amount_usd)

    return total_profit


@function(sources=["BTCPriceData"])
def total_profit_strike(transactions: List[BitcoinTransaction]) -> float:
    current_price = get_current_price()
    total_profit = 0.0

    for tx in transactions:

        if tx.source == "Strike":

            current_value = tx.amount_btc * current_price

            if tx.type == "Buy":
                total_profit += (current_value - tx.amount_usd)

            elif tx.type == "Sell" or (tx.type == "Send" and tx.notes != "Send to Cold Storage"):
                total_profit -= (current_value - tx.amount_usd)

    return total_profit


@function(sources=["BTCPriceData"])
def total_usd_profit(transactions: List[BitcoinTransaction]) -> float:
    strike_profit = total_profit_strike(transactions)
    gemini_profit = total_profit_gemini(transactions)
    ibit_profit = total_profit_ibit(transactions)
    coinbase_profit = total_profit_coinbase(transactions)
    exodus_profit = total_profit_exodus(transactions)

    total_profit = coinbase_profit + ibit_profit + exodus_profit + gemini_profit + strike_profit

    return total_profit


@function(sources=["BTCPriceData"])
def total_portfolio_value(transactions: List[BitcoinTransaction]) -> float:
    current_price = get_current_price()
    holdings = total_btc_holdings(transactions)
    return holdings * current_price

@function
def total_cost_basis(transactions: List[BitcoinTransaction]) -> float:
    total = 0.0
    for tx in transactions:
        if tx.type == "Buy":
            total += tx.amount_usd
    return total


@function
def average_purchase_price(transactions: List[BitcoinTransaction]) -> float:
    total_usd = 0.0
    total_btc = 0.0
    for tx in transactions:
        if tx.type == "Buy":
            total_usd += tx.amount_usd
            total_btc += tx.amount_btc
    return total_usd / total_btc if total_btc > 0 else 0.0


@function
def total_fees_paid(transactions: List[BitcoinTransaction]) -> float:
    return sum(tx.fee_usd for tx in transactions if tx.fee_usd is not None)


@function(sources=["BTCPriceData"])
def overall_return_percentage(transactions: List[BitcoinTransaction]) -> float:
    portfolio_value = total_portfolio_value(transactions)
    cost = total_cost_basis(transactions)
    return ((portfolio_value - cost) / cost) * 100 if cost > 0 else 0.0
