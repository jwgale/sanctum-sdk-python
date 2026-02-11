"""Unit tests for the Sanctum wire protocol."""

import json
import struct
import pytest

from sanctum_ai.protocol import encode_frame, decode_frame
from sanctum_ai.exceptions import VaultError


class TestEncodeFrame:
    def test_roundtrip(self):
        obj = {"id": 1, "method": "authenticate", "params": {"agent_name": "test"}}
        frame = encode_frame(obj)
        decoded, remainder = decode_frame(frame)
        assert decoded == obj
        assert remainder == b""

    def test_length_prefix(self):
        obj = {"hello": "world"}
        frame = encode_frame(obj)
        length = struct.unpack(">I", frame[:4])[0]
        assert length == len(frame) - 4
        assert json.loads(frame[4:]) == obj

    def test_multiple_frames(self):
        a = {"id": 1}
        b = {"id": 2}
        data = encode_frame(a) + encode_frame(b)
        first, rest = decode_frame(data)
        assert first == a
        second, rest = decode_frame(rest)
        assert second == b
        assert rest == b""

    def test_compact_json(self):
        obj = {"key": "value", "nested": {"a": 1}}
        frame = encode_frame(obj)
        payload = frame[4:]
        # No extra whitespace
        assert b" " not in payload


class TestDecodeFrame:
    def test_incomplete_header(self):
        with pytest.raises(VaultError, match="Incomplete frame header"):
            decode_frame(b"\x00\x00")

    def test_incomplete_body(self):
        header = struct.pack(">I", 100)
        with pytest.raises(VaultError, match="Incomplete frame body"):
            decode_frame(header + b"short")


class TestRaiseOnError:
    def test_no_error(self):
        from sanctum_ai.protocol import raise_on_error
        raise_on_error({"id": 1, "result": {}})  # Should not raise

    def test_string_error(self):
        from sanctum_ai.protocol import raise_on_error
        with pytest.raises(VaultError, match="something went wrong"):
            raise_on_error({"id": 1, "error": "something went wrong"})

    def test_structured_error(self):
        from sanctum_ai.protocol import raise_on_error
        from sanctum_ai.exceptions import AccessDenied
        with pytest.raises(AccessDenied) as exc_info:
            raise_on_error({
                "id": 1,
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "not allowed",
                    "detail": "policy forbids",
                    "suggestion": "ask admin",
                },
            })
        assert exc_info.value.code == "ACCESS_DENIED"
        assert exc_info.value.detail == "policy forbids"
