# Security, Data and Licence Questions

Ask yourself these five questions about the change. Turn each relevant answer into one requirement line. Each line must be checkable by a test, a scan or a review question.

| # | Question | Requirement it produces | Example |
|---|---|---|---|
| 1 | Which data does the change read, store, send or show? | DATA: what must not be logged, stored, returned or sent | **DATA1** — The service SHALL NOT write e-mail addresses to logs. |
| 2 | Who can call the new code, and with which input? | SEC: input validation and authorisation | **SEC1** — The endpoint SHALL reject an order ID that is not a positive integer. **SEC2** — Only the owner of an order SHALL be able to read it. |
| 3 | What can go wrong if the input is hostile? | SEC: injection, path traversal, unsafe deserialisation | **SEC3** — The query SHALL use parameters. It SHALL NOT build SQL text from input. |
| 4 | What is new: a dependency, an external service, a file format, copied code? | LIC and SEC for the new part | **LIC1** — New dependencies SHALL have a licence in `policy-config/allowed-licenses.txt`, or an approved exception. |
| 5 | What must never happen? | The main SHALL NOT | **SEC4** — A failed refund SHALL NOT change the order state. |

## Rules

- Write "None" in the security section only for a Routine change with no security effect.
- Elevated and above need at least one SEC line.
- Personal or secret data needs at least one DATA line.
- A possible new dependency needs a LIC line.
- Do not write generic lines such as "the code SHALL be secure". A reviewer cannot check them.
