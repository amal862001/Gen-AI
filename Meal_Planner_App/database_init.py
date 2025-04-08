import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def initialize_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME')}")
            cursor.execute(f"USE {os.getenv('DB_NAME')}")
            
            # Create BasicInfo table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS BasicInfo (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    age INT NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    weight FLOAT NOT NULL,
                    height FLOAT NOT NULL,
                    activity_level VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create HealthGoals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS HealthGoals (
                    goal_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    main_goal VARCHAR(100) NOT NULL,
                    specific_goals TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES BasicInfo(user_id)
                )
            """)
            
            # Create DietaryPreferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DietaryPreferences (
                    preference_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    preferences JSON,
                    allergies TEXT,
                    cultural_preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES BasicInfo(user_id)
                )
            """)
            
            # Create MealPlan table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MealPlan (
                    plan_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    day_of_week INT NOT NULL,
                    meal_type VARCHAR(50) NOT NULL,
                    recipe_name VARCHAR(255) NOT NULL,
                    calories FLOAT NOT NULL,
                    ingredients TEXT,
                    instructions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES BasicInfo(user_id)
                )
            """)
            
            connection.commit()
            print("Database and tables created successfully!")
            
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    initialize_database()