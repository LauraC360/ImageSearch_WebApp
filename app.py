# from flask import Flask
#
# app = Flask(__name__)
#
# @app.route('/')
# def home():
#     return "Hello from Azure via GitHub!"


from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
import pyodbc
from azure.storage.blob import ContainerClient
import json
import requests

# Load environment variables from .env
load_dotenv()

# Flask app
app = Flask(__name__)

# Retrieve secrets from .env
sas_token = os.getenv("SAS_TOKEN")
container_name = os.getenv("CONTAINER_NAME")
account_name = "jackblack"  # Replace with your Azure Storage account name
connection_string = os.getenv("AZURE_SQL_CONNECTION_STRING")

# For search
search_service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
search_api_key = os.getenv("AZURE_SEARCH_API_KEY")
search_endpoint = f"https://{search_service_name}.search.windows.net/indexes/{search_index_name}/docs"

# Construct the base URL for the images
base_url = f"https://{account_name}.blob.core.windows.net/{container_name}"

@app.route('/')
def list_all_images():
    try:
        # Connect to the database
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Fetch image data from the database
        cursor.execute("SELECT * FROM images")
        rows = cursor.fetchall()

        # Construct image URLs and prepare data for rendering
        images = []
        for row in rows:
            # Parse labels from JSON string and format them
            labels_list = json.loads(row[2])  # Convert JSON string to list
            formatted_labels = ', '.join(labels_list)  # Join labels without quotes

            image_data = {
                "url": f"{base_url}/{row[1]}?{sas_token}",  # Construct the image URL
                "name": row[1],  # Image name
                "labels": formatted_labels,  # Formatted labels
                "safe_adult": row[3],  # Safe adult score
                "safe_racy": row[4],  # Safe racy score
                "safe_violence": row[5],  # Safe violence score
            }
            images.append(image_data)

        # Pass the image data to the template
        return render_template('images.html', images=images)

    except Exception as e:
        return f"Error: {e}"

    finally:
        # Close the database connection
        if 'connection' in locals() and connection:
            connection.close()


@app.route('/search', methods=['GET', 'POST'])
def search_images():
    if request.method == 'POST':
        query = request.form.get('query')  # Get the search query from the form

        # Azure Cognitive Search query
        headers = {
            "Content-Type": "application/json",
            "api-key": search_api_key
        }
        payload = {
            "search": query,
            "searchFields": "labels",  # Specify the fields to search
            "select": "name,labels,safe_adult,safe_racy,safe_violence",  # Fields to retrieve
        }
        response = requests.post(f"{search_endpoint}/search?api-version=2021-04-30-Preview", headers=headers, json=payload)

        if response.status_code == 200:
            results = response.json().get('value', [])
            images = []
            for result in results:
                labels_list = result['labels'] if isinstance(result['labels'], list) else json.loads(result['labels'])
                formatted_labels = ', '.join(labels_list)

                image_data = {
                    "url": f"{base_url}/{result['name']}?{sas_token}",
                    "name": result['name'],
                    "labels": formatted_labels,
                    "safe_adult": result['safe_adult'],
                    "safe_racy": result['safe_racy'],
                    "safe_violence": result['safe_violence'],
                }
                images.append(image_data)

            return render_template('search_results.html', images=images, query=query)
        else:
            return f"Error: {response.status_code} - {response.text}"

    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True)