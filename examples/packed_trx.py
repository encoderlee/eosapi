from eosapi import EosApi, Transaction
from requests import RequestException

api = EosApi(rpc_host="https://jungle3.greymass.com")

def main():
    print("packe transaction to packed_trx")
    trx = {
        "actions": [{
            "account": "eosio.token",
            "name": "transfer",
            "authorization": [
                {
                    "actor": "consumer1111",
                    "permission": "active",
                },
            ],
            "data": {
                "from": "consumer1111",
                "to": "consumer2222",
                "quantity": "0.0001 EOS",
                "memo": "by eosapi",
            },
        }]
    }
    trx = api.make_transaction(trx)
    packed_trx = list(trx.pack())
    print("packed_trx: {0}".format(packed_trx))



if __name__ == '__main__':
    main()
