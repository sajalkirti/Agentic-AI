import pandas as pd
import random
from datetime import datetime, timedelta

modules = ["User", "Card"]
levels = ["INFO", "WARN", "ERROR"]
users = [f"driver{i:02d}" for i in range(1,21)]
cards = [f"FUEL{i:03d}" for i in range(1,51)]
start_time = datetime(2026,4,21,9,0,0)

# Application Log
app_rows = []
for i in range(100):
    ts = start_time + timedelta(seconds=i*5)
    module = random.choice(modules)
    level = random.choice(levels)
    if module=="User":
        event = random.choice(["Login Success","Profile Updated","Profile Update Failed","Password Reset Failed","Logout Success"])
        detail = f"User={random.choice(users)}"
    else:
        event = random.choice(["Card Issued","Transaction Recorded","Transaction Failed","Card Blocked"])
        detail = f"Card={random.choice(cards)}, User={random.choice(users)}"
    app_rows.append({"Timestamp":ts,"Module":module,"Level":level,"Event":event,"Details":detail})
pd.DataFrame(app_rows).to_excel("ApplicationLog.xlsx",index=False)

# Log Analytics
analytics_rows = []
for i in range(100):
    ts = start_time + timedelta(seconds=i*6)
    module = random.choice(modules)
    level = random.choice(levels)
    user = random.choice(users)
    card = random.choice(cards)
    event = random.choice(["Login Success","Profile Update Failed","Logout Success"]) if module=="User" else random.choice(["Card Issued","Transaction Failed","Card Blocked"])
    extra = "OK" if level=="INFO" else "Issue"
    analytics_rows.append({"Timestamp":ts,"Module":module,"Level":level,"Event":event,"User/Card":user if module=="User" else card,"Extra Details":extra})
pd.DataFrame(analytics_rows).to_excel("LogAnalytics.xlsx",index=False)

# DB Log
db_rows = []
for i in range(100):
    ts = start_time + timedelta(seconds=i*7)
    op = random.choice([
        f"INSERT INTO users (id,email) VALUES ('{random.choice(users)}','{random.choice(users)}@shellfleet.com');",
        f"INSERT INTO cards (card_id,user_id) VALUES ('{random.choice(cards)}','{random.choice(users)}');",
        f"UPDATE users SET email=NULL WHERE id='{random.choice(users)}';",
        f"INSERT INTO transactions (card_id,liters) VALUES ('{random.choice(cards)}',{random.randint(10,100)});"
    ])
    status = random.choice(["SUCCESS","ERROR"])
    detail = "" if status=="SUCCESS" else random.choice(["Constraint violation","Duplicate key","Invalid token","Timeout"])
    db_rows.append({"Timestamp":ts,"SQL Operation":op,"Status":status,"Error Details":detail})
pd.DataFrame(db_rows).to_excel("DBLog.xlsx",index=False)
