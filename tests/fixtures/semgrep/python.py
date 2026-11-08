# Test file for policy-config/semgrep/python.yaml (semgrep --test format).
# "ruleid" marks a line that MUST match. "ok" marks a line that MUST NOT match.
import hashlib
import logging
import os
import subprocess

import requests

LOG = logging.getLogger(__name__)


def unsafe(cur, order_id, email, cmd):
    # ruleid: python-sql-built-from-strings
    cur.execute(f"SELECT * FROM orders WHERE id = {order_id}")
    # ruleid: python-sql-built-from-strings
    cur.execute("SELECT * FROM orders WHERE id = " + order_id)
    # ruleid: python-sql-built-from-strings
    cur.execute("SELECT * FROM orders WHERE id = %s" % order_id)
    # ruleid: python-sql-built-from-strings
    cur.execute("SELECT * FROM orders WHERE id = {}".format(order_id))
    # ruleid: python-sql-built-from-strings
    cur.execute(
        f"SELECT * FROM orders "
        f"WHERE id = {order_id}"
    )
    # ruleid: python-dynamic-code-execution
    eval(cmd)
    # ruleid: python-subprocess-shell
    subprocess.run(cmd, shell=True)
    # ruleid: python-subprocess-shell
    os.system(cmd)
    # ruleid: python-weak-hash
    hashlib.md5(email.encode())
    # ruleid: python-tls-verification-disabled
    requests.get("https://example.test", verify=False)
    # ruleid: python-hardcoded-credential
    api_key = "synthetic-not-a-real-key-123456"
    # ruleid: python-personal-data-in-logs
    LOG.info("login for %s", email)
    return api_key


def safe(cur, order_id, email, mask_email):
    # ok: python-sql-built-from-strings
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    # ok: python-sql-built-from-strings
    cur.execute("SELECT * FROM orders " "WHERE id = ?", (order_id,))
    # ok: python-subprocess-shell
    subprocess.run(["pytest", "-q"])
    # ok: python-weak-hash
    hashlib.sha256(email.encode())
    # ok: python-weak-hash
    hashlib.md5(b"cache-key", usedforsecurity=False)
    # ok: python-tls-verification-disabled
    requests.get("https://example.test", timeout=5)
    # ok: python-hardcoded-credential
    api_key = os.environ.get("API_KEY", "")
    # ok: python-personal-data-in-logs
    LOG.info("login for %s", mask_email(email))
    # ok: python-personal-data-in-logs
    LOG.info("order %s refunded", order_id)
    return api_key
