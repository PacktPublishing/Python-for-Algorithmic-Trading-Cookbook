from ibapi.contract import Contract, ComboLeg


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


def combo_leg(contract_details, ratio, action):
    leg = ComboLeg()
    leg.conId = contract_details.contract.conId
    leg.ratio = ratio
    leg.action = action
    leg.exchange = contract_details.contract.exchange

    return leg


def spread(legs):
    contract = Contract()
    contract.symbol = "USD"
    contract.secType = "BAG"
    contract.currency = "USD"
    contract.exchange = "SMART"
    contract.comboLegs = legs

    return contract
