import re
import requests
from cryptos_f.transaction import public_txhash
from .utils import parse_addr_args

# Documentation: https://blockchair.com/api/docs

def get_url(coin_symbol):
    if coin_symbol == "BTC":
        return "https://api.blockchair.com/bitcoin"
    return "https://api.blockchair.com/bitcoin/testnet"
          
sendtx_url = "%s/push/transaction"
address_url = "%s/dashboards/address/%s"
utxo_url = "%s/dashboards/address/%s?limit=1000"
utxom_url = "%s/dashboards/addresses/%s?limit=1000"
fetchtx_url = "%s/dashboards/transaction/%s"
block_height_url = "%s/raw/block/%s"
latest_block_url = "%s/stats"
block_info_url = "%s/raw/block/%s"


def balance(*args, coin_symbol="BTC"):
    addrs = parse_addr_args(*args)
    if len(addrs) == 0:
        return []

    base_url = get_url(coin_symbol)

    if len(addrs) == 1:
        url = utxo_url % (base_url, addrs[0])
    else:
        url = utxom_url % (base_url, ','.join(addrs))

    response = requests.get(url)
    balances = []
    try:
        outputs = response.json()['data']

        if len(addrs) == 1:
            for i in outputs:
                balances.append(outputs[i]['address']['balance'])
        else:
            for i in outputs['addresses']:
                balances.append(outputs['addresses'][i]['balance'])

        if len(balances) == 1:
            return balances[0]
        else:
            tot = 0
            for b in balances:
                tot = tot + b
            return tot

    except (ValueError, KeyError):
        raise Exception("Unable to decode JSON from result: %s" % response.text)


def unspent(*args, coin_symbol="BTC"):

    addrs = parse_addr_args(*args)

    if len(addrs) == 0:
        return []

    base_url = get_url(coin_symbol)

    if len(addrs) == 1:
        url = utxo_url % (base_url, addrs[0])
    else:
        url = utxom_url % (base_url, ','.join(addrs))

    response = requests.get(url)

    try:

        outputs = response.json()['data']
        outs = []

        for i in outputs:
            d = {}
            for j in outputs[i]['utxo']:
                d = {
                    "output": j['transaction_hash']+':'+str(j['index']),
                    "value": j['value']
                }
                if d != {}:
                    outs.append(d)
        return outs
    except (ValueError, KeyError):
        raise Exception("Unable to decode JSON from result: %s" % response.text)


def fetchtx(txhash, coin_symbol="BTC"):
    base_url = get_url(coin_symbol)
    url = fetchtx_url % (base_url, txhash)
    response = requests.get(url)
    try:
        return response.json()
    except ValueError:
        raise Exception("Unable to decode JSON in %s from result: %s" % (url, response.text))


def tx_hash_from_index(index, coin_symbol="BTC"):
    result = fetchtx(index, coin_symbol=coin_symbol)
    return result['hash']

def txinputs(txhash, coin_symbol="BTC"):
    result = fetchtx(txhash, coin_symbol=coin_symbol)
    inputs = result['inputs']
    unspents = [{'output': "%s:%s" % (
    tx_hash_from_index(i["prev_out"]['tx_index'], coin_symbol=coin_symbol), i["prev_out"]['n']),
                 'value': i["prev_out"]['value']} for i in inputs]
    return unspents


def pushtx(tx, coin_symbol="BTC"):
    if not re.match('^[0-9a-fA-F]*$', tx):
        tx = tx.encode('hex')

    base_url = get_url(coin_symbol)
    url = sendtx_url % base_url
    hash = public_txhash(tx)

    response = requests.post(url, {'data': tx})
    if response.status_code == 200:
        return {'status': 'success',
                'data': {
                    'txid': hash,
                    'network': coin_symbol
                    }
                }
    return response

# Gets the transaction output history of a given set of addresses,
# including whether or not they have been spent
def history(*args, coin_symbol="BTC"):
    # Valid input formats: history([addr1, addr2,addr3])
    #                      history(addr1, addr2, addr3)

    addrs = parse_addr_args(*args)

    if len(addrs) == 0:
        return []

    base_url = get_url(coin_symbol)
    url = address_url % (base_url, '|'.join(addrs))
    response = requests.get(url)
    return response.json()

def block_height(txhash, coin_symbol="BTC"):
    tx = fetchtx(txhash, coin_symbol=coin_symbol)
    return tx['data'][txhash]['transaction']['block_id']

def block_info(height, coin_symbol="BTC"):
    base_url = get_url(coin_symbol)
    url = block_height_url % (base_url, height)
    response = requests.get(url)
    blocks = response.json()['blocks']
    data = list(filter(lambda d: d['main_chain'], blocks))[0]
    return {
        'version': data['ver'],
        'hash': data['hash'],
        'prevhash': data['prev_block'],
        'timestamp': data['time'],
        'merkle_root': data['mrkl_root'],
        'bits': data['bits'],
        'nonce': data['nonce'],
        'tx_hashes': [t['hash'] for t in data['tx']]
    }

def current_block_height(coin_symbol="BTC"):
    base_url = get_url(coin_symbol)
    url = latest_block_url % base_url
    response = requests.get(url)
    return response.json()["data"]["best_block_height"]
