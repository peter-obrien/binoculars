import configparser
filename = 'properties.ini'
defaultValues = {'bot_token': '','server_id': '', 'pokemon_src_channel_id':'', 'pokemon_dest_channel_id':'', 'zones':''}
config = configparser.ConfigParser()
config.read(filename)

for key in defaultValues.keys():
    if key not in config['DEFAULT']:
        config['DEFAULT'][key] = defaultValues[key]

with open(filename, 'w') as configFile:
    config.write(configFile)
