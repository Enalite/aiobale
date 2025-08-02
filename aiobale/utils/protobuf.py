import base64
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union

from blackboxprotobuf import decode_message, encode_message


def _read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    result = 0
    shift = 0
    i = pos
    while i < len(data):
        b = data[i]
        result |= (b & 0x7F) << shift
        i += 1
        if not (b & 0x80):
            return result, i - pos
        shift += 7
    raise ValueError("Unexpected end of data while reading varint")


def _parse_length_delimited(data: bytes, pos: int) -> Tuple[bytes, int]:
    length, n_len = _read_varint(data, pos)
    start = pos + n_len
    end = start + length
    if end > len(data):
        raise ValueError("Invalid length-delimited field: data too short")
    return data[start:end], n_len + length


def _parse_protobuf_fields(data: bytes) -> List[Tuple[int, int, bytes]]:
    i = 0
    out: List[Tuple[int, int, bytes]] = []
    length = len(data)
    while i < length:
        try:
            tag, n_tag = _read_varint(data, i)
        except Exception as e:
            raise ValueError(f"Error reading tag at position {i}: {e}")

        field_no = tag >> 3
        wire_type = tag & 0x7
        i += n_tag

        if wire_type == 0:  # varint
            value, n_val = _read_varint(data, i)
            out.append(
                (
                    field_no,
                    wire_type,
                    value.to_bytes((value.bit_length() + 7) // 8 or 1, "little"),
                )
            )
            i += n_val
        elif wire_type == 1:  # 64-bit
            if i + 8 > length:
                raise ValueError("Invalid 64-bit field: data too short")
            out.append((field_no, wire_type, data[i : i + 8]))
            i += 8
        elif wire_type == 2:  # length-delimited
            raw_bytes, n_tot = _parse_length_delimited(data, i)
            out.append((field_no, wire_type, raw_bytes))
            i += n_tot
        elif wire_type == 5:  # 32-bit
            if i + 4 > length:
                raise ValueError("Invalid 32-bit field: data too short")
            out.append((field_no, wire_type, data[i : i + 4]))
            i += 4
        else:
            raise ValueError(f"Unknown wire type {wire_type} at position {i}")
    return out


def _is_valid_text(s: str, check_first_bytes: bool = True) -> bool:
    if s.isdigit():
        return True

    if re.findall(r"(\\x[0-9A-Fa-f]{2}|\\n|\\r|\\t)", s):
        escape_like = len(re.findall(r"(\\x[0-9A-Fa-f]{2}|\\n|\\r|\\t)", s))
        if escape_like / max(len(s), 1) > 0.1:
            return False

    printable = sum(1 for c in s if unicodedata.category(c)[0] in ("L", "N", "P", "Z"))
    total = len(s)

    if total and (printable / total) > 0.95:
        if check_first_bytes and len(s) >= 5:
            return _is_valid_text(s[:5], False)
        return True
    return False


class ProtoBuf:
    def encode(
        self,
        data: Dict[str, Any],
        force_raw: bool = True,
        type_def: Optional[Dict[str, Any]] = None,
    ) -> Union[bytes, str]:
        typedef = self.infer_typedef(data)
        if type_def:
            typedef.update(type_def)

        encoded = encode_message(data, typedef)
        return encoded if force_raw else base64.b64encode(encoded).decode("utf-8")

    def decode(
        self, value: bytes, type_def: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        decoded, _ = decode_message(value, type_def)
        return self._convert_bytes_to_string(self._fix_fields(decoded, value))

    def _fix_fields(self, data: Any, raw_message_bytes: bytes) -> Any:
        if isinstance(data, dict):
            try:
                entries = _parse_protobuf_fields(raw_message_bytes)
            except Exception as e:
                print(e)
                return data

            new_data: Dict[str, Any] = {}

            for key, value in data.items():
                pure_key = key.split("-")[0]
                candidates = [e for e in entries if e[0] == int(pure_key) and e[1] == 2]

                fixed: Optional[str] = None
                if candidates:
                    rb = candidates[0][2]
                    try:
                        text = rb.decode("utf-8")
                    except UnicodeDecodeError:
                        text = rb.decode("latin-1", errors="ignore")
                    if _is_valid_text(text):
                        fixed = text

                if fixed is not None:
                    new_data[key] = fixed
                elif isinstance(value, dict) and candidates:
                    new_data[key] = self._fix_fields(value, candidates[0][2])
                elif isinstance(value, list):
                    new_data[key] = [
                        self._fix_fields(v, raw_message_bytes) for v in value
                    ]
                else:
                    new_data[key] = value

            return new_data

        if isinstance(data, list):
            return [self._fix_fields(item, raw_message_bytes) for item in data]

        return data

    def _convert_bytes_to_string(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._convert_bytes_to_string(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_bytes_to_string(v) for v in obj]
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return obj
        return obj

    def infer_typedef(self, message_dict: Dict[str, Any]) -> Dict[str, Any]:
        typedef: Dict[str, Any] = {}
        for field_num, value in message_dict.items():
            if isinstance(value, list):
                elem = value[0] if value else {}
                if isinstance(elem, dict):
                    sub_typedef = self.infer_typedef(elem)
                    typedef[field_num] = {
                        "rule": "repeated",
                        "type": "message",
                        "message_typedef": sub_typedef,
                        "name": "",
                    }
                else:
                    base_type = "int" if isinstance(elem, int) else "bytes"
                    typedef[field_num] = {
                        "rule": "repeated",
                        "type": base_type,
                        "name": "",
                    }
            elif isinstance(value, dict):
                sub_typedef = self.infer_typedef(value)
                typedef[field_num] = {
                    "type": "message",
                    "message_typedef": sub_typedef,
                    "name": "",
                }
            elif isinstance(value, int):
                typedef[field_num] = {"type": "int", "name": ""}
            else:
                typedef[field_num] = {"type": "bytes", "name": ""}

        return typedef
