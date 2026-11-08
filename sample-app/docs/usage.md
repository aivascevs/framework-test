# Sample Application: Usage

The sample application is a small order store for the governance demonstrator. It uses only the Python standard library. All data is synthetic.

| Module | Purpose | Minimum risk class (`policy-config/risk-paths.yaml`) |
|---|---|---|
| `orders/store.py` | Store, read and refund orders (SQLite in memory) | Elevated |
| `orders/api.py` | Request handlers: check the caller, validate input | Elevated |
| `auth/tokens.py` | Token check and roles | High impact |
| `docs/` | This documentation | Routine |

Run the tests from the `sample-app` folder:

```bash
pytest -q
```
