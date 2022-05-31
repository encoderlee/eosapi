# eosapi
![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-brightgreen)
![python_version](https://img.shields.io/badge/python-%3E%3D%203.6-brightgreen)
![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
[![](https://img.shields.io/badge/blog-@encoderlee-red)](https://encoderlee.blog.csdn.net)

A simple, high-level and lightweight eosio sdk write by python.

# What is it?
eosapi is a python library to interact with EOSIO blockchains.

its main focus are bot applications on the blockchain.

# Install
```$ pip install eosapi```

# Using
```python
from eosapi import EosApi

api = EosApi(rpc_host="https://jungle3.greymass.com")
api.import_key("consumer1111", "5KWxgG4rPEXzHnRBaiVRCCE6WAfnqkRpTu1uHzJoQRzixqBB1k3")

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

resp = api.push_transaction(trx)
```
