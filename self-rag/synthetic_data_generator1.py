import pandas as pd
import random
from datetime import datetime, timedelta
import os
import uuid

# =========================================================
# CONFIG
# =========================================================

project_folder = os.path.join(
    os.path.dirname(__file__),
    "documents"
)

NUM_RECORDS = 500

# =========================================================
# USERS
# =========================================================

users = [
    {
        "UserId": f"driver{i:03}",
        "Email": f"driver{i:03}@shellfleet.com"
    }
    for i in range(1, 1001)
]

# =========================================================
# CARDS
# =========================================================

cards = [
    f"CARD-{10000+i}"
    for i in range(1, 3001)
]

# =========================================================
# METHODS
# =========================================================

method_map = {

    "User": [

        "UserController.UpdateProfile",
        "UserController.CreateUser",
        "UserController.DeleteUser",

        "AuthController.Login",
        "AuthController.Logout",
        "AuthController.ResetPassword",

        "UserRepository.InsertUser",
        "UserRepository.UpdateProfile"
    ],

    "Card": [

        "CardController.ProcessTransaction",
        "CardController.BlockCard",
        "CardController.ValidateCard",
        "CardController.IssueCard",

        "CardRepository.InsertTransaction",
        "CardRepository.GetCardDetails",
        "CardRepository.BlockCard"
    ],

    "API": [

        "Gateway.ProcessRequest",
        "Gateway.ValidateToken",
        "Gateway.Dispatch"
    ]
}

# =========================================================
# EVENTS
# =========================================================

events = [

    "Profile Updated",
    "Profile Update Failed",

    "User Created",
    "User Creation Failed",

    "Transaction Success",
    "Transaction Failed",

    "Card Issued",
    "Card Blocked",
    "Card Validation Failed",

    "Login Success",
    "Login Failed",

    "Password Reset Failed",

    "Session Timeout",

    "DB Insert Failed",
    "DB Deadlock",
    "Duplicate Key Violation",

    "API Authentication Failed"
]

# =========================================================
# SQL QUERIES
# =========================================================

sql_templates = [

    "INSERT INTO users (id,email) VALUES ('{user_id}','{email}')",

    "UPDATE users SET email='{email}' WHERE id='{user_id}'",

    "INSERT INTO transactions (card_id,liters) VALUES ('{card}',{liters})",

    "UPDATE cards SET status='BLOCKED' WHERE card_id='{card}'",

    "SELECT * FROM cards WHERE card_id='{card}'",

    "UPDATE transactions SET amount={amount} WHERE card_id='{card}'"
]

# =========================================================
# DETAILED STACK TRACES
# =========================================================

stack_traces = {

    "Profile Update Failed":
        """
System.NullReferenceException: Object reference not set to an instance of an object
   at ShellFleetHub.UserController.UpdateProfile(User user)
   at ShellFleetHub.Services.UserService.Save(User user)
   at ShellFleetHub.Services.ValidationService.ValidateProfile(User user)
   at ShellFleetHub.API.UserEndpoint.Process()
Inner Exception:
System.ArgumentNullException: user object was null
        """,

    "User Creation Failed":
        """
System.Data.SqlClient.SqlException: Violation of UNIQUE KEY constraint 'UQ_USER_EMAIL'
Cannot insert duplicate key in object 'dbo.Users'
   at ShellFleetHub.DB.Command.ExecuteNonQuery()
   at ShellFleetHub.UserRepository.InsertUser(User user)
   at ShellFleetHub.Services.UserService.Create(User user)
   at ShellFleetHub.API.UserEndpoint.Process()
        """,

    "Transaction Failed":
        """
ShellFleetHub.Exceptions.TransactionDeclinedException: Balance too low
   at ShellFleetHub.CardController.ProcessTransaction(Transaction txn)
   at ShellFleetHub.Services.CardService.Execute(Transaction txn)
   at ShellFleetHub.Services.FuelService.Authorize()
Inner Exception:
System.InvalidOperationException: Transaction state invalid
        """,

    "Card Blocked":
        """
ShellFleetHub.Exceptions.CardBlockedException: Fraud detection triggered
   at ShellFleetHub.CardController.BlockCard(Card card)
   at ShellFleetHub.Services.CardService.Block(Card card)
   at ShellFleetHub.Services.FraudService.Analyze(Card card)
Inner Exception:
ShellFleetHub.Security.FraudRuleException: Velocity limit exceeded
        """,

    "Card Validation Failed":
        """
System.InvalidOperationException: Card inactive
   at ShellFleetHub.CardController.ValidateCard(Card card)
   at ShellFleetHub.Services.CardService.Validate(Card card)
Inner Exception:
System.Exception: Expired fleet card
        """,

    "Login Failed":
        """
ShellFleetHub.Exceptions.InvalidCredentialException: Invalid username/password
   at ShellFleetHub.AuthController.Login(User user)
   at ShellFleetHub.Services.AuthService.Authenticate(user)
   at ShellFleetHub.Security.TokenService.Generate()
Inner Exception:
System.Security.SecurityException: Password hash mismatch
        """,

    "Password Reset Failed":
        """
ShellFleetHub.Exceptions.TokenExpiredException: Reset token expired
   at ShellFleetHub.AuthController.ResetPassword(token)
   at ShellFleetHub.Services.AuthService.Reset(user)
Inner Exception:
System.TimeoutException: Redis cache timeout
        """,

    "Session Timeout":
        """
System.TimeoutException: Request timed out
   at ShellFleetHub.API.Gateway.ProcessRequest()
   at ShellFleetHub.API.Gateway.Dispatch()
Inner Exception:
System.Net.Http.HttpRequestException: Upstream API timeout
        """,

    "DB Insert Failed":
        """
System.Data.SqlClient.SqlException: INSERT statement conflicted with FOREIGN KEY constraint
   at ShellFleetHub.DB.Connection.Execute()
   at ShellFleetHub.CardRepository.InsertTransaction(Transaction txn)
   at ShellFleetHub.DB.Command.ExecuteNonQuery()
        """,

    "DB Deadlock":
        """
System.Data.SqlClient.SqlException: Transaction deadlock detected
   at ShellFleetHub.DB.Connection.BeginTransaction()
   at ShellFleetHub.DB.Connection.Execute()
Inner Exception:
System.TimeoutException: Lock wait timeout exceeded
        """,

    "Duplicate Key Violation":
        """
System.Data.SqlClient.SqlException: Duplicate key value violates unique constraint
   at ShellFleetHub.UserRepository.InsertUser(User user)
   at ShellFleetHub.DB.Command.ExecuteNonQuery()
        """,

    "API Authentication Failed":
        """
System.Security.Authentication.AuthenticationException: Invalid authentication token
   at ShellFleetHub.API.Gateway.ValidateToken()
   at ShellFleetHub.API.Gateway.ProcessRequest()
Inner Exception:
System.Security.SecurityException: JWT signature invalid
        """
}

# =========================================================
# CID
# =========================================================

def generate_cid():

    return f"REQ-{uuid.uuid4().hex[:8].upper()}"

# =========================================================
# OUTPUT ARRAYS
# =========================================================

app_logs = []
analytics_logs = []
db_logs = []

# =========================================================
# GENERATION
# =========================================================

for _ in range(NUM_RECORDS):

    cid = generate_cid()

    user = random.choice(users)

    user_id = user["UserId"]
    email = user["Email"]

    card = random.choice(cards)

    event = random.choice(events)

    timestamp = datetime.now() + timedelta(
        seconds=random.randint(1, 300)
    )

    # -----------------------------------------------------
    # MODULE
    # -----------------------------------------------------

    if any(
        x in event
        for x in [
            "Profile",
            "User",
            "Login",
            "Password"
        ]
    ):
        module = "User"

    elif any(
        x in event
        for x in [
            "Card",
            "Transaction"
        ]
    ):
        module = "Card"

    else:
        module = "API"

    method = random.choice(
        method_map.get(module, [])
    )

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    is_error = any(
        x in event
        for x in [
            "Failed",
            "Blocked",
            "Timeout",
            "Violation",
            "Deadlock"
        ]
    )

    # -----------------------------------------------------
    # STACK TRACE
    # -----------------------------------------------------

    stack_trace = stack_traces.get(
        event,
        """
System.Exception: Unknown enterprise exception
   at ShellFleetHub.Core.Execute()
        """
    )

    # -----------------------------------------------------
    # SQL
    # -----------------------------------------------------

    sql = random.choice(sql_templates).format(
        user_id=user_id,
        email=email,
        card=card,
        liters=random.randint(5, 90),
        amount=random.randint(1000, 9000)
    )

    # =====================================================
    # APPLICATION LOG
    # =====================================================

    app_details = (
        f"Issue | "
        f"CorrelationId={cid} | "
        f"UserId={user_id} | "
        f"Email={email} | "
        f"CardId={card} | "
        f"Method={method} | "
        f"Event={event}"
    )

    if is_error:

        app_details += (
            f" | {stack_trace}"
        )

    app_logs.append({

        "Timestamp": timestamp,

        "Module": module,

        "Level": (
            "ERROR"
            if is_error
            else "INFO"
        ),

        "Event": event,

        "CorrelationId": cid,

        "UserId": user_id,

        "Email": email,

        "CardId": card,

        "Details": app_details
    })

    # =====================================================
    # ANALYTICS LOG
    # =====================================================

    analytics_details = (
        f"AnalyticsEvent | "
        f"CorrelationId={cid} | "
        f"UserId={user_id} | "
        f"Email={email} | "
        f"CardId={card} | "
        f"Event={event} | "
        f"Status={'FAILED' if is_error else 'SUCCESS'}"
    )

    if is_error:

        analytics_details += (
            f" | FailurePoint={method}"
        )

    analytics_logs.append({

        "Timestamp": timestamp,

        "Module": "Analytics",

        "Level": (
            "ERROR"
            if is_error
            else "INFO"
        ),

        "Event": event,

        "CorrelationId": cid,

        "UserId": user_id,

        "Email": email,

        "CardId": card,

        "Details": analytics_details
    })

    # =====================================================
    # DB LOG
    # =====================================================

    db_details = (
        f"{event} | "
        f"CorrelationId={cid} | "
        f"UserId={user_id} | "
        f"Email={email} | "
        f"CardId={card} | "
        f"Method={method} | "
        f"SQL={sql}"
    )

    if is_error:

        db_details += (
            f" | {stack_trace}"
        )

    db_logs.append({

        "Timestamp": timestamp,

        "SQL Operation": sql,

        "Status": (
            "ERROR"
            if is_error
            else "SUCCESS"
        ),

        "CorrelationId": cid,

        "UserId": user_id,

        "Email": email,

        "CardId": card,

        "Details": db_details
    })

# =========================================================
# SAVE
# =========================================================

os.makedirs(
    project_folder,
    exist_ok=True
)

pd.DataFrame(app_logs).to_excel(
    os.path.join(
        project_folder,
        "EnhancedApplicationLog.xlsx"
    ),
    index=False
)

pd.DataFrame(analytics_logs).to_excel(
    os.path.join(
        project_folder,
        "EnhancedLogAnalytics.xlsx"
    ),
    index=False
)

pd.DataFrame(db_logs).to_excel(
    os.path.join(
        project_folder,
        "EnhancedDBLog.xlsx"
    ),
    index=False
)

print(
    "✅ Enterprise-grade logs generated successfully"
)