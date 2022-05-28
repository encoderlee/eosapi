# This example shows how to use ONLY_BILL_FIRTH_AUTHORIZER feature

from eosapi import EosApi

account_name = "consumer1111"
private_key = "5KWxgG4rPEXzHnRBaiVRCCE6WAfnqkRpTu1uHzJoQRzixqBB1k3"
payer_name = "payer2222222"
payer_private_key = "5KAskRRbqYVCRhZxLXqeg9yvWYQQHifDtf7BPceZUDw6zybjaQh"

api = EosApi(rpc_host="https://jungle3.greymass.com")
api.import_key(account_name, private_key)
api.set_cpu_payer(payer_name, payer_private_key)


def main():
    print("transfer EOS token from [consumer1111] to [consumer2222] by eospy")
    print("but let [payer2222222] pay for CPU/NET resources of this transaction")
    trx = {
        "actions": [{
            "account": "eosio.token",
            "name": "transfer",
            "authorization": [
                {
                    "actor": account_name,
                    "permission": "active",
                },
            ],
            "data": {
                "from": account_name,
                "to": "consumer2222",
                "quantity": "0.0001 EOS",
                "memo": "by eosapi",
            },
        }]
    }
    resp = api.push_transaction(trx)
    print("transaction ok: {0}".format(resp))



if __name__ == '__main__':
    main()
