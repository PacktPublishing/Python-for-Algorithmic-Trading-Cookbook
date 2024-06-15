from ibapi.contract import Contract


def future(symbol, exchange, contract_month):
    contract = Contract()
    contract.symbol = symbol
    contract.exchange = exchange
    contract.lastTradeDateOrContractMonth = contract_month
    contract.secType = "FUT"

    return contract


def stock(symbol, exchange, currency):
    contract = Contract()
    contract.symbol = symbol
    contract.exchange = exchange
    contract.currency = currency
    contract.secType = "STK"

    return contract


def option(symbol, exchange, contract_month, strike, right):
    contract = Contract()
    contract.symbol = symbol
    contract.exchange = exchange
    contract.lastTradeDateOrContractMonth = contract_month
    contract.strike = strike
    contract.right = right
    contract.secType = "OPT"

    return contract
