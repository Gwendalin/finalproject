from django.shortcuts import render
from .firebase import load_and_preprocess_data, store_search_keyword, clustered_content, filtering, random_posts, get_popular_content

# Recommendation view
def recommendation_view(request):
    popular_content = get_popular_content()
    print(f"Popular content: {popular_content}")

    if not popular_content:
        popular_content = random_posts()
        print("Fallback to random posts for popular content.")

    # Get the user's search query
    user_search_query = request.GET.get('search', '').strip()
    print(f"User search query: {user_search_query}")

    if user_search_query:
        # Store the search keyword for future recommendations
        store_search_keyword(user_search_query)

        # Content-based filtering based on search query
        df = load_and_preprocess_data()
        filtered_posts = filtering(df, user_search_query)
        print(f"Filtered posts: {filtered_posts}")

        # If no posts found, fallback to random posts
        if not filtered_posts:
            filtered_posts = random_posts()
            print("Fallback to random posts for filtered content.")

        # Optionally, cluster content based on user search
        cluster_id = request.GET.get('cluster', None)
        if cluster_id:
            filtered_posts = clustered_content(int(cluster_id))
            print(f"Clustered content for cluster ID {cluster_id}: {filtered_posts}")

    else:
        # No search query, just show random posts
        filtered_posts = random_posts()
        print("No search query, showing random posts.")

    context = {
        'popular_content': popular_content,
        'filtered_posts': filtered_posts,
        'message': f"Search results for '{user_search_query}'" if user_search_query else "Showing popular content"
    }

    print(f"Context: {context}")
    return render(request, 'recommendations.html', context)
