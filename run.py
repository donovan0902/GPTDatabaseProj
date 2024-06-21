import sqlite3
import json
from openai import OpenAI

def get_schema():
    # Establish a connection to the database
    conn = sqlite3.connect('SampleCors.db')
    cursor = conn.cursor()

    # Extract table and column information
    schema = {}
    # Query the sqlite_master table for schema information
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Iterate over the tables and print out their schema
    for table in tables:
        table_name = table[0]

        # Extract column information
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Store the column information in the schema dictionary
        schema[table_name] = {"columns": {}}
        for column in columns:
            column_name = column[1]
            column_type = column[2]
            schema[table_name]["columns"][column_name] = column_type

        # Fetch primary key
        for column in columns:
                if column[5]:  # column[5] is 1 if it's a primary key
                    schema[table_name]["primary_key"] = column[1]
                    break

        # Fetch foreign key
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        fkeys = cursor.fetchall()

        if fkeys:
            schema[table_name]["foreign_keys"] = {}
            for fkey in fkeys:
                schema[table_name]["foreign_keys"][fkey[3]] = {
                    "references": f"{fkey[2]}({fkey[4]})",
                }

    # Close the connection
    conn.close()

    # Write the schema to a JSON file
    with open('schema.json', 'w') as f:
        json.dump(schema, f, indent=4)

    return schema

# put together user input and schema to create a prompt
# create_prompt reads schema.json and request from the user
def create_prompt(schema, request):
    # Load the schema from the JSON file
    with open('schema.json', 'r') as f:
        schema = json.load(f)

    # Create the prompt
    prompt = "Database Schema:\n\n"
    for table_name, table_info in schema.items():
        prompt += f"Table: {table_name}\n"
        prompt += "Columns: "
        for column_name, column_type in table_info["columns"].items():
            prompt += f"{column_name} ({column_type}), "
        prompt = prompt[:-2] + "\n"
        if "primary_key" in table_info:
            prompt += f"Primary Key: {table_info['primary_key']}\n"
        if "foreign_keys" in table_info:
            for column_name, fkey_info in table_info["foreign_keys"].items():
                prompt += f"Foreign Key: {column_name} REFERENCES {fkey_info['references']}\n"
        prompt += "\n"
    prompt += f"Request: {request}\n"
    prompt += "SQL Query:\n"
    
    return prompt

# get the sql query from the user
def get_query(prompt):
    client = OpenAI()
    messages = [{"role": "user", "content": prompt}]       
    response = client.chat.completions.create(   
        model="gpt-3.5-turbo",                                         
        messages=messages,
        max_tokens=1024
    )

    # Extract the SQL query from the response
    response = response.choices[0].message.content

    # Remove the prompt from the result
    # pattern = r'```sql\n(.*?)\n```'
    # match = re.search(pattern, response, re.DOTALL)
    #print(response)
   
    return response

# execute the query and return the result
def execute_query(query):
    # Establish a connection to the database
    conn = sqlite3.connect('SampleCors.db')
    cursor = conn.cursor()

    # Execute the query
    cursor.execute(query)
    result = cursor.fetchall()

    # Close the connection
    conn.close()

    return result

# main function
def main():
    # Get the schema
    schema = get_schema()

    # Get the user's request
    request = input("What would you like to do?\n")

    # Create the prompt
    prompt = create_prompt(schema, request)

    # Get the SQL query
    query = get_query(prompt)

    # print(query)

    # Execute the query
    result = execute_query(query)

    client = OpenAI()
    
    rephrase = "given the result of a query, and the original prompt for the query, please provide a summary of the data."
    messages = [{"role": "user", "content": rephrase + "\n" + str(result) + "\n" + request}]       
    response = client.chat.completions.create(   
        model="gpt-3.5-turbo",                                         
        messages=messages,
        max_tokens=1024
    )

    # Print the result
    print(response.choices[0].message.content)

if __name__ == "__main__":
    main()
