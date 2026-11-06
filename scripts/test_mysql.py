import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="Chinuvish@1204"
)
print("Connected! MySQL version:", conn.get_server_info())
conn.close()