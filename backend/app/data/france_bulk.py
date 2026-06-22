"""French cities and business categories for nationwide bulk scraping."""

FRANCE_CITIES: list[str] = [
    "Paris",
    "Lyon",
    "Marseille",
    "Toulouse",
    "Nice",
    "Nantes",
    "Strasbourg",
    "Montpellier",
    "Bordeaux",
    "Lille",
    "Rennes",
    "Reims",
    "Toulon",
    "Saint-Étienne",
    "Le Havre",
    "Grenoble",
    "Dijon",
    "Angers",
    "Nîmes",
    "Villeurbanne",
    "Clermont-Ferrand",
    "Le Mans",
    "Aix-en-Provence",
    "Brest",
    "Tours",
    "Amiens",
    "Limoges",
    "Annecy",
    "Perpignan",
    "Metz",
    "Besançon",
    "Orléans",
    "Rouen",
    "Mulhouse",
    "Caen",
    "Nancy",
    "Avignon",
    "Dunkerque",
    "Poitiers",
    "Versailles",
    "Courbevoie",
    "Pau",
    "La Rochelle",
    "Cannes",
    "Antibes",
]

FRANCE_CATEGORIES: list[str] = [
    "Restaurant",
    "Hôtel",
    "Plombier",
    "Électricien",
    "Coiffeur",
    "Dentiste",
    "Boulangerie",
    "Garage automobile",
    "Pharmacie",
    "Avocat",
    "Comptable",
    "Agence immobilière",
]


def build_france_query_plan(
    *,
    cities: list[str] | None = None,
    categories: list[str] | None = None,
    max_queries: int | None = None,
) -> list[tuple[str, str]]:
    city_list = cities or FRANCE_CITIES
    category_list = categories or FRANCE_CATEGORIES
    queries = [(city, category) for city in city_list for category in category_list]
    if max_queries is not None:
        return queries[:max_queries]
    return queries
