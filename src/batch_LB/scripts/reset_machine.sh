#!/bin/bash

RESP="$(curl -sS -f -X POST "http://127.0.0.1:8000/reset/n9kSerial2")"
echo "$RESP" | jq .