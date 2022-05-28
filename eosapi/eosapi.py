from .transaction import Account, Authorization, Action, Transaction
import requests
import functools
from typing import List, Dict, Union
from .exceptions import TransactionException, NodeException

class EosApi:

    def __init__(self, rpc_host: str = "https://wax.pink.gg", timeout = 120):
        self.rpc_host = rpc_host
        self.accounts: Dict[str, Account] = {}
        self.cpu_payer: Account = None
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["User-Agent"] = "Mozilla/5.0"
        self.session.request = functools.partial(self.session.request, timeout=timeout)


    def import_key(self, account: str, private_key: str, permission: str = "active"):
        account = Account(account, private_key, permission)
        self.accounts[account.index()] = account

    def import_keys(self, accounts: Union[List[Dict], List[Account]]):
        for item in accounts:
            if isinstance(item, dict):
                account = Account(item["account"], item["private_key"], item["permission"])
            elif isinstance(item, Account):
                account = item
            else:
                raise TypeError("unknown account type")
            self.accounts[account.index()] = account

    def set_cpu_payer(self, account: str, private_key: str, permission: str = "active"):
        self.cpu_payer = Account(account, private_key, permission)

    def remove_cpu_payer(self):
        self.cpu_payer = None

    def post(self, url: str, post_data: Dict = None) -> requests.Response:
        resp = self.session.post(url, json = post_data)

        if resp.status_code == 500:
            raise TransactionException("transaction error: {0}".format(resp.text), resp)

        if resp.status_code >= 300 or resp.status_code < 200:
            raise NodeException("eos node error, bad http status code: {0}".format(resp.status_code), resp)

        return resp

    def abi_json_to_bin(self, code: str, action: str, args: Dict) -> bytes:
        url = self.rpc_host + "/v1/chain/abi_json_to_bin"
        post_data = {
            "code": code,
            "action": action,
            "args": args,
        }
        resp = self.post(url, post_data)
        binargs = resp.json().get("binargs")
        if binargs is None:
            raise NodeException("eos node error, not find binargs", resp)
        return bytes.fromhex(binargs)

    def get_info(self) -> Dict:
        url = self.rpc_host + "/v1/chain/get_info"
        resp = self.post(url)
        return resp.json()

    def post_transaction(self, trx: Transaction, compression: bool = False, packed_context_free_data: str = "") -> Dict:
        url = self.rpc_host + "/v1/chain/push_transaction"
        post_data = {
            "signatures": trx.signatures,
            "compression": compression,
            "packed_context_free_data": packed_context_free_data,
            "packed_trx": trx.pack().hex(),
        }
        resp = self.post(url, post_data)
        return resp.json()

    def get_table_rows(self, post_data: Dict) -> Dict:
        url = self.rpc_host + "/v1/chain/get_table_rows"
        resp = self.post(url, post_data)
        return resp.json()

    def make_transaction(self, trx: Dict) -> Transaction:
        # if cpu/net paid by another
        if self.cpu_payer:
            trx["actions"][0]["authorization"].insert(0, {
                "actor": self.cpu_payer.account,
                "permission": self.cpu_payer.permission,
            })

        # create trx
        actors = []
        actions = []
        for item in trx["actions"]:
            authorization = []
            for auth in item["authorization"]:
                authorization.append(Authorization(
                    actor=auth["actor"],
                    permission=auth["permission"]
                ))
                actor_premission = "{0}-{1}".format(auth["actor"], auth["permission"])
                if actor_premission not in actors:
                    actors.append(actor_premission)
            actions.append(Action(
                account=item["account"],
                name=item["name"],
                authorization=authorization,
                data=item["data"],
            ))
        trx = Transaction(actions=actions)

        # link actions, convert data to binargs
        for item in trx.actions:
            binargs = self.abi_json_to_bin(item.account, item.name, item.data)
            item.link(binargs)

        # link trx by latest block info
        net_info = self.get_info()
        trx.link(net_info["last_irreversible_block_id"], net_info["chain_id"])

        # sign trx by private keys
        signed_keys = []
        for actor_premission in actors:
            if actor_premission in self.accounts:
                private_key = self.accounts[actor_premission].private_key
            elif self.cpu_payer and actor_premission == self.cpu_payer.index():
                private_key = self.cpu_payer.private_key
            else:
                continue
            if private_key not in signed_keys:
                trx.sign(private_key)
                signed_keys.append(private_key)

        return trx

    def push_transaction(self, trx: Union[Dict, Transaction], extra_signatures: Union[str, List[str]] = None) -> Dict:
        if isinstance(trx, dict):
            trx = self.make_transaction(trx)
        if extra_signatures:
            if isinstance(extra_signatures, str):
                extra_signatures = [extra_signatures]
            for item in extra_signatures:
                if item not in trx.signatures:
                    trx.signatures.append(item)

        return self.post_transaction(trx)
