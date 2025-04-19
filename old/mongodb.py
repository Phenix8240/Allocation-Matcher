import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

class MongoDBConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance.init_connection()
        return cls._instance
    
    def init_connection(self):
        try:
            username = os.getenv("MONGO_USERNAME")
            password = os.getenv("MONGO_PASSWORD")
            cluster_url = os.getenv("MONGO_CLUSTER_URL")
            db_name = os.getenv("MONGO_DB_NAME")
            
            self.uri = f"mongodb+srv://{username}:{password}@{cluster_url}/{db_name}?retryWrites=true&w=majority"
            
            self.client = MongoClient(
                self.uri,
                server_api=ServerApi('1'),
                maxPoolSize=50,
                connectTimeoutMS=5000
            )
            
            # Test the connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            print("Successfully connected to MongoDB!")
            
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise
    
    def get_db(self):
        return self.db
    
    def get_collection(self, collection_name):
        return self.db[collection_name]
    
    def close_connection(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

# Singleton instance
mongo_connection = MongoDBConnection()