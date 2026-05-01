import os, psycopg
from dotenv import load_dotenv

#load environment variables from .env file
load_dotenv()
# connects to postgres
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        # Creates the vector extension if needed
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Runs a simple pgvector query
        cur.execute("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector")
        print("pgvector distance:", cur.fetchone()[0])