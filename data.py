import os

from dotenv import load_dotenv

from api import Api

load_dotenv()

token = os.getenv("TELEGRAM_TOKEN")
storage_name = os.getenv("STORAGE_NAME", "users.db")
admin_id = os.getenv("ADMIN_IDS").split(",")

tracks = ('mobile', 'quality', 'database', 'design',
          'frontend', 'leading', 'iot', 'data_science',
          'start_up', 'vr', 'gamedev', 'devops', 'java', 'master')

links = (
    {'text': 'ВКонтакте', 'url': os.getenv('LINK_VK')},
    {'text': 'Instagram', 'url': os.getenv('LINK_INSTAGRAM')},
    {'text': 'Facebook', 'url': os.getenv('LINK_FACEBOOK')},
    {'text': 'Сайт', 'url': os.getenv('LINK_SITE')}
)

api = Api(os.getenv("API_URL"))
