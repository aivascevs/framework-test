# Data Handling (C3)

Give an AI tool only the context that the task needs. Do not give it secrets or data above the class that the tool register permits.

This control is mostly **manual** and **advisory**. Scanners can find some secrets after you commit them. No scanner can prove that sensitive data did not go into a prompt.

## 1. Data classes

| Class | Examples | May go to an approved hosted AI tool? |
|---|---|---|
| public | Published documentation, open-source code, public prices | Yes |
| internal | Internal code, non-sensitive configuration, internal tickets | Yes, if `max_data_class` in `approved-tools.yaml` is `internal` or higher |
| confidential | Contracts, pricing logic, business rules that are not public, client code | Only if the register permits it for that tool |
| personal | Names, e-mail addresses, phone numbers, personal codes, IP addresses, user IDs linked to people | No, unless the register and a data-processing agreement permit it |
| secret | Credentials, private keys, tokens, special-category or regulated data | No |

## 2. Safe-context checklist

Before you start an AI-assisted task, check these items:

- [ ] The specification records the highest data class that the task touches.
- [ ] That class is not above `max_data_class` for the tool.
- [ ] The workspace does not contain `.env` files, key files or exported data that the task does not need.
- [ ] Test data is synthetic. It contains no real personal data.
- [ ] Logs, stack traces and tickets that you paste into the tool contain no secrets or personal data.
- [ ] For agents: the capability profile denies read access to credential files (A4).

## 3. If sensitive data went to a tool

1. Stop the session.
2. Tell the governance or security owner.
3. Rotate any credential that the tool received.
4. Record the event as an incident. Use the lessons to update this guidance.
