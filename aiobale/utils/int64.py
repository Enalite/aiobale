from typing import Any, Union
from .protobuf import ProtoBuf


def decode_list(input_data: Union[str, bytes, Any]) -> list[int]:
    """"Decodes a hex string or bytes containing a sequence of int64 varints into a list of integers."""
    if isinstance(input_data, str):
        data = bytes.fromhex(input_data)
    else:
        data = input_data
        
    codec = ProtoBuf()
    encoded = codec.encode({"1": data})
    decoded = codec.decode(encoded, {"1": {"type": "packed_int"}})
    
    return decoded["1"]
