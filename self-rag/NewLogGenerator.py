import pandas as pd
import uuid
import random
from datetime import datetime, timedelta
import os

# -----------------------------
# CONFIG
# -----------------------------
project_folder = os.path.join(os.path.dirname(__file__), "documents")

NUM_INCIDENTS = 120
STEPS_RANGE = (3, 5)

base_time = datetime.now()

# -----------------------------
# FLEET ENTITIES
# -----------------------------
drivers = [f"driver_{i}" for i in range(1, 80)]
vehicles = [f"BH-FL-{str(i).zfill(4)}" for i in range(1, 200)]
merchants = [
    "EV Charging Hub",
    "Highway Toll Plaza",
    "City Parking Zone",
    "Fuel Station",
    "Battery Swap Center"
]

methods = [
    "WalletController.Debit",
    "PaymentController.Process",
    "TollController.Pay",
    "ChargingController.StartSession",
    "BookingController.ReserveSlot"
]

events = [
    "Wallet Debit",
    "Charging Started",
    "Toll Payment",
    "Parking Entry",
    "Fuel Purchase"
]

errors = [
    "InsufficientBalanceException",
    "TimeoutException",
    "PaymentGatewayFailure",
    "RFIDReadFailure",
    "SessionExpiredException"
]

# -----------------------------
# STACK TRACE BUILDER
# -----------------------------
def stack_trace(error):
    return f"""{error}: Transaction failed
   at FleetCore.Controllers.PaymentController.Process()
   at FleetCore.Services.WalletService.Debit()
   at FleetCore.Repositories.TransactionRepository.Save()"""

# -----------------------------
# CORRELATION ID
# -----------------------------
def cid():
    return f"CID-{uuid.uuid4().hex[:8].upper()}"

def ts(i, j):
    return (base_time + timedelta(seconds=i*30 + j*3)).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------
# OUTPUT LISTS
# -----------------------------
app_logs = []
analytics_logs = []
db_logs = []
MAX_LOGS_PER_CID = 5
# -----------------------------
# GENERATION
# -----------------------------
for i in range(NUM_INCIDENTS):

    correlation = cid()
    driver = random.choice(drivers)
    vehicle = random.choice(vehicles)
    merchant = random.choice(merchants)
    event = random.choice(events)
    error = random.choice(errors)

    steps = min(random.randint(*STEPS_RANGE), MAX_LOGS_PER_CID)

    for j in range(steps):

        method = random.choice(methods)
        time = ts(i, j)

        is_error = (j == steps - 1)

        # ---------------- APP LOG ----------------
        app_logs.append({
            "Timestamp": time,
            "Module": "FleetApp",
            "Level": "ERROR" if is_error else "INFO",
            "Event": event,
            "Details":
                f"CID={correlation} | Driver={driver} | Vehicle={vehicle} | "
                f"Merchant={merchant} | Step={j}/{steps} | Method={method} | "
                f"{stack_trace(error) if is_error else 'Transaction in progress'}"
        })

        # ---------------- ANALYTICS LOG ----------------
        analytics_logs.append({
            "Timestamp": time,
            "Module": "Analytics",
            "Level": "ERROR" if is_error else "INFO",
            "Event": event,
            "User/Card": driver,
            "Details":
                f"CID={correlation} | Vehicle={vehicle} | "
                f"Event={event} | Status={'FAILED' if is_error else 'OK'}"
        })

        # ---------------- DB LOG ----------------
        db_logs.append({
            "Timestamp": time,
            "SQL Operation": random.choice(["SELECT", "UPDATE", "INSERT"]),
            "Status": "ERROR" if is_error else "SUCCESS",
            "Details":
                f"CID={correlation} | DB Operation | Method={method} | "
                f"{error if is_error else 'OK'}"
        })

# -----------------------------
# SAVE
# -----------------------------
pd.DataFrame(app_logs).to_excel("EnhancedApplicationLog.xlsx", index=False)
pd.DataFrame(analytics_logs).to_excel("EnhancedLogAnalytics.xlsx", index=False)
pd.DataFrame(db_logs).to_excel("EnhancedDBLog.xlsx", index=False)

print("🚀FINAL FLEET LOG GENERATION COMPLETE")
print("App logs:", len(app_logs))
print("Analytics logs:", len(analytics_logs))
print("DB logs:", len(db_logs))