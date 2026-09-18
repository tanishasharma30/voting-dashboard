from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os


# ============================================================
# VOTEX - SECURE DIGITAL VOTING SYSTEM
# ============================================================

app = Flask(__name__)

app.secret_key = "votex_demo_secret_key_2026"


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "votex.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_db()

    cursor = conn.cursor()


    # ========================================================
    # VOTERS TABLE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voters (

            voter_id TEXT PRIMARY KEY,

            name TEXT NOT NULL,

            has_voted INTEGER DEFAULT 0

        )
    """)


    # ========================================================
    # VOTES TABLE
    #
    # timestamp is required by the existing database.
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            voter_id TEXT NOT NULL,

            group_name TEXT NOT NULL,

            timestamp TIMESTAMP NOT NULL

        )
    """)


    # ========================================================
    # DEMO VOTER
    #
    # Used only because fingerprint hardware is not
    # connected yet.
    #
    # Later:
    #
    # ESP32
    #    ↓
    # R307
    #    ↓
    # Fingerprint extraction
    #    ↓
    # CNN liveness detection
    #    ↓
    # Fingerprint matching
    #
    # ========================================================

    cursor.execute("""
        INSERT OR IGNORE INTO voters
        (
            voter_id,
            name,
            has_voted
        )
        VALUES (?, ?, ?)
    """, (
        "DEMO001",
        "Demo Voter",
        0
    ))


    conn.commit()

    conn.close()


# ============================================================
# PAGE 1
# HOME
# ============================================================

@app.route("/")
@app.route("/page1")
@app.route("/page1.html")
def page1():

    return render_template(
        "page1.html"
    )


# ============================================================
# PAGE 2
# FINGERPRINT VERIFICATION
# ============================================================

@app.route("/page2")
@app.route("/page2.html")
@app.route("/verify")
def page2():

    return render_template(
        "page2.html"
    )


# ============================================================
# DEMO FINGERPRINT VERIFICATION
# ============================================================
#
# This is temporary demo logic.
#
# It simulates a successful fingerprint verification.
#
# Later this route can receive the actual result from:
#
# ESP32 → R307 → CNN liveness detection
#
# ============================================================

@app.route(
    "/demo_verify",
    methods=["POST"]
)
def demo_verify():

    # --------------------------------------------------------
    # DEMO VOTER
    # --------------------------------------------------------

    voter_id = "DEMO001"


    # --------------------------------------------------------
    # DATABASE CONNECTION
    # --------------------------------------------------------

    conn = get_db()

    cursor = conn.cursor()


    # --------------------------------------------------------
    # FIND VOTER
    # --------------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM voters
        WHERE voter_id = ?
    """, (
        voter_id,
    ))

    voter = cursor.fetchone()

    conn.close()


    # --------------------------------------------------------
    # VOTER NOT REGISTERED
    # --------------------------------------------------------

    if voter is None:

        return jsonify({
            "success": False,
            "message": "Fingerprint is not registered."
        }), 403


    # --------------------------------------------------------
    # CHECK WHETHER VOTER ALREADY VOTED
    # --------------------------------------------------------

    if voter["has_voted"] == 1:

        return jsonify({
            "success": False,
            "message": "You have already voted."
        }), 403


    # --------------------------------------------------------
    # CREATE VERIFIED VOTER SESSION
    # --------------------------------------------------------

    session["voter_id"] = voter["voter_id"]

    session["voter_name"] = voter["name"]

    session["fingerprint_verified"] = True


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return jsonify({
        "success": True,
        "message": "Fingerprint verified successfully."
    })


# ============================================================
# PAGE 3
# VOTING PAGE
# ============================================================

@app.route("/page3")
@app.route("/page3.html")
@app.route("/vote")
def page3():

    # --------------------------------------------------------
    # CHECK FINGERPRINT VERIFICATION
    # --------------------------------------------------------

    if not session.get(
        "fingerprint_verified"
    ):

        return redirect(
            url_for("page2")
        )


    # --------------------------------------------------------
    # GET VERIFIED VOTER
    # --------------------------------------------------------

    voter_id = session.get(
        "voter_id"
    )


    if not voter_id:

        return redirect(
            url_for("page2")
        )


    # --------------------------------------------------------
    # CHECK VOTER IN DATABASE
    # --------------------------------------------------------

    conn = get_db()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT *
        FROM voters
        WHERE voter_id = ?
    """, (
        voter_id,
    ))

    voter = cursor.fetchone()

    conn.close()


    # --------------------------------------------------------
    # VOTER NOT FOUND
    # --------------------------------------------------------

    if voter is None:

        session.clear()

        return redirect(
            url_for("page2")
        )


    # --------------------------------------------------------
    # PREVENT RE-VOTING
    # --------------------------------------------------------

    if voter["has_voted"] == 1:

        session.clear()

        return redirect(
            url_for("page2")
        )


    # --------------------------------------------------------
    # SHOW PAGE 3
    # --------------------------------------------------------

    return render_template(
        "page3.html",
        voter_name=voter["name"]
    )


# ============================================================
# SUBMIT VOTE
# ============================================================

@app.route(
    "/submit_vote",
    methods=["POST"]
)
def submit_vote():

    # --------------------------------------------------------
    # CHECK VERIFIED SESSION
    # --------------------------------------------------------

    if not session.get(
        "fingerprint_verified"
    ):

        return jsonify({
            "success": False,
            "message": "Fingerprint verification required."
        }), 403


    # --------------------------------------------------------
    # GET VOTER ID FROM SERVER SESSION
    # --------------------------------------------------------

    voter_id = session.get(
        "voter_id"
    )


    if not voter_id:

        return jsonify({
            "success": False,
            "message": "Voter session not found."
        }), 403


    # --------------------------------------------------------
    # GET VOTE DATA
    # --------------------------------------------------------

    data = request.get_json()


    if not data:

        return jsonify({
            "success": False,
            "message": "No vote data received."
        }), 400


    group_name = data.get(
        "group"
    )


    # --------------------------------------------------------
    # ALLOWED GROUPS
    # --------------------------------------------------------

    allowed_groups = [
        "Group A",
        "Group B",
        "Group C",
        "Group D"
    ]


    if group_name not in allowed_groups:

        return jsonify({
            "success": False,
            "message": "Invalid group selected."
        }), 400


    # --------------------------------------------------------
    # DATABASE CONNECTION
    # --------------------------------------------------------

    conn = get_db()

    cursor = conn.cursor()


    try:

        # ====================================================
        # CHECK VOTER STATUS
        # ====================================================

        cursor.execute("""
            SELECT has_voted
            FROM voters
            WHERE voter_id = ?
        """, (
            voter_id,
        ))

        voter = cursor.fetchone()


        # ====================================================
        # VOTER DOES NOT EXIST
        # ====================================================

        if voter is None:

            conn.rollback()

            return jsonify({
                "success": False,
                "message": "Voter not found."
            }), 404


        # ====================================================
        # PREVENT DOUBLE VOTING
        # ====================================================

        if voter["has_voted"] == 1:

            conn.rollback()

            return jsonify({
                "success": False,
                "message": "You have already voted."
            }), 403


        # ====================================================
        # INSERT VOTE
        #
        # IMPORTANT:
        #
        # Your existing SQLite database has:
        #
        # timestamp NOT NULL
        #
        # Therefore CURRENT_TIMESTAMP is supplied here.
        # ====================================================

        cursor.execute("""
            INSERT INTO votes
            (
                voter_id,
                group_name,
                timestamp
            )
            VALUES
            (
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
        """, (
            voter_id,
            group_name
        ))


        # ====================================================
        # MARK VOTER AS HAVING VOTED
        # ====================================================

        cursor.execute("""
            UPDATE voters
            SET has_voted = 1
            WHERE voter_id = ?
        """, (
            voter_id,
        ))


        # ====================================================
        # SAVE BOTH OPERATIONS
        # ====================================================

        conn.commit()


        # ====================================================
        # MARK VOTE COMPLETION
        #
        # Page 4 can use this to confirm that the vote
        # was actually recorded.
        # ====================================================

        session["vote_completed"] = True


        # ====================================================
        # CLEAR VOTER INFORMATION
        # ====================================================

        session.pop(
            "voter_id",
            None
        )

        session.pop(
            "voter_name",
            None
        )

        session.pop(
            "fingerprint_verified",
            None
        )


        # ====================================================
        # SUCCESS
        # ====================================================

        return jsonify({
            "success": True,
            "message": "Vote cast successfully."
        })


    except Exception as e:

        # ----------------------------------------------------
        # ROLLBACK IF ANYTHING FAILS
        # ----------------------------------------------------

        conn.rollback()


        print(
            "Vote submission error:",
            e
        )


        return jsonify({
            "success": False,
            "message": "Unable to record vote."
        }), 500


    finally:

        conn.close()


# ============================================================
# PAGE 4
# SUCCESS
# ============================================================

@app.route("/page4")
@app.route("/page4.html")
@app.route("/success")
def page4():

    # --------------------------------------------------------
    # PAGE 4 SHOULD ONLY BE SHOWN AFTER A SUCCESSFUL VOTE
    # --------------------------------------------------------

    if not session.get(
        "vote_completed"
    ):

        return redirect(
            url_for("page1")
        )


    # --------------------------------------------------------
    # SHOW SUCCESS PAGE
    # --------------------------------------------------------

    return render_template(
        "page4.html"
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    # --------------------------------------------------------
    # LOGIN FORM
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )


        # ----------------------------------------------------
        # DEMO ADMIN CREDENTIALS
        # ----------------------------------------------------

        if (
            username == "admin"
            and
            password == "admin123"
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )


        # ----------------------------------------------------
        # INVALID LOGIN
        # ----------------------------------------------------

        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )


    # --------------------------------------------------------
    # SHOW LOGIN PAGE
    # --------------------------------------------------------

    return render_template(
        "admin_login.html"
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    # --------------------------------------------------------
    # ADMIN-ONLY ACCESS
    # --------------------------------------------------------

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_db()

    cursor = conn.cursor()


    # ========================================================
    # TOTAL VOTES
    # ========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM votes
    """)

    total_votes = cursor.fetchone()["total"]


    # ========================================================
    # GROUP A
    # ========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM votes
        WHERE group_name = ?
    """, (
        "Group A",
    ))

    group_a = cursor.fetchone()["total"]


    # ========================================================
    # GROUP B
    # ========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM votes
        WHERE group_name = ?
    """, (
        "Group B",
    ))

    group_b = cursor.fetchone()["total"]


    # ========================================================
    # GROUP C
    # ========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM votes
        WHERE group_name = ?
    """, (
        "Group C",
    ))

    group_c = cursor.fetchone()["total"]


    # ========================================================
    # GROUP D
    # ========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM votes
        WHERE group_name = ?
    """, (
        "Group D",
    ))

    group_d = cursor.fetchone()["total"]


    conn.close()


    # ========================================================
    # CALCULATE VOTE SHARE
    # ========================================================

    if total_votes > 0:

        group_a_percentage = round(
            (group_a / total_votes) * 100,
            1
        )

        group_b_percentage = round(
            (group_b / total_votes) * 100,
            1
        )

        group_c_percentage = round(
            (group_c / total_votes) * 100,
            1
        )

        group_d_percentage = round(
            (group_d / total_votes) * 100,
            1
        )

    else:

        group_a_percentage = 0

        group_b_percentage = 0

        group_c_percentage = 0

        group_d_percentage = 0


    # ========================================================
    # SEND DATA TO DASHBOARD
    # ========================================================

    return render_template(

        "admin_dashboard.html",

        total_votes=total_votes,

        group_a=group_a,

        group_b=group_b,

        group_c=group_c,

        group_d=group_d,

        group_a_percentage=group_a_percentage,

        group_b_percentage=group_b_percentage,

        group_c_percentage=group_c_percentage,

        group_d_percentage=group_d_percentage
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# ============================================================
# ADMIN RESULTS API
# ============================================================

@app.route("/admin/api/results")
def admin_results():

    # --------------------------------------------------------
    # ADMIN ACCESS CHECK
    # --------------------------------------------------------

    if not session.get(
        "admin_logged_in"
    ):

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 403


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_db()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            group_name,
            COUNT(*) AS total
        FROM votes
        GROUP BY group_name
    """)

    rows = cursor.fetchall()

    conn.close()


    # --------------------------------------------------------
    # DEFAULT GROUP COUNTS
    # --------------------------------------------------------

    results = {

        "Group A": 0,

        "Group B": 0,

        "Group C": 0,

        "Group D": 0
    }


    # --------------------------------------------------------
    # FILL COUNTS
    # --------------------------------------------------------

    for row in rows:

        if row["group_name"] in results:

            results[
                row["group_name"]
            ] = row["total"]


    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total = sum(
        results.values()
    )


    # --------------------------------------------------------
    # PERCENTAGES
    # --------------------------------------------------------

    percentages = {}


    for group, count in results.items():

        if total > 0:

            percentages[group] = round(
                (count / total) * 100,
                1
            )

        else:

            percentages[group] = 0


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return jsonify({

        "success": True,

        "total_votes": total,

        "groups": results,

        "percentages": percentages
    })


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # INITIALIZE DATABASE
    # --------------------------------------------------------

    init_db()


    # --------------------------------------------------------
    # SERVER INFORMATION
    # --------------------------------------------------------

    print()

    print(
        "============================================"
    )

    print(
        "   VoteX Secure Digital Voting System"
    )

    print(
        "============================================"
    )

    print(
        "Server : http://127.0.0.1:5001"
    )

    print(
        "Page 1 : http://127.0.0.1:5001/page1"
    )

    print(
        "Page 2 : http://127.0.0.1:5001/page2"
    )

    print(
        "Page 3 : http://127.0.0.1:5001/page3"
    )

    print(
        "Page 4 : http://127.0.0.1:5001/page4"
    )

    print(
        "Admin  : http://127.0.0.1:5001/admin"
    )

    print(
        "============================================"
    )

    print()


    # --------------------------------------------------------
    # START FLASK SERVER
    # --------------------------------------------------------

    app.run(

        host="127.0.0.1",

        port=5001,

        debug=True,

        use_reloader=False
    )