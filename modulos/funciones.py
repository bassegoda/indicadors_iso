import pandas as pd
import mysql.connector
import json
import os


# Creo la variable 'config' (datos de acceso a Datanex), que será usada por las siguientes funciones:
current_dir = os.path.dirname(os.path.abspath(__file__))  ## Directorio actual.
json_file_path = os.path.join(current_dir, '..', 'otros', 'path.json')  ## Ruta al archivo path.json.
with open(json_file_path, 'r') as path:
    path = json.load(path)["path"]
with open(path, 'r') as my_file:
    my_file = json.load(my_file)
config = {
    'user': my_file["user"],
    'password': my_file["password"],
    'host': my_file["host"],
    'database': my_file["database"],
    'raise_on_warnings': True
}


# Funciones:

def fun_con(consulta):
    """
    La función se conecta a la base de datos, realiza la consulta 'consulta', se desconecta de la base de datos y devuelve un dataframe con la respuesta.
    """
    # Conexión:
    cnx = mysql.connector.connect(**config)
    
    # Consulta, crea dataframe:
    mycursor = cnx.cursor()
    mycursor.execute(consulta)
    res = mycursor.fetchall()
    field_names = [i[0] for i in mycursor.description]
    df = pd.DataFrame(res, columns=field_names)
    
    # Desconexión:
    cnx.close()
    
    # Devuelve el dataframe:
    return df