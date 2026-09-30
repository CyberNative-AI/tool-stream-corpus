"""Offline SSE/tool-call acceptance probe. Never executes a tool."""
from __future__ import annotations

import codecs
import json
import re
from pathlib import Path


class SSE:
    def __init__(self):
        self.decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
        self.line = ""
        self.data = []
        self.events = []
        self.cr = False

    def feed(self, chunk: bytes):
        for ch in self.decoder.decode(chunk):
            if ch == "\n" and self.cr:
                self.cr = False
                continue
            self.cr = False
            if ch in "\r\n":
                self.consume(self.line)
                self.line = ""
                self.cr = ch == "\r"
            else:
                self.line += ch

    def consume(self, line):
        if not line:
            if self.data:
                self.events.append("\n".join(self.data))
            self.data = []
        elif not line.startswith(":"):
            field, sep, value = line.partition(":")
            if field == "data":
                self.data.append(value[1:] if value.startswith(" ") else value)

    def finish(self):
        self.decoder.decode(b"", final=True)
        # SSE EOF does not dispatch an unterminated event.
        return self.events


def reference_events(blob):
    """Whole-buffer line parser: no transport boundaries to manage."""
    lines = re.split(r"\r\n|\r|\n", blob.decode("utf-8-sig"))
    data, events = [], []
    for line in lines[:-1]:
        if not line:
            if data:
                events.append("\n".join(data))
            data = []
        elif not line.startswith(":"):
            field, _, value = line.partition(":")
            if field == "data":
                data.append(value[1:] if value.startswith(" ") else value)
    return events


def accept(events, mode="terminal"):
    """Single-choice synthetic chat-delta dialect; output is proposed calls only."""
    tools, emitted, terminal = {}, {}, False
    for text in events:
        if text == "[DONE]":
            break
        event = json.loads(text)
        for choice in event["choices"]:
            if choice["index"] != 0:
                raise ValueError("only one choice supported")
            if terminal:
                raise ValueError("data after finish")
            for delta in choice.get("delta", {}).get("tool_calls", []):
                idx = delta["index"]
                tool = tools.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                if "id" in delta:
                    if tool["id"] and tool["id"] != delta["id"]:
                        raise ValueError("changed tool identity")
                    tool["id"] = delta["id"]
                fn = delta.get("function", {})
                tool["name"] += fn.get("name", "")
                tool["arguments"] += fn.get("arguments", "")
                if mode == "eager" and idx not in emitted and tool["name"]:
                    try:
                        args = json.loads(tool["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    emitted[idx] = {"id": tool["id"], "name": tool["name"], "arguments": args}
                elif mode == "json-ready" and idx not in emitted and tool["name"]:
                    try:
                        args = json.loads(tool["arguments"])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(args, dict):
                        emitted[idx] = {"id": tool["id"], "name": tool["name"], "arguments": args}
            reason = choice.get("finish_reason")
            if reason is not None:
                terminal = True
                if mode == "terminal" and reason == "tool_calls":
                    candidate = {}
                    for idx, tool in tools.items():
                        args = json.loads(tool["arguments"])
                        if not isinstance(args, dict) or not tool["name"] or not tool["id"]:
                            raise ValueError("invalid tool object")
                        candidate[idx] = {"id": tool["id"], "name": tool["name"], "arguments": args}
                    if len({x["id"] for x in candidate.values()}) != len(candidate):
                        raise ValueError("duplicate tool id")
                    emitted = candidate
    return [emitted[k] for k in sorted(emitted)]


def probe(chunks, mode="terminal", reference=False):
    try:
        if reference:
            events = reference_events(b"".join(chunks))
        else:
            decoder = SSE()
            for chunk in chunks:
                decoder.feed(chunk)
            events = decoder.finish()
        return {"calls": accept(events, mode), "error": None}
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        return {"calls": [], "error": type(exc).__name__}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stream", type=Path, help="synthetic or reviewed non-sensitive SSE capture")
    parser.add_argument("--chunk-bytes", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.chunk_bytes <= 100000:
        parser.error("chunk size must be 1..100000")
    if args.stream.stat().st_size > 100000:
        parser.error("capture exceeds 100000 bytes")
    blob = args.stream.read_bytes()
    result = probe([blob[i:i+args.chunk_bytes] for i in range(0, len(blob), args.chunk_bytes)])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
