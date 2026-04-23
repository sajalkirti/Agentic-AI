import pandas as pd
import uuid
import random
from datetime import datetime
import os
# Load all three Excel files
project_folder = os.path.join(os.path.dirname(__file__), "documents")
app_df = pd.read_excel(os.path.join(project_folder, "ApplicationLog.xlsx"))
analytics_df = pd.read_excel(os.path.join(project_folder, "LogAnalytics.xlsx"))
db_df = pd.read_excel(os.path.join(project_folder, "DBLog.xlsx"))

# Method mappings
method_map = {
    "User": ["UserController.UpdateProfile", "AuthController.ResetPassword", "AuthController.Login", "AuthController.Logout"],
    "Card": ["CardController.ProcessTransaction", "CardController.IssueCard", "CardController.BlockCard"],
    "DB": ["UserRepository.UpdateProfile", "CardRepository.InsertTransaction", "CardRepository.BlockCard"]
}

# Example stack traces
stack_traces = {
    "Profile Updated": "System.NullReferenceException: Object reference not set\n   at ShellFleetHub.UserController.UpdateProfile(User user)\n   at ShellFleetHub.Services.UserService.Save(User user)",
    "Profile Update Failed": "ShellFleetHub.Exceptions.ValidationException: Invalid input\n   at ShellFleetHub.UserController.UpdateProfile(User user)\n   at ShellFleetHub.Services.UserService.Save(User user)",
    "Password Reset Failed": "ShellFleetHub.Exceptions.InvalidTokenException: Token expired\n   at ShellFleetHub.AuthController.ResetPassword(String token)\n   at ShellFleetHub.Services.AuthService.Reset(User user)",
    "Transaction Failed": "ShellFleetHub.Exceptions.TransactionDeclinedException: Balance below threshold\n   at ShellFleetHub.CardController.ProcessTransaction(Transaction txn)\n   at ShellFleetHub.Services.CardService.Execute(Transaction txn)",
    "Card Issued": "ShellFleetHub.Exceptions.CardDuplicateException: Card ID already exists\n   at ShellFleetHub.CardController.IssueCard(Card card)\n   at ShellFleetHub.Services.CardService.Create(Card card)",
    "Card Blocked": "ShellFleetHub.Exceptions.CardBlockedException: Fraud detection triggered\n   at ShellFleetHub.CardController.BlockCard(Card card)\n   at ShellFleetHub.Services.CardService.Block(Card card)",
    "Login Success": "ShellFleetHub.AuthController.Login(User user)\n   at ShellFleetHub.Services.AuthService.Authenticate(User user)",
    "Logout Success": "ShellFleetHub.AuthController.Logout(User user)\n   at ShellFleetHub.Services.AuthService.Terminate(User user)",
    "Invalid token": "System.Data.SqlClient.SqlException: Invalid authentication token\n   at ShellFleetHub.DB.TokenValidator.Validate()\n   at ShellFleetHub.UserRepository.Save(User user)",
    "Timeout": "System.Data.SqlClient.SqlException: Execution timeout expired\n   at ShellFleetHub.DB.Connection.Execute()\n   at ShellFleetHub.CardRepository.InsertTransaction(Transaction txn)",
    "Duplicate key": "System.Data.SqlClient.SqlException: Violation of UNIQUE KEY constraint\n   at ShellFleetHub.DB.Command.ExecuteNonQuery()\n   at ShellFleetHub.UserRepository.Insert(User user)",
    "Constraint violation": "System.Data.SqlClient.SqlException: Cannot insert NULL into non-nullable column\n   at ShellFleetHub.DB.Command.ExecuteNonQuery()\n   at ShellFleetHub.UserRepository.UpdateProfile(User user)"
}

# Generate correlation IDs
def generate_correlation_id():
    return f"REQ-{uuid.uuid4().hex[:8].upper()}"

# Enhance ApplicationLog
enhanced_app_logs = []
for _, row in app_df.iterrows():
    correlation_id = generate_correlation_id()
    method = random.choice(method_map.get(row["Module"], ["UnknownMethod"]))
    details = row["Details"]

    if row["Level"] == "ERROR":
        error_msg = stack_traces.get(row["Event"], "No stack trace available")
        details = f"{row['Details']} | CorrelationId={correlation_id} | Method={method} | {error_msg}"
    else:
        details = f"{row['Details']} | CorrelationId={correlation_id} | Method={method}"

    enhanced_app_logs.append({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Module": row["Module"],
        "Level": row["Level"],
        "Event": row["Event"],
        "Details": details
    })

pd.DataFrame(enhanced_app_logs).to_excel("EnhancedApplicationLog.xlsx", index=False)

# Enhance LogAnalytics
enhanced_analytics_logs = []
for _, row in analytics_df.iterrows():
    correlation_id = generate_correlation_id()
    method = random.choice(method_map.get(row["Module"], ["UnknownMethod"]))
    details = row["Extra Details"]

    if row["Level"] == "ERROR":
        error_msg = stack_traces.get(row["Event"], "No stack trace available")
        details = f"{row['Extra Details']} | CorrelationId={correlation_id} | Method={method} | {error_msg}"
    else:
        details = f"{row['Extra Details']} | CorrelationId={correlation_id} | Method={method}"

    enhanced_analytics_logs.append({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Module": row["Module"],
        "Level": row["Level"],
        "Event": row["Event"],
        "User/Card": row["User/Card"],
        "Details": details
    })

pd.DataFrame(enhanced_analytics_logs).to_excel("EnhancedLogAnalytics.xlsx", index=False)

# Enhance DBLog
enhanced_db_logs = []
for _, row in db_df.iterrows():
    correlation_id = generate_correlation_id()
    method = random.choice(method_map.get("DB", ["UnknownMethod"]))
    details = row["Details"]

    if row["Status"] == "ERROR":
        error_msg = stack_traces.get(row["Details"], "No stack trace available")
        details = f"{row['Details']} | CorrelationId={correlation_id} | Method={method} | SQL={row['SQL Operation']} | {error_msg}"
    else:
        details = f"{row['Details']} | CorrelationId={correlation_id} | Method={method} | SQL={row['SQL Operation']}"

    enhanced_db_logs.append({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "SQL Operation": row["SQL Operation"],
        "Status": row["Status"],
        "Details": details
    })

pd.DataFrame(enhanced_db_logs).to_excel("EnhancedDBLog.xlsx", index=False)

print("EnhancedApplicationLog.xlsx, EnhancedLogAnalytics.xlsx, and EnhancedDBLog.xlsx generated successfully!")