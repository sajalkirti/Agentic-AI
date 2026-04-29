import pandas as pd
import uuid
import random
from datetime import datetime
import os

project_folder = os.path.join(os.path.dirname(__file__), "documents")

app_df = pd.read_excel(os.path.join(project_folder, "ApplicationLog.xlsx"))
analytics_df = pd.read_excel(os.path.join(project_folder, "LogAnalytics.xlsx"))
db_df = pd.read_excel(os.path.join(project_folder, "DBLog.xlsx"))

# -----------------------------
# FIXED: ONE correlation = ONE request flow
# -----------------------------
def generate_correlation_id():
    return f"REQ-{uuid.uuid4().hex[:8].upper()}"

# -----------------------------
# Predefine real failure chains (IMPORTANT)
# -----------------------------
incident_flows = [
    {
        "event": "Profile Updated",
        "root_cause": "NullReferenceException",
        "db_error": "Cannot insert NULL into non-nullable column",
        "analytics_error": "Profile update anomaly detected",
        "method_chain": [
            "AuthController.Login",
            "UserController.UpdateProfile",
            "UserService.Save",
            "UserRepository.UpdateProfile"
        ]
    },
    {
        "event": "Transaction Failed",
        "root_cause": "Timeout",
        "db_error": "Execution timeout expired",
        "analytics_error": "Transaction delay spike detected",
        "method_chain": [
            "CardController.ProcessTransaction",
            "CardService.Execute",
            "CardRepository.InsertTransaction"
        ]
    },
    {
        "event": "Card Blocked",
        "root_cause": "Fraud detection trigger",
        "db_error": "Lock timeout",
        "analytics_error": "Fraud model triggered block event",
        "method_chain": [
            "CardController.BlockCard",
            "CardService.Block",
            "CardRepository.BlockCard"
        ]
    },
]

# -----------------------------
# LOG BUILDERS
# -----------------------------
def build_app_log(row, cid, flow):
    method = random.choice(flow["method_chain"])

    if row["Level"] == "ERROR":
        details = (
            f"{row['Details']} | CorrelationId={cid} | Method={method} | "
            f"{flow['root_cause']}"
        )
    else:
        details = f"{row['Details']} | CorrelationId={cid} | Method={method}"

    return {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Module": row["Module"],
        "Level": row["Level"],
        "Event": row["Event"],
        "Details": details
    }

def build_analytics_log(row, cid, flow):
    method = random.choice(flow["method_chain"])

    details = (
        f"{row['Details']} | CorrelationId={cid} | Method={method} | "
        f"{flow['analytics_error'] if row['Level']=='ERROR' else 'OK'}"
    )

    return {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Module": row["Module"],
        "Level": row["Level"],
        "Event": row["Event"],
        "User/Card": row["User/Card"],
        "Details": details
    }

def build_db_log(row, cid, flow):
    method = random.choice(flow["method_chain"])

    details = (
        f"{row['Details']} | CorrelationId={cid} | Method={method} | "
        f"SQL={row['SQL Operation']} | "
        f"{flow['db_error'] if row['Status']=='ERROR' else 'OK'}"
    )

    return {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "SQL Operation": row["SQL Operation"],
        "Status": row["Status"],
        "Details": details
    }

# -----------------------------
# GENERATE INCIDENT-BASED LOGS
# -----------------------------
enhanced_app_logs = []
enhanced_analytics_logs = []
enhanced_db_logs = []

for flow in incident_flows:
    cid = generate_correlation_id()

    # pick random rows but KEEP SAME CID (IMPORTANT FIX)
    app_row = app_df.sample(1).iloc[0]
    analytics_row = analytics_df.sample(1).iloc[0]
    db_row = db_df.sample(1).iloc[0]

    enhanced_app_logs.append(build_app_log(app_row, cid, flow))
    enhanced_analytics_logs.append(build_analytics_log(analytics_row, cid, flow))
    enhanced_db_logs.append(build_db_log(db_row, cid, flow))

# -----------------------------
# SAVE OUTPUT
# -----------------------------
pd.DataFrame(enhanced_app_logs).to_excel("EnhancedApplicationLog.xlsx", index=False)
pd.DataFrame(enhanced_analytics_logs).to_excel("EnhancedLogAnalytics.xlsx", index=False)
pd.DataFrame(enhanced_db_logs).to_excel("EnhancedDBLog.xlsx", index=False)

print("SRE-grade correlated logs generated successfully!")