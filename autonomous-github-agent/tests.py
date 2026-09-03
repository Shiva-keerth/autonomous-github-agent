import os
from dotenv import load_dotenv
from github import Github,Auth

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
auth= Auth.Token(token)
g = Github(auth=auth)

user= g.get_user()
print("Connected as :",user.login)