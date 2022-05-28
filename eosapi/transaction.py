from dataclasses import dataclass, field
from .packer import *
from typing import List, Dict
import hashlib
from base58 import b58encode
import json

@dataclass
class Account:
    account: str
    private_key: str
    permission: str = "active"

    def index(self):
        return "{0}-{1}".format(self.account, self.permission)

@dataclass
class Authorization:
    actor: str
    permission: str = "active"

    def pack(self):
        mbytes = b""
        mbytes += Name.pack(self.actor)
        mbytes += Name.pack(self.permission)
        return mbytes

    def to_dict(self):
        return {
            "actor": self.actor,
            "permission": self.permission,
        }

    def __str__(self):
        return json.dumps(self.to_dict())


@dataclass
class Action:
    account: str
    name: str
    authorization: List[Authorization]
    data: Dict = field(default_factory=dict)
    binargs: bytes = None

    def pack(self) -> bytes:
        mbytes = b""
        mbytes += Name.pack(self.account)
        mbytes += Name.pack(self.name)
        auth_bytes = [item.pack() for item in self.authorization]
        mbytes += Bytes.pack_array(auth_bytes)

        if self.binargs is None:
            raise EosApiException("no binargs, please serialize 'data' first")

        mbytes += VarUint32.pack(len(self.binargs))
        mbytes += self.binargs
        return mbytes

    def link(self, binargs: bytes):
        self.binargs = binargs

    def to_dict(self):
        return {
            "account": self.account,
            "name": self.name,
            "authorization": [item.to_dict() for item in self.authorization],
            "data": self.data,
        }

    def __str__(self):
        return json.dumps(self.to_dict())


@dataclass
class Transaction:
    actions: List[Action]
    expiration_delay_sec: int = 300
    delay_sec: int = 0
    max_cpu_usage_ms: int = 0
    max_net_usage_words: int = 0

    # params need link
    chain_id: int = None
    ref_block_num: int = None
    ref_block_prefix: int = None
    expiration: datetime.datetime = None

    signatures: List[str] = field(default_factory = list)

    def link(self, block_id: int, chain_id: int):
        self.chain_id = chain_id
        self.ref_block_num, self.ref_block_prefix = get_tapos_info(block_id)
        self.expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds = self.expiration_delay_sec)

    def pack(self) -> bytes:
        mbytes = b""
        mbytes += Time.pack(self.expiration)
        mbytes += Uint16.pack(self.ref_block_num)
        mbytes += Uint32.pack(self.ref_block_prefix)
        mbytes += VarUint32.pack(self.max_net_usage_words)
        mbytes += Uint8.pack(self.max_cpu_usage_ms)
        mbytes += VarUint32.pack(self.delay_sec)
        # context_free_actions
        mbytes += Int8.pack_array([])
        actions_bytes = [item.pack() for item in self.actions]
        mbytes += Bytes.pack_array(actions_bytes)
        # transaction_extensions
        mbytes += Int8.pack_array([])
        return mbytes

    def sign(self, private_key: str):
        chain_bytes = bytes.fromhex(self.chain_id)
        trans_bytes = self.pack()
        zero_bytes = b"\x00" * 32
        mbytes = chain_bytes + trans_bytes + zero_bytes
        signature = self.sign_bytes(mbytes, private_key)
        self.signatures.append(signature)

    def sign_bytes(self, mbytes: bytes, private_key: str) -> str:
        nonce = 0
        sha256 = hashlib.sha256()
        sha256.update(mbytes)
        while True:
            v, r, s = ecdsa_raw_sign_nonce(sha256.digest(), private_key, nonce)
            if is_canonical(r, s):
                signature = "00%02x%064x%064x" % (v, r, s)
                break
            nonce += 1

        return self.unpack_signature(bytes.fromhex(signature))

    def unpack_signature(self, signature: bytes):
        t = Uint8.unpack(signature)
        if t == 0:
            data = signature[Uint8.size: Uint8.size + 65]
            data = data + ripmed160(data + b"K1")[:4]
            return "SIG_K1_" + b58encode(data).decode("ascii")
        elif t == 1:
            raise EosApiException("not implementd")
        else:
            raise EosApiException("invalid binary signature")

    def to_dict(self):
        return {"actions": [item.to_dict() for item in self.actions]}

    def __str__(self):
        return json.dumps(self.to_dict())
