from werkzeug.security import generate_password_hash

# Replace 'your_password_here' with your desired admin password
password = input("Enter the password you want to hash: ")

# Generate the hash
hashed_password = generate_password_hash(password)

print("\nGenerated password hash:")
print(hashed_password)
print("\nCopy this hash and replace it in your mysql.sql file")
