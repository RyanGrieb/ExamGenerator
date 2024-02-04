import mysql.connector
from mysql.connector.connection import MySQLConnection, MySQLCursor
import sys
import os
import hashlib
import stripe
import time


class DBUser:
    def __init__(self, db_tuple):
        self.id = db_tuple[0]
        self.email = db_tuple[1]
        self.password = db_tuple[2]
        self.salt = bytes(db_tuple[3])
        self.card_connected = db_tuple[4]
        self.pages_processed = int(db_tuple[6])


class DBManager:
    def __init__(self, database="user", host="db", user="root", pass_file=None):
        password_file = open(pass_file, "r")
        self.connection: MySQLConnection = mysql.connector.connect(
            user=user,
            password=password_file.read(),
            host=host,  # name of the mysql service as set in the docker compose file
            database=database,
            auth_plugin="mysql_native_password",
        )
        password_file.close()
        self.cursor: MySQLCursor = self.connection.cursor(buffered=True)

    def run_query(self, query: str):
        self.cursor.execute(query)
        self.connection.commit()
        return self.cursor.fetchone()

    def get_user_subscription_id(self, user_id):
        query = "SELECT subscription_id FROM stripe_users WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        subscription_id = self.cursor.fetchone()
        return subscription_id[0] if subscription_id else None

    def assign_user_subscriptions(
        self, user_id: str, subscription_id: str, subscription_item_id: str
    ):
        query = "UPDATE stripe_users SET subscription_id = %s, subscription_item_id = %s WHERE user_id = %s"
        values = (subscription_id, subscription_item_id, user_id)
        self.cursor.execute(query, values)
        self.connection.commit()

    def add_pages_processed(self, email: str, amount: int):
        query = f"UPDATE users SET pages_processed = pages_processed + {amount} WHERE email='{email}'"
        self.cursor.execute(query)
        self.connection.commit()

        # Get user_id from email: SELECT stripe_user_id from users WHERE email='{email}'
        subscription_query = f"""
        SELECT subscription_item_id, subscription_id
        FROM stripe_users
        WHERE user_id = (
            SELECT stripe_user_id
            FROM users
            WHERE email = '{email}'
        )
        """
        self.cursor.execute(subscription_query)
        subscription_item_id: str = self.cursor.fetchone()[0]

        stripe.SubscriptionItem.create_usage_record(
            subscription_item_id,
            quantity=amount,
            timestamp=int(time.time()),
            action="increment",
        )

    def get_pages_processed(self, email) -> int:
        query = "SELECT pages_processed FROM users WHERE email = %s"
        self.cursor.execute(query, (email,))
        pages_processed: int = self.cursor.fetchone()[0]
        return pages_processed

    def add_user(self, email: str, password: str):
        try:
            # Check for existing users:
            existing_user_query = "SELECT COUNT(*) FROM users WHERE email= %s"
            self.cursor.execute(existing_user_query, (email,))
            count = self.cursor.fetchone()[0]
            print(email, file=sys.stderr)
            print(count, file=sys.stderr)
            if count > 0:
                return (1, "User already exists")

            # Generate a salt
            salt = os.urandom(16)
            # Hash the password with the salt
            hashed_password_bytes = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, 100000
            )

            query = "INSERT INTO users (email, password, salt, card_connected) VALUES (%s, %s, %s, false)"
            data = (email, hashed_password_bytes.hex(), salt)
            self.cursor.execute(query, data)
            self.connection.commit()

        except Exception as e:
            print("Error:", e, file=sys.stderr)
            return (1, str(e))
        return (0, "Success")

    def get_user(self, email: str, password: str | None = None):
        try:
            query = f"SELECT * FROM users WHERE email='{email}'"
            self.cursor.execute(query)
            user_db_tuple = self.cursor.fetchone()

            if user_db_tuple:
                db_user_obj = DBUser(user_db_tuple)

                # If we are not providing a password
                if not password:
                    return (db_user_obj, "Success")

                # Hash the entered password with the stored salt
                hash_password_entered_hex = hashlib.pbkdf2_hmac(
                    "sha256", password.encode("utf-8"), db_user_obj.salt, 100000
                ).hex()

                if db_user_obj.password == hash_password_entered_hex:
                    # Return the user data from SQL
                    return (db_user_obj, "Success")
                else:
                    return (None, "Invalid email or password")  # Password is incorrect
            else:
                return (None, "Invalid email or password")  # User doesn't exist
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            return (None, str(e))

    def set_card_connected(self, email, value):
        try:
            query = "UPDATE users SET card_connected = %s WHERE email = %s"
            data = (value, email)
            self.cursor.execute(query, data)
            self.connection.commit()
            return (0, "Success")
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            return (1, str(e))

    def get_stripe_user_id(self, email):
        # TODO: Use try
        query = f"SELECT stripe_user_id from users WHERE email='{email}'"
        self.cursor.execute(query)
        stripe_user_id = self.cursor.fetchone()
        print(stripe_user_id)

        if not stripe_user_id:
            return None

        return stripe_user_id[0]

    def add_stripe_customer(self, stripe_customer: stripe.Customer):
        # Extract relevant information from the Stripe customer object
        user_id = stripe_customer.id
        email = stripe_customer.email
        name = stripe_customer.name
        delinquent = stripe_customer.delinquent
        currency = stripe_customer.currency
        default_source = stripe_customer.default_source
        livemode = stripe_customer.livemode

        stripe_query = """
            INSERT INTO stripe_users (user_id, name, delinquent, currency, default_source, livemode)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (user_id, name, delinquent, currency, default_source, livemode)

        self.cursor.execute(stripe_query, values)

        users_query = f"""
            UPDATE users SET stripe_user_id = '{user_id}' WHERE email = '{email}'
        """

        self.cursor.execute(users_query)

        self.connection.commit()

    def close_connections(self):
        self.cursor.close()
        self.connection.close()


"""
@server.route("/dbtest")
def listBlog():
    global conn
    if not conn:
        conn = DBManager(password_file="/run/secrets/db-password")
        conn.populate_db()
    rec = conn.query_titles()

    response = ""
    for c in rec:
        response = response + "<div>   yeah we still got it:  " + c + "</div>"
    return response
"""


# In /:
# global conn
# if not conn:
#    conn = DBManager(password_file="/run/secrets/db-password")
#    conn.populate_db()
# rec = conn.query_titles()
