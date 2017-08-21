import configparser
filename = 'properties.ini'
defaultValues = {'bot_token': '','server_id': '', 'pokemon_src_channel_id':'', 'pokemon_dest_channel_id':'', 'zones':''}
databaseValues = {'ENGINE': 'django.db.backends.postgresql', 'NAME': '','USER': '', 'PASSWORD': ''}
securityValues = {'SECRET_KEY': ''}
config = configparser.ConfigParser()
config.read(filename)

for key in defaultValues.keys():
    if key not in config['DEFAULT']:
        config['DEFAULT'][key] = defaultValues[key]

for key in databaseValues.keys():
    if key not in config['DATABASES']:
        config['DATABASES'][key] = databaseValues[key]

for key in securityValues.keys():
    if key not in config['SECURITY']:
        config['SECURITY'][key] = securityValues[key]

with open(filename, 'w') as configFile:
    config.write(configFile)
