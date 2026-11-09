"""Writes an invented Slim CD SearchTransactions2 reply in tests/canned/search-reply.json: 36 card transactions
of a fictional shop in October 2026, every value as text. Card numbers are masked and invented; the shape of the
reply (reply > datablock > Transactions > Transaction) follows the block's script.
Run from the block folder: python3 tests/make_canned.py
"""
import datetime as dt
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(8)

people = [("Amelia", "Hart", "Boston", "MA", "02134"), ("Noah", "Becker", "Cambridge", "MA", "02139-4307"),
          ("Grace", "Okoro", "Providence", "RI", "02903"), ("Liam", "Novak", "Hartford", "CT", "06103"),
          ("Chloe", "Ramos", "Worcester", "MA", "01608"), ("Ethan", "Kowalski", "Nashua", "NH", "03060")]
clerks = ["Dana", "Marcus", "Priya"]
transactions = []
when = dt.datetime(2026, 10, 1, 9, 0)
for i in range(36):
    when += dt.timedelta(minutes=rng.randint(40, 1100))
    first, last, city, state, zip_ = rng.choice(people)
    kind = "RETURN" if i % 9 == 4 else "SALE"
    approved = "N" if i % 13 == 7 else "Y"
    amount = round(rng.uniform(6, 240), 2)
    card = rng.choice(["VISA", "MC", "AMEX", "DISC"])
    transactions.append({
        "gateid": str(1840221000 + i * 7), "transactiondate": when.strftime("%-m/%-d/%Y %-I:%M:%S %p"),
        "transtype": kind, "processor": "DEMO", "siteid": "100200300", "batchno": str(310 + (when.day - 1)),
        "approved": approved, "cardtype": card, "cardpresent": "true" if i % 4 else "false",
        "proc_code": "00" if approved == "Y" else "05", "cardid": str(7700 + i % 11),
        "cardnumber": "XXXXXXXXXXXX" + str(1000 + rng.randint(0, 8999)), "amount": f"{amount:.2f}",
        "authcode": f"{rng.randint(0, 999999):06d}" if approved == "Y" else "", "cvv2reply": "M", "avsreply": "Y",
        "checkid": "", "checkno": "", "routeno": "", "accountnumber": "", "trackindicator": "1",
        "voided": "1" if i == 20 else "0", "requestingip": "", "remoteip": "", "firstname": first,
        "lastname": last, "address": "", "city": city, "state": state, "zip": zip_, "country": "US", "phone": "",
        "email": f"{first.lower()}.{last.lower()}@example.com", "proc_response": "APPROVED" if approved == "Y"
        else "DECLINED", "clerkname": rng.choice(clerks), "po": "", "salestax": f"{amount * 0.0625:.2f}",
        "salestaxtype": "1", "tip": "0.00", "clienttransref": f"POS-{5000 + i}", "giftbalance": "",
        "cashback": "0.00",
    })
reply = {"reply": {"response": "Success", "responsecode": "0", "description": "OK", "responseurl": "",
                   "datablock": {"Transactions": {"Transaction": transactions}}}}
os.makedirs(os.path.join(HERE, "canned"), exist_ok=True)
with open(os.path.join(HERE, "canned", "search-reply.json"), "w", encoding="utf-8") as fh:
    json.dump(reply, fh, indent=1)
