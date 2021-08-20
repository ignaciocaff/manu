#BD config
USER_DB = 'postgres'
PASS_DB = 'root'
URL_DB = 'localhost'
NAME_DB = 'challenge'

SQLALCHEMY_DATABASE_URI = f'postgresql://{USER_DB}:{PASS_DB}@{URL_DB}/{NAME_DB}'
SQLALCHEMY_TRACK_MODIFICATIONS = False