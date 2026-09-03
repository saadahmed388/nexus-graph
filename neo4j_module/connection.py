from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jConnection:
    def __init__(self):
        self.user = os.getenv("NEO4J_LOCAL_USER")
        self.password = os.getenv("NEO4J_LOCAL_PASS")
        self.key = os.getenv("NEO4J_LOCAL_URI")

        try:
            self.driver = GraphDatabase.driver(
                uri = self.key,
                auth = (self.user, self.password)
            )
        except Exception as e:
            print(f"Error: {e}")

        try:
            self.driver.verify_connectivity()
            print("Neo4j connection successful!")

            with self.driver.session() as session:
                result = session.run("""
                    RETURN
                        "Connected" AS status,
                        datetime() AS server_time
                """)
                print(result.single())

        except Exception as e:
            print("Neo4j connection failed:", e)
            

    def get_driver(self):
        return self.driver

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        with self.driver.session() as session:
            return session.execute_write(
                self._execute_query,
                query,
                parameters or {}
            )
        
    @staticmethod
    def _execute_query(tx, query, parameters):
        result = tx.run(query, parameters)
        return list(result)
