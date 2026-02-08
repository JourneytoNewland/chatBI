
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recall.graph.neo4j_client import Neo4jClient
from src.config.settings import settings

def check_neo4j():
    print(f"🔌 Connecting to Neo4j at {settings.neo4j.uri}...")
    client = Neo4jClient(
        uri=settings.neo4j.uri,
        user=settings.neo4j.user,
        password=settings.neo4j.password
    )
    
    try:
        driver = client.connect()
        print("✅ Connection successful!")
        
        # Run a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            record = result.single()
            print(f"   Query result: {record['num']}")
            
        client.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    if not check_neo4j():
        sys.exit(1)
