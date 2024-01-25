import mysql.connector
import sys
import os
import hashlib


class DBManager:
    def __init__(self, database="user", host="db", user="root", pass_file=None):
        password_file = open(pass_file, "r")
        self.connection = mysql.connector.connect(
            user=user,
            password=password_file.read(),
            host=host,  # name of the mysql service as set in the docker compose file
            database=database,
            auth_plugin="mysql_native_password",
        )
        password_file.close()
        self.cursor = self.connection.cursor()

    def add_user(self, email: str, password: str):
        try:
            # Check for existing users:
            existing_user_query = "SELECT COUNT(*) FROM users WHERE email= '%s'"
            self.cursor.execute(existing_user_query, email)
            count = self.cursor.fetchone()[0]
            if count > 0:
                return (1, "User already exists")

            # Generate a salt
            salt = os.urandom(16)
            # Hash the password with the salt
            hashed_password_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)

            query = "INSERT INTO users (email, password, salt) VALUES (%s, %s, %s)"
            data = (email, hashed_password_bytes.hex(), salt)
            self.cursor.execute(query, data)
            self.connection.commit()

        except Exception as e:
            print("Error:", e, file=sys.stderr)
            return (1, str(e))
        return (0, "Success")

    def check_user(self, email: str, password: str):
        try:
            query = f"SELECT password, salt FROM users WHERE email= '{email}'"
            self.cursor.execute(query)
            result = self.cursor.fetchone()

            if result:
                hashed_password_stored_hex, salt_raw = result
                salt = bytes(salt_raw)
                # Hash the entered password with the stored salt
                hash_password_entered_hex = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()

                if hashed_password_stored_hex == hash_password_entered_hex:
                    return (0, "Success")
                else:
                    return (1, "Invalid email or password")  # Password is incorrect
            else:
                return (1, "Invalid email or password")  # User doesn't exist
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            return (1, str(e))

    def populate_db(self):
        self.cursor.execute("DROP TABLE IF EXISTS blog")
        self.cursor.execute("CREATE TABLE blog (id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(255))")
        self.cursor.executemany(
            "INSERT INTO blog (id, title) VALUES (%s, %s);",
            [(i, "Blog post #%d" % i) for i in range(1, 5)],
        )
        self.connection.commit()

    def query_titles(self):
        self.cursor.execute("SELECT title FROM blog")
        rec = []
        for c in self.cursor:
            rec.append(c[0])
        return rec


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
