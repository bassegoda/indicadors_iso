import asyncio
import httpx
import json
from dotenv import load_dotenv
import os
import time
load_dotenv()


METABASE_URL = os.environ.get("METABASE_URL", "https://metabase.clinic.cat") 
EMAIL = os.environ.get("METABASE_EMAIL")
PASSWORD = os.environ.get("METABASE_PASSWORD")
DATABASE_NAME = "datascope_gestor_dev"

query = """SELECT * FROM datascope_gestor_dev.rc
            limit 2
        ;"""



async def authenticate (): 
    async with httpx.AsyncClient() as client: 
        
        resp = await client.post(
            f"{METABASE_URL}/api/session",
            json={"username": EMAIL, "password": PASSWORD},
            timeout=60.0
        )
        
        if resp.status_code == 200:
            session_id = resp.json()["id"]
            return  session_id

        
        else:
            raise Exception(f"Error al autenticar")

     
    
async def map_databases (session_id): 
    async with httpx.AsyncClient() as client:  
        resp_db = await client.get(
            f"{METABASE_URL}/api/database",
            headers={"X-Metabase-Session": session_id},
            timeout=30.0
        )
        
        if resp_db.status_code == 200:
            data = resp_db.json()
            map_db = {}
            for d in data["data"]:
                map_db[d["name"]] = d["id"]
            return map_db
        else:
            raise Exception(f"Error get databases")


def parse_metabase_response(response_json):
    """
    Convierte la respuesta de Metabase (/api/dataset) a una lista de diccionarios:
    [
        {"col1": val1, "col2": val2, ...},
        ...
    ]
    """
    data = response_json.get("data", {})
    cols = [c["name"] for c in data.get("cols", [])]
    rows = data.get("rows", [])

    result = [dict(zip(cols, row)) for row in rows]
    return result


async def query_databases (database_name, map_db, query, session_id, parse_result=False): 
    start = time.time()
    query_dict = {
        "database": map_db[database_name],  # ID de la base de datos
        "type": "native",
        "native": {
            "query":  query
        },
        "cache_ttl": 0  
    }
    # print(review_query(query, database_name))
    
    async with httpx.AsyncClient() as client:  #  solo si tu SSL falla
        resp_query = await client.post(
            f"{METABASE_URL}/api/dataset",
            headers={"X-Metabase-Session": session_id},
            json=query_dict,
            timeout=120.0
        )
        # print(resp_query.status_code)
        if (resp_query.status_code == 200 | resp_query.status_code == 202):
            raw_data = resp_query.json()
            end = time.time()
            if parse_result:
                data = parse_metabase_response(raw_data)
            else:
                data = raw_data.get("data", {}).get("rows", [])
            total_time = round(end - start, 3)
            print(f'{database_name} \t len:{len(data)} \t time:{total_time}')
            return data, total_time
            

        
        else:
            print(json.dumps(json.loads(resp_query.text), indent=2, ensure_ascii=False))
            raise Exception(f"Error query request")


async def main() -> None:
    log = []

    # 1. Autenticarse
    session_id = await authenticate()
    
    # 2. Listar bases de datos
    map_db = await map_databases (session_id)
    
    # 3. Quey  
    try:
        results, t_time = await query_databases (
            database_name = DATABASE_NAME, 
            map_db = map_db, 
            query = query, 
            session_id = session_id,
            parse_result=True
            )
        print(results)
    except:
        print("timeout")
            
   
        

if __name__ == '__main__':
    asyncio.run(main())

# # Iniciar sesión
# auth = requests.post(
#     f"{METABASE_URL}/api/session",
#     json={"username": EMAIL, "password": PASSWORD}
# )

# session_id = auth.json()['id']
# print("Session ID:", session_id)