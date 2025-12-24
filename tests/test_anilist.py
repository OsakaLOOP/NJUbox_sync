import requests

url = 'https://graphql.anilist.co'
query = '''
query ($search: String) {
  Media (search: $search, type: ANIME, sort: SEARCH_MATCH) {
    id
    title {
      romaji
      english
      native
    }
    description
    coverImage {
      large
    }
    season
    seasonYear
    episodes
    status
    genres
    averageScore
    studios(isMain: true) {
      nodes {
        name
      }
    }
  }
}
'''

variables = {
    'search': 'Shingeki no Kyojin'
}

response = requests.post(url, json={'query': query, 'variables': variables})
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code}")
    print(response.text)
