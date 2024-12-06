import pyrebase
from django.shortcuts import render
import firebase_admin 
from firebase_admin import credentials, db
from firebase_admin import auth
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import os
from django.conf import settings

config = {
    "apiKey": "AIzaSyDyvnnQlWsTlO4Qfdj6EqBbHhcC-LNBLu4",
    "authDomain": "final-project-8018a.firebaseapp.com",
    "databaseURL": "https://final-project-8018a-default-rtdb.firebaseio.com",
    "projectId": "final-project-8018a",
    "storageBucket": "final-project-8018a.appspot.com",
    "messagingSenderId": "951767625787",
    "appId": "1:951767625787:web:ba80c0ad4ac3310e60ac1e"
}
firebase = pyrebase.initialize_app(config)
authentication = firebase.auth()
database = firebase.database()
storage = firebase.storage()

cred = credentials.Certificate("C:/Users/User/OneDrive/Documents/Final_Year_Project/final-project-8018a-firebase-adminsdk-7lrpf-6036b2a3c5.json")
firebase_admin.initialize_app(cred, { 'databaseURL': 'https://final-project-8018a-default-rtdb.firebaseio.com' })

def login(email, password):
    try:
        user = authentication.sign_in_with_email_and_password(email, password)
        # Check if the 'user' object is valid
        if 'idToken' in user:
            return user
        else:
            return None
    except Exception as e:
        print(f"Login failed: {e}")
        return None 
    
def register(email, password):
    try:
        user = authentication.create_user_with_email_and_password(email, password)
        return user
    except Exception as e:
        print(f"Registration error: {e}")
        return None
    
def forgot_password(email):
    try:
        authentication.send_password_reset_email(email)
        return True 
    except Exception as e:
        return False 

def guest_home():
    return "Welcome to the guest home!" 

def user_home(request):
    return render(request, 'user_home.html')

def get_user_profile(user_id):
    print(f"Attempting to retrieve profile for user ID: {user_id}")
    try:
        # Replace this with your actual Firebase call
        user_data = database.child("users").child(user_id).get().val()
        if user_data:
            print(f"Retrieved user data for {user_id}: {user_data}") 
            return user_data
        else:
            print(f"No user data found for {user_id}") 
            return None
    except Exception as e:
        print(f"Error retrieving profile: {e}")
        return None  

def update_user_profile(user_id, name, email, phone):
    try:
        user_ref = db.reference(f'users/{user_id}')
        updates = {}
        
        if name:
            updates['name'] = name
        if email:
            updates['email'] = email
        if phone:
            updates['phone'] = phone

        if updates:
            user_ref.update(updates)
            print(f"User profile updated in Realtime Database for {user_id}")

        # Update in Firebase Authentication
        if email: 
            # Correct usage of the auth.update_user method 
            auth.update_user( uid=user_id, email=email ) 
            print(f"User profile updated in Firebase Authentication for {user_id} with email: {email}")

        updated_user_data = get_user_profile(user_id)
        return updated_user_data
    
    except Exception as e:
        print(f"Error updating profile for user {user_id}: {e}")
        return None
    
def delete_user_account(user_id):
    try:
        # Delete user from Realtime Database
        user_ref = db.reference(f'users/{user_id}')
        user_ref.delete()
        
        # Delete user from Firebase Authentication
        auth.delete_user(user_id)
        print(f"User account {user_id} deleted.")
        return True
    except Exception as e:
        print(f"Error deleting account for user {user_id}: {e}")
        return False    
    
# Function to load and preprocess data
def load_and_preprocess_data():
    file_path = settings.DATASET_PATH
    print(f"Attempting to load file from path: {file_path}")
    
    # Check if the file exists
    if not os.path.isfile(file_path):
        print(f"Error: The file {file_path} does not exist.")
        return pd.DataFrame()  
    
    try:
        df = pd.read_csv(file_path, encoding='utf-16', delimiter=',')
        print(f"CSV file loaded successfully with shape: {df.shape}")
    except Exception as e:
        print(f"Error reading the CSV file: {e}")
        return pd.DataFrame()
    
    # Check if the DataFrame is empty
    if df.empty:
        print("Error: The DataFrame is empty.")
        return pd.DataFrame() 
    
    # Check if required columns exist
    required_columns = ['Title', 'Caption', 'Image']
    for column in required_columns:
        if column not in df.columns:
            print(f"Error: Missing column '{column}' in the DataFrame. Columns present: {df.columns.tolist()}")
            return pd.DataFrame()  # Return an empty DataFrame if any required column is missing
    
    df['text'] = df['Title'] + ' ' + df['Caption']
    print(f"DataFrame after adding 'text' column: {df.head()}")
    return df[['Title', 'Caption', 'Image', 'text']]


# K-means clustering function
def kmeans_clustering(df, num_clusters=5):
    if df.empty:
        print("Error: DataFrame is empty. Cannot perform clustering.")
        return df
    
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(df['text'])
    
    kmeans = KMeans(n_clusters=num_clusters, random_state=0)
    df['Cluster'] = kmeans.fit_predict(X)
    
    return df

# Function to get content based on K-means cluster
def clustered_content(cluster_id):
    df = load_and_preprocess_data()
    if df.empty:
        return [] 
    df = kmeans_clustering(df)
    
    cluster_content = df[df['Cluster'] == cluster_id]
    return cluster_content.to_dict(orient='records')

# Function to get content based on content-based filtering
def filtering(df, search_query):
    if df.empty:
        print("Error: DataFrame is empty. Cannot perform filtering.")
        return []
     
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df['text'])
    query_tfidf = vectorizer.transform([search_query])
    cosine_similarities = cosine_similarity(query_tfidf, tfidf_matrix).flatten()
    
    similar_indices = cosine_similarities.argsort()[-5:][::-1]
    recommended_posts = df.iloc[similar_indices]
    
    return recommended_posts.to_dict(orient='records')

# Function to store search keyword in Firebase
def store_search_keyword(keyword):
    search_ref = database.child("search_keywords").child(keyword)
    if search_ref.get().val() is None:
        search_ref.set({'count': 1})
    else:
        search_ref.update({'count': pyrebase.database.ServerValue.increment(1)})

# Function to get popular keywords based on frequency
def popular_keywords():
    search_ref = db.reference('search_keywords')
    popular_keywords = search_ref.order_by_child('count').limit_to_last(5).get()
    
    if popular_keywords:
        sorted_keywords = sorted(popular_keywords.items(), key=lambda x: x[1]['count'], reverse=True)
        return [(keyword, data['count']) for keyword, data in sorted_keywords]
    return []

# Function to search posts from the dataset based on the query
def search_posts(keyword):
    df = load_and_preprocess_data()
    if df.empty:
        return []  
    
    matching_posts = df[df['Title'].str.contains(keyword, case=False, na=False) |
                        df['Caption'].str.contains(keyword, case=False, na=False)]
    return matching_posts.to_dict(orient='records')

# Function to get popular content from Firebase based on search keyword frequency
def get_popular_content():
    search_ref = db.reference('search_keywords')
    popular_keywords = search_ref.order_by_child('count').limit_to_last(5).get()
    
    if popular_keywords:
        sorted_keywords = sorted(popular_keywords.items(), key=lambda x: x[1]['count'], reverse=True)
      
        popular_posts = []
        for keyword, data in sorted_keywords:
            posts = search_posts(keyword) 
            popular_posts.extend(posts)
        return popular_posts
    return []

def random_posts():
    df = load_and_preprocess_data()
    if df.empty:
        return [] 
    random_posts = df.sample(frac=1)  
    return random_posts.to_dict(orient='records')

    







