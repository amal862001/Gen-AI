import streamlit as st
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from langchain_groq import ChatGroq
import requests
import random
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()



# Helper Functions
def store_user_data_in_db(user_inputs):
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),       # Replace with your MySQL host
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),           # Replace with your MySQL username
            password=os.getenv('DB_PASSWORD')    # Replace with your MySQL password
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Insert Basic Information
            basic_info = user_inputs['basic_info']
            cursor.execute("""
                INSERT INTO BasicInfo (age, gender, weight, height, activity_level)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                basic_info['age'],
                basic_info['gender'],
                basic_info['weight'],
                basic_info['height'],
                basic_info['activity_level']
            ))
            user_id = cursor.lastrowid  # Get the auto-generated user_id

            # Insert Health Goals
            health_goals = user_inputs['health_goals']
            cursor.execute("""
                INSERT INTO HealthGoals (user_id, main_goal, specific_goals)
                VALUES (%s, %s, %s)
            """, (
                user_id,
                health_goals['main_goal'],
                health_goals['specific_goals']
            ))

            # Insert Dietary Preferences
            dietary_preferences = user_inputs['dietary_preferences']
            preferences = dietary_preferences['preferences']
            cursor.execute("""
                INSERT INTO DietaryPreferences (user_id, preferences, allergies, cultural_preferences)
                VALUES (%s, %s, %s, %s)
            """, (
                user_id,
                json.dumps(preferences) if preferences else '[]',  # Handle empty preferences
                dietary_preferences['allergies'],
                dietary_preferences['cultural_preferences']
            ))

            # Commit the transaction
            connection.commit()
            print("User data successfully stored in the database!")

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def calculate_tdee(age, gender, weight, height, activity_level):
    if gender == 'male':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

    activity_factors = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    tdee = bmr * activity_factors[activity_level]
    return tdee  

def calculate_bmr(age, gender, weight, height):
    if gender == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender == 'female':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    return round(bmr, 2)        


def calculate_tdee(bmr, activity_level):
    activity_factors = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    tdee = bmr * activity_factors[activity_level]
    return round(tdee, 2)


def adjust_calories_for_goal(tdee, health_goal):
    if health_goal == 'weight_loss':
        adjusted_calories = tdee - 500  # Example: 500 calorie deficit
    elif health_goal == 'maintenance':
        adjusted_calories = tdee
    elif health_goal == 'weight_gain':
        adjusted_calories = tdee + 250  # Example: 250 calorie surplus
    return round(adjusted_calories, 2)


def calculate_macronutrients(calories, protein_ratio=0.25, carb_ratio=0.50, fat_ratio=0.25):
    protein_calories = calories * protein_ratio
    carb_calories = calories * carb_ratio
    fat_calories = calories * fat_ratio

    protein_grams = protein_calories / 4
    carb_grams = carb_calories / 4
    fat_grams = fat_calories / 9

    return {
        'protein_grams': round(protein_grams, 2),
        'carb_grams': round(carb_grams, 2),
        'fat_grams': round(fat_grams, 2)
    }


def filter_recipes(recipes, dietary_preferences, allergies, cultural_preferences):
    """
    Filters recipes based on dietary preferences, allergies, and cultural preferences.
    
    Args:
        recipes (list): List of recipe dictionaries.
        dietary_preferences (list): List of dietary preferences (e.g., ['vegetarian', 'vegan']).
        allergies (str): Comma-separated string of allergies (e.g., 'dairy,nuts').
        cultural_preferences (str): Cultural preference (e.g., 'halal', 'kosher').
    
    Returns:
        list: Filtered list of recipes.
    """
    # Define dietary preference mappings
    dietary_mappings = {
        "vegetarian": ["vegetarian", "lacto ovo vegetarian", "vegan"],
        "vegan": ["vegan"],
        "gluten free": ["gluten free"],
        "dairy free": ["dairy free"]
    }
    
    allergen_keywords = {
        "dairy": ["milk", "cheese", "butter", "yogurt", "cream"],
        "nuts": ["almond", "walnut", "cashew", "peanut", "pecan"],
        "shellfish": ["shrimp", "crab", "lobster", "clam", "scallop"],
        "soy": ["soy", "tofu", "tempeh", "miso"],
        "gluten": ["wheat", "barley", "rye", "bread", "pasta"]
    }
    
    filtered_recipes = []
    for recipe in recipes:
        # Check dietary preferences
        if dietary_preferences:
            recipe_dietary_tags = [tag.lower() for tag in recipe.get("dietary_tags", [])]
            match_found = False
            for pref in dietary_preferences:
                mapped_tags = dietary_mappings.get(pref.lower(), [])
                if any(tag in recipe_dietary_tags for tag in mapped_tags):
                    match_found = True
                    break
            
            if not match_found:
                continue
        
        # Check allergies
        if allergies:
            allergens = [allergen.strip().lower() for allergen in allergies.split(",")]
            recipe_ingredients = recipe.get("ingredients", "").lower()
            allergen_count = sum(1 for allergen in allergens if any(keyword in recipe_ingredients for keyword in allergen_keywords.get(allergen, [])))
            
            if allergen_count > len(allergens) / 2:
                continue
        
        # Check cultural preferences
        if cultural_preferences:
            recipe_cultural_tags = [tag.lower() for tag in recipe.get("cultural_tags", [])]
            if cultural_preferences.lower() not in recipe_cultural_tags:
                # Allow recipes without cultural tags as fallback
                if recipe_cultural_tags:
                    continue
        
        # If all checks pass, add the recipe to the filtered list
        filtered_recipes.append(recipe)
    
    return filtered_recipes



def fetch_recipes_from_spoonacular(dietary_preferences, allergies, cultural_preferences, max_calories):
    api_key = os.getenv('SPOONACULAR_API_KEY')  # Replace with your actual Spoonacular API key
    base_url = "https://api.spoonacular.com/recipes/complexSearch"
    
    query_params = {
        "apiKey": api_key,
        "diet": ",".join(dietary_preferences),
        "intolerances": allergies,
        "maxCalories": max_calories,
        "number": 100,  # Fetch more recipes for variety
        "addRecipeInformation": True,
        "instructionsRequired": True
    }
    
    if cultural_preferences:
        query_params["cuisine"] = cultural_preferences
    
    # Fetch recipes for specific meal types
    meal_types = ["breakfast", "main course", "side dish", "snack"]
    all_recipes = []
    
    for meal_type in meal_types:
        query_params["type"] = meal_type
        response = requests.get(base_url, params=query_params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Fetched {len(data.get('results', []))} recipes for {meal_type}.")
            for recipe in data.get("results", []):
                all_recipes.append({
                    "name": recipe.get("title"),
                    "ingredients": ", ".join([ingredient["name"] for ingredient in recipe.get("extendedIngredients", [])]),
                    "instructions": recipe.get("instructions"),
                    "calories": recipe.get("nutrition", {}).get("nutrients", [{}])[0].get("amount", 0),
                    "dietary_tags": recipe.get("diets", []),
                    "cultural_tags": recipe.get("cuisines", []),
                    "meal_type": recipe.get("dishTypes", []),  # Use Spoonacular's dishType metadata
                    "cuisine": recipe.get("cuisines", [])
                })
        else:
            print(f"Error fetching recipes for {meal_type}: {response.status_code}")
    
    return all_recipes


def categorize_recipes_by_meal_type(recipes):
    """
    Categorizes recipes into meal types (breakfast, lunch, dinner, snacks) using metadata.
    
    Args:
        recipes (list): List of recipe dictionaries.
    
    Returns:
        dict: Dictionary with meal types as keys and lists of recipes as values.
    """
    categorized_recipes = {
        "breakfast": [],
        "lunch": [],
        "dinner": [],
        "snacks": []
    }
    
    for recipe in recipes:
        meal_types = recipe.get("meal_type", [])
        
        if "breakfast" in meal_types:
            categorized_recipes["breakfast"].append(recipe)
        elif "snack" in meal_types or "appetizer" in meal_types:
            categorized_recipes["snacks"].append(recipe)
        elif "main course" in meal_types:
            categorized_recipes["lunch"].append(recipe)
            categorized_recipes["dinner"].append(recipe)
        else:
            # Default to lunch or dinner if no specific meal type is found
            categorized_recipes["lunch"].append(recipe)
            categorized_recipes["dinner"].append(recipe)
    
    return categorized_recipes



def calculate_meal_calories(adjusted_calories):
    """
    Calculates calorie targets for each meal type.
    
    Args:
        adjusted_calories (float): Total daily calories after adjustment.
    
    Returns:
        dict: Dictionary with meal types as keys and calorie targets as values.
    """
    meal_calories = {
        "breakfast": adjusted_calories * 0.25,
        "lunch": adjusted_calories * 0.35,
        "dinner": adjusted_calories * 0.35,
        "snacks": adjusted_calories * 0.05
    }
    return meal_calories




fallback_recipes = {
    "breakfast": [
        {"name": "Oatmeal with Berries", "calories": 300},
        {"name": "Avocado Toast", "calories": 250},
        {"name": "Smoothie Bowl", "calories": 350}
    ],
    "snacks": [
        {"name": "Apple Slices", "calories": 100},
        {"name": "Carrot Sticks with Hummus", "calories": 150},
        {"name": "Mixed Nuts", "calories": 200},
        {"name": "Greek Yogurt with Honey", "calories": 120},
        {"name": "Trail Mix", "calories": 180},
        {"name": "Dark Chocolate and Almonds", "calories": 200}
    ],
    "lunch": [
        {"name": "Vegetable Stir-Fry", "calories": 500},
        {"name": "Quinoa Salad", "calories": 500},
        {"name": "Chickpea Curry", "calories": 550}
    ],
    "dinner": [
        {"name": "Lentil Soup", "calories": 500},
        {"name": "Stuffed Bell Peppers", "calories": 550},
        {"name": "Veggie Burger", "calories": 600}
    ]
}

def generate_daily_meal_plan(categorized_recipes, meal_calories):
    daily_meal_plan = {}
    
    for meal_type, calorie_target in meal_calories.items():
        recipes = categorized_recipes[meal_type]
        
        if not recipes:
            # Use fallback option if no recipes are available
            fallback_options = fallback_recipes.get(meal_type, [{"name": "No recipe available", "calories": 0}])
            daily_meal_plan[meal_type] = random.choice(fallback_options)
            continue
        
        # Shuffle recipes to add variety
        random.shuffle(recipes)
        
        # Select a recipe within ±20% of the calorie target
        tolerance = calorie_target * 0.20
        lower_bound = calorie_target - tolerance
        upper_bound = calorie_target + tolerance
        
        selected_recipe = None
        for recipe in recipes:
            if lower_bound <= recipe["calories"] <= upper_bound:
                selected_recipe = recipe
                break
        
        if selected_recipe:
            daily_meal_plan[meal_type] = {
                "name": selected_recipe["name"],
                "calories": selected_recipe["calories"]
            }
        else:
            # Use fallback option if no recipe matches the calorie target
            fallback_options = fallback_recipes.get(meal_type, [{"name": "No suitable recipe found", "calories": 0}])
            daily_meal_plan[meal_type] = random.choice(fallback_options)
    
    return daily_meal_plan




import json
import os
import random
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq


import re

class RecipeInstructionGenerator:
    def __init__(self, cache_file="instruction_cache.json"):
        # Initialize the ChatGROQ LLM
        self.llm = ChatGroq(
            temperature=0.7,
            groq_api_key=os.getenv('GROQ_API_KEY'),
            model_name="deepseek-r1-distill-llama-70b"
        )
        
        # Cache to store generated instructions and ingredients
        self.cache_file = cache_file
        self.instruction_cache = self.load_cache()

    def load_cache(self):
        """
        Loads the instruction and ingredient cache from a JSON file.
        """
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_cache(self):
        """
        Saves the instruction and ingredient cache to a JSON file.
        """
        with open(self.cache_file, "w") as f:
            json.dump(self.instruction_cache, f, indent=4)

    def generate_ingredients(self, recipe_name):
        """
        Generates plausible ingredients for a recipe using the LLM.
        
        Args:
            recipe_name (str): Name of the recipe.

        Returns:
            str: Generated ingredients as a clean, comma-separated string.
        """
        # Check if ingredients are already cached
        cache_key = f"ingredients::{recipe_name}"
        if cache_key in self.instruction_cache:
            print(f"Using cached ingredients for '{recipe_name}'.")
            return self.instruction_cache[cache_key]
    
        # Define the prompt template with strict output format
        prompt_template = PromptTemplate.from_template(
            """
            ### RECIPE DETAILS:
            Recipe Name: {recipe_name}
    
            ### INSTRUCTION:
            Generate a STRICTLY comma-separated list of plausible ingredients for this recipe.
            - ONLY list the ingredients in a single line, separated by commas.
            - Do NOT include explanations, bullet points, or extra text.
            - Example: "flour, sugar, eggs, butter, vanilla extract"
            - If unsure, use common ingredients for the recipe type.
            ### INGREDIENTS:
            """
        )
    
        # Create the chain for ingredient generation
        chain = prompt_template | self.llm

        # Prepare the input for the prompt
        input_data = {"recipe_name": recipe_name}
        try:
            # Invoke the chain to generate the ingredients
            response = chain.invoke(input_data)
            raw_ingredients = response.content.strip()
        
            # Post-process the response to ensure a clean, comma-separated list
            ingredients = re.sub(r"\s+", " ", raw_ingredients)  # Remove extra whitespace
            ingredients = re.sub(r"[^a-zA-Z0-9,\s]", "", ingredients)  # Remove invalid characters
            ingredients = ",".join([item.strip() for item in ingredients.split(",") if item.strip()])
        
            # Validate the output to ensure it contains at least one ingredient
            if not ingredients:
                raise ValueError("Generated ingredients are empty or invalid.")
        
            # Cache the generated ingredients
            self.instruction_cache[cache_key] = ingredients
            self.save_cache()  # Save the updated cache to disk
            print(f"Cached ingredients for '{recipe_name}'.")
            return ingredients
        except Exception as e:
            # Handle errors gracefully and provide a fallback
            fallback_ingredients = "Ingredients not available"
            print(f"Error generating ingredients for '{recipe_name}': {e}. Using fallback.")
            self.instruction_cache[cache_key] = fallback_ingredients
            self.save_cache()
            return fallback_ingredients    


    def generate_instructions(self, recipe_name, ingredients=None):
        """
        Generates cooking instructions for a recipe using ChatGROQ.
        Uses caching to avoid redundant API calls.
        Handles cases where ingredients are not specified by generating placeholders.
        
        Args:
            recipe_name (str): Name of the recipe.
            ingredients (str, optional): Comma-separated list of ingredients. Defaults to None.
        
        Returns:
            str: Generated cooking instructions.
        """
        # Handle missing ingredients gracefully
        if not ingredients or ingredients.strip().lower() in ["ingredients not available", ""]:
            ingredients = self.generate_ingredients(recipe_name)

        # Check if instructions are already cached
        cache_key = f"{recipe_name}::{ingredients}"
        if cache_key in self.instruction_cache:
            print(f"Using cached instructions for '{recipe_name}'.")
            return self.instruction_cache[cache_key]

        # Define the prompt template for instruction generation
        prompt_template = PromptTemplate.from_template(
            """
            ### RECIPE DETAILS:
            Recipe Name: {recipe_name}
            Ingredients: {ingredients}
            
            ### INSTRUCTION:
            Generate step-by-step cooking instructions for this recipe.
            Be concise but clear, and ensure the instructions are easy to follow.
            Do not include a preamble or introduction.
            If ingredients are not specified, provide general instructions based on the recipe name.
            Ensure the output is concise and avoids unnecessary details.
            ### INSTRUCTIONS (NO PREAMBLE):
            """
        )

        # Create the chain for instruction generation
        chain = prompt_template | self.llm

        # Prepare the input for the prompt
        input_data = {
            "recipe_name": recipe_name,
            "ingredients": ingredients
        }

        # Invoke the chain to generate the instructions
        response = chain.invoke(input_data)
        instructions = response.content.strip()

        # Cache the generated instructions
        self.instruction_cache[cache_key] = instructions
        self.save_cache()  # Save the updated cache to disk
        print(f"Cached instructions for '{recipe_name}'.")
        return instructions


def generate_weekly_meal_plan(categorized_recipes, meal_calories):
    weekly_meal_plan = []
    used_recipes = set()  # Track recipes already used in the week
    
    # Initialize the instruction generator
    instruction_generator = RecipeInstructionGenerator()
    
    for _ in range(7):  # Generate a plan for 7 days
        daily_meal_plan = {}
        for meal_type, calorie_target in meal_calories.items():
            recipes = categorized_recipes.get(meal_type, [])
            
            if not recipes:
                fallback_options = fallback_recipes.get(meal_type, [{"name": "No recipe available", "calories": 0}])
                selected_recipe = random.choice(fallback_options)
            else:
                random.shuffle(recipes)
                tolerance = calorie_target * 0.20
                lower_bound = calorie_target - tolerance
                upper_bound = calorie_target + tolerance
                
                selected_recipe = None
                for recipe in recipes:
                    if lower_bound <= recipe["calories"] <= upper_bound and recipe["name"] not in used_recipes:
                        selected_recipe = recipe
                        break
                
                if not selected_recipe:
                    fallback_options = fallback_recipes.get(meal_type, [{"name": "No suitable recipe found", "calories": 0}])
                    selected_recipe = random.choice(fallback_options)
            
            # Ensure ingredients are not empty
            ingredients = selected_recipe.get("ingredients", "")
            if not ingredients or ingredients.strip().lower() in ["ingredients not available", ""]:
                ingredients = instruction_generator.generate_ingredients(selected_recipe["name"])
            
            # Ensure instructions are not empty
            if not selected_recipe.get("instructions"):
                generated_instructions = instruction_generator.generate_instructions(
                    recipe_name=selected_recipe["name"],
                    ingredients=ingredients
                )
                selected_recipe["instructions"] = generated_instructions
            
            daily_meal_plan[meal_type] = {
                "name": selected_recipe["name"],
                "calories": selected_recipe["calories"],
                "ingredients": ingredients,
                "instructions": selected_recipe.get("instructions", "Instructions not available")
            }
            used_recipes.add(selected_recipe["name"])
        
        weekly_meal_plan.append(daily_meal_plan)
    
    return weekly_meal_plan


def analyze_user_data(user_inputs):
    # Extract user data
    basic_info = user_inputs['basic_info']
    health_goals = user_inputs['health_goals']
    dietary_preferences = user_inputs['dietary_preferences']
    
    # Step 1: Calculate BMR, TDEE, adjusted calories, and macros
    bmr = calculate_bmr(age=basic_info['age'], gender=basic_info['gender'],
                        weight=basic_info['weight'], height=basic_info['height'])
    tdee = calculate_tdee(bmr, basic_info['activity_level'])
    adjusted_calories = adjust_calories_for_goal(tdee, health_goals['main_goal'])
    macros = calculate_macronutrients(adjusted_calories)
    
    # Step 2: Fetch recipes from Spoonacular
    recipes = fetch_recipes_from_spoonacular(
        dietary_preferences=dietary_preferences['preferences'],
        allergies=dietary_preferences['allergies'],
        cultural_preferences=dietary_preferences['cultural_preferences'],
        max_calories=adjusted_calories / 3
    )
    filtered_recipes = filter_recipes(
        recipes,
        dietary_preferences['preferences'],
        dietary_preferences['allergies'],
        dietary_preferences['cultural_preferences']
    )
    
    # Step 3: Categorize recipes by meal type
    categorized_recipes = categorize_recipes_by_meal_type(filtered_recipes)
    
    # Step 4: Calculate meal calories and generate weekly meal plan
    meal_calories = calculate_meal_calories(adjusted_calories)
    weekly_meal_plan = generate_weekly_meal_plan(categorized_recipes, meal_calories)
    
    # Return analysis results
    return {
        'bmr': bmr,
        'tdee': tdee,
        'adjusted_calories': adjusted_calories,
        'macros': macros,
        'weekly_meal_plan': weekly_meal_plan
    }



from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import textwrap

def extract_numbered_steps(instructions):
    """
    Extracts numbered steps from the instructions.
    """
    lines = instructions.split("\n")
    steps = [line.strip() for line in lines if line.strip().startswith(tuple(f"{i}." for i in range(1, 21)))]
    return steps

def clean_text(text):
    """
    Removes asterisks (*) from the given text.
    """
    return text.replace("*", "").strip()

def export_meal_plan_to_pdf(weekly_meal_plan, output_file="meal_plan.pdf"):
    """
    Exports the weekly meal plan to a PDF file with numbered steps in instructions.
    Ensures consistent font sizes, proper alignment, and removes asterisks from the text.
    """
    c = canvas.Canvas(output_file, pagesize=letter)
    width, height = letter
    margin = 50
    y_position = height - margin
    line_height = 15
    page_width = width - 2 * margin  # Usable width for text
    max_lines_per_page = (height - 2 * margin) // line_height  # Max lines per page

    # Define colors
    header_color = HexColor("#4CAF50")  # Green
    meal_name_color = HexColor("#FF9800")  # Orange

    # Define consistent font sizes
    header_font_size = 14
    meal_type_font_size = 12
    meal_name_font_size = 10
    instructions_font_size = 10

    def add_page():
        """
        Adds a new page to the PDF and resets the y_position.
        """
        nonlocal y_position
        c.showPage()
        y_position = height - margin

    def wrap_text(text, width):
        """
        Wraps text to fit within the specified width.
        Returns a list of wrapped lines.
        """
        return textwrap.wrap(text, width=70)

    for i, day in enumerate(weekly_meal_plan, start=1):
        if y_position - (line_height * 10) < margin:
            add_page()

        # Add day header with color and consistent font size
        c.setFillColor(header_color)
        c.setFont("Helvetica-Bold", header_font_size)
        c.drawString(margin, y_position, f"Day {i}:")
        c.setFillColorRGB(0, 0, 0)  # Reset to black
        y_position -= line_height + 10

        for meal_type, meal in day.items():
            if y_position - (line_height * 8) < margin:
                add_page()

            # Add meal type header with consistent font size
            c.setFont("Helvetica", meal_type_font_size)
            c.drawString(margin + 10, y_position, f"{meal_type.capitalize()}:")
            y_position -= line_height

            # Add meal name with color and consistent font size
            c.setFillColor(meal_name_color)
            c.setFont("Helvetica-Bold", meal_name_font_size)
            meal_name = clean_text(meal['name'])  # Clean meal name
            c.drawString(margin + 20, y_position, f"Name: {meal_name} ({meal['calories']} calories)")
            c.setFillColorRGB(0, 0, 0)  # Reset to black
            y_position -= line_height

            # Add ingredients with consistent font size
            ingredients = meal.get("ingredients", "Ingredients not available")
            if ingredients == "Ingredients not available":
                ingredients = "Ingredients: Not specified"
            ingredients = clean_text(ingredients)  # Clean ingredients
            c.setFont("Helvetica", instructions_font_size)
            wrapped_ingredients = wrap_text(ingredients, width=70)
            for line in wrapped_ingredients:
                c.drawString(margin + 20, y_position, line)
                y_position -= line_height
                if y_position < margin:
                    add_page()

            # Add instructions (only numbered steps) with consistent font size
            steps = extract_numbered_steps(meal['instructions'])
            c.setFont("Helvetica", instructions_font_size)
            c.drawString(margin + 20, y_position, "Instructions:")
            y_position -= line_height
            if steps:
                for step in steps:
                    cleaned_step = clean_text(step)  # Clean each step
                    wrapped_step = wrap_text(cleaned_step, width=70)
                    for line in wrapped_step:
                        if y_position - line_height < margin:
                            add_page()
                        c.drawString(margin + 30, y_position, line)
                        y_position -= line_height
            else:
                if y_position - line_height < margin:
                    add_page()
                c.drawString(margin + 30, y_position, "No numbered steps found.")
                y_position -= line_height

            y_position -= line_height  # Add space between meals

        y_position -= line_height * 2  # Add space between days

    c.save()
    print(f"Meal plan exported successfully to {output_file}")


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_meal_plan_via_email(recipient_email, pdf_file_name, sender_email, sender_password):
    """
    Sends the weekly meal plan as a PDF attachment via email.
    
    Args:
        recipient_email (str): Email address of the recipient.
        pdf_file_name (str): Name of the PDF file to attach.
        sender_email (str): Email address of the sender.
        sender_password (str): Password for the sender's email account.
    """
    try:
        # Create the email message
        subject = "Your Weekly Meal Plan"
        body = "Please find attached your weekly meal plan."
        
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Attach the PDF file
        with open(pdf_file_name, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={pdf_file_name}"
            )
            msg.attach(part)

        # Connect to the SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print(f"Meal plan sent to {recipient_email}.")
    except Exception as e:
        print(f"Error sending email: {e}")



def collect_user_inputs():
    st.title("Personalized Meal Planner")
    st.write("Please provide the following information to generate your meal plan.")

    # Basic Information
    st.header("Basic Information")
    age = st.number_input("Age", min_value=1, max_value=120)
    gender = st.selectbox("Gender", ["Male", "Female"])
    weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0)
    height = st.number_input("Height (cm)", min_value=1.0, max_value=300.0)

    activity_levels = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
        "Extra Active": 1.9
    }
    activity_level = st.selectbox("Activity Level", list(activity_levels.keys()))

    # Health Goals
    st.header("Health Goals")
    health_goals = ["Weight Loss", "Maintenance", "Weight Gain"]
    health_goal = st.selectbox("Main Health Goal", health_goals)
    specific_goals = st.text_input("Specific Goals (e.g., muscle_gain, improved_endurance)")

    # Dietary Preferences
    st.header("Dietary Preferences")
    dietary_options = ["Vegetarian", "Vegan", "Keto", "Paleo", "None"]
    dietary_preferences = st.multiselect("Dietary Preferences", dietary_options)
    allergies = st.text_input("Allergies or Intolerances (e.g., lactose_free, gluten_free)")
    cultural_preferences = st.text_input("Cultural Preferences (e.g., halal, kosher, indian,italian)")

    # Compile all user inputs into a dictionary
    user_inputs = {
        "basic_info": {
            "age": age,
            "gender": gender.lower(),
            "weight": weight,
            "height": height,
            "activity_level": activity_level.lower().replace(" ", "_")
        },
        "health_goals": {
            "main_goal": health_goal.lower().replace(" ", "_"),
            "specific_goals": specific_goals
        },
        "dietary_preferences": {
            "preferences": [p.lower() for p in dietary_preferences],
            "allergies": allergies,
            "cultural_preferences": cultural_preferences
        }
    }

    return user_inputs






import streamlit as st
from streamlit_extras.app_logo import add_logo  # Optional: For adding a logo

# Custom CSS for styling
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load custom CSS
local_css("styles.css")  # Create a `styles.css` file for custom styles

# Initialize session state
if "meal_plan_generated" not in st.session_state:
    st.session_state.meal_plan_generated = False

# Title and Logo
st.title("Meal Planner App 🍽️")
add_logo("logo.png")  # Replace with your logo file

# Sidebar for User Inputs
with st.sidebar:
    st.header("User Information")
    user_data = collect_user_inputs()

# Main Content
st.subheader("Generate Your Personalized Meal Plan")
if st.button("Generate Meal Plan 🍳", help="Click to generate your weekly meal plan"):
    try:
        # Save user data to MySQL database
        store_user_data_in_db(user_data)
        
        # Generate meal plan
        analysis_results = analyze_user_data(user_data)
        weekly_meal_plan = analysis_results['weekly_meal_plan']
        
        # Export to PDF
        pdf_filename = "meal_plan.pdf"
        export_meal_plan_to_pdf(weekly_meal_plan, output_file=pdf_filename)
        
        # Display success message
        st.success("Meal plan generated successfully! 🎉")
        st.session_state.meal_plan_generated = True
        
        # Display the meal plan
        st.subheader("Weekly Meal Plan 📅")
        for i, day in enumerate(weekly_meal_plan, start=1):
            with st.expander(f"**Day {i}**", expanded=False):
                for meal_type, meal in day.items():
                    st.write(f"- **{meal_type.capitalize()}:**")
                    st.write(f"  - Name: {meal['name']}")
                    st.write(f"  - Calories: {meal['calories']}")
                    st.write(f"  - Ingredients: {meal['ingredients']}")
                    st.write("  - Instructions:")
                    
                    # Extract and print numbered steps
                    steps = extract_numbered_steps(meal['instructions'])
                    if steps:
                        for step in steps:
                            st.write(f"    - {step}")
                    else:
                        st.write("      No numbered steps found in instructions.")
        
        # Option to download PDF
        with open(pdf_filename, "rb") as file:
            st.download_button(
                label="Download Meal Plan as PDF 📥",
                data=file,
                file_name=pdf_filename,
                mime="application/pdf",
                help="Click to download your meal plan as a PDF"
            )
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Email Section
if st.session_state.meal_plan_generated:
    st.subheader("Send Meal Plan via Email 📧")
    email = st.text_input("Enter your email to receive the meal plan:", help="We'll send the meal plan to this email address.")
    if st.button("Send via Email ✉️", help="Click to send the meal plan to your email"):
        if email:
            try:
                send_meal_plan_via_email(email, pdf_filename)
                st.success(f"Meal plan sent to {email}! ✅")
            except Exception as e:
                st.error(f"Failed to send email: {str(e)}")
        else:
            st.warning("Please enter a valid email address.")
else:
    st.info("Generate a meal plan first to access additional options.")

# Footer
st.markdown("""
---
**Meal Planner App** © 2023  
For support, contact us at support@mealplanner.com  
""")







