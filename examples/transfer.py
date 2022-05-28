from eosapi import EosApi, NodeException, TransactionException
from requests import RequestException

account_name = "consumer1111"
private_key = "5KWxgG4rPEXzHnRBaiVRCCE6WAfnqkRpTu1uHzJoQRzixqBB1k3"

api = EosApi(rpc_host="https://jungle3.greymass.com", timeout=60)
api.import_key(account_name, private_key)

def main():
    print("transfer EOS token from [consumer1111] to [consumer2222] by eosapi")
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
    try:
        resp = api.push_transaction(trx)
        print("transaction ok: {0}".format(resp))
    except RequestException as e:
        print("network error: {0}".format(str(e)))
    except NodeException as e:
        print("eos node error, http status code {0}, response text: {1}".format(e.resp.status_code, e.resp.text))
    except TransactionException as e:
        print("eos transaction error, http status code {0}, response text: {1}".format(e.resp.status_code, e.resp.text))


def advance():
    # api.session isinstance of requests.Session
    # you can modify any of its properties

    # e.g If you want to set up an http proxy
    proxy = "127.0.0.1:1081"
    api.session.proxies = {
        "http": "http://{0}".format(proxy),
        "https": "http://{0}".format(proxy),
    }

    # e.g if you want to modify the http request header
    api.session.headers["User-Agent"] = "Mozilla/5.0"


if __name__ == '__main__':
    main()
