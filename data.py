import os

from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_TOKEN")
storage_name = "users.json"
admin_id = os.getenv("ADMIN_IDS").split(",")

directions = ['mobile', 'quality', 'database', 'design',
              'frontend', 'leading', 'iot', 'data_science',
              'start_up', 'vr', 'gamedev', 'devops', 'java', 'master']
