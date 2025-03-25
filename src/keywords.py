"""
Keywords configuration for LinkedIn Recruiting Bot in multiple languages
"""

# English keywords
EN_KEYWORDS = [
    "Recruiting",
    "AI recruitment",
]

# French keywords
FR_KEYWORDS = [
    "Recrutement",
    "Recrutement IA",

]

# Spanish keywords
ES_KEYWORDS = [
    "Reclutamiento IA",

]

# All keywords combined (for multilingual searches)
ALL_KEYWORDS = EN_KEYWORDS + FR_KEYWORDS + ES_KEYWORDS

# Mapping of languages to their respective keywords
LANGUAGE_KEYWORDS = {
    "en": EN_KEYWORDS,
    "fr": FR_KEYWORDS,
    "es": ES_KEYWORDS,
    "all": ALL_KEYWORDS
}

def get_keywords(language="en"):
    """
    Get keywords for a specific language
    
    Args:
        language (str): Language code ('en', 'fr', 'es', or 'all')
        
    Returns:
        list: List of keywords for the specified language
    """
    return LANGUAGE_KEYWORDS.get(language.lower(), EN_KEYWORDS)