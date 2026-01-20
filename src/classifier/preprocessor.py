# src/classifier/preprocessor.py
"""
Module de prétraitement NLP pour améliorer la qualité de classification.
Pipeline : Nettoyage → Détection langue → Tokenisation → Stop words → Lemmatisation
"""

import re
import unicodedata
import logging
from langdetect import detect, LangDetectException
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer, SnowballStemmer

logger = logging.getLogger(__name__)

# Téléchargement des ressources NLTK (une seule fois au démarrage)
def _download_nltk_resources():
    """Télécharge les ressources NLTK nécessaires."""
    resources = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/stopwords', 'stopwords'),
        ('corpora/wordnet', 'wordnet'),
    ]
    for path, name in resources:
        try:
            nltk.data.find(path)
        except LookupError:
            logger.info(f"Téléchargement NLTK: {name}")
            nltk.download(name, quiet=True)

_download_nltk_resources()


# -------------------------------------------------
# Étape 1 : Nettoyage des caractères spéciaux
# -------------------------------------------------
def clean_text(text: str) -> str:
    """
    Nettoie le texte brut :
    - Supprime les caractères de contrôle
    - Normalise les espaces et sauts de ligne
    - Garde les accents (utile pour la détection de langue)
    """
    if not text:
        return ""

    # Suppression des caractères de contrôle (sauf newline et tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Remplacer les sauts de ligne multiples par un seul espace
    text = re.sub(r'\n+', ' ', text)

    # Normaliser les espaces multiples
    text = re.sub(r'\s+', ' ', text)

    # Supprimer les caractères non-imprimables Unicode
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')

    return text.strip()


# -------------------------------------------------
# Étape 2 : Normalisation du texte
# -------------------------------------------------
def normalize_text(text: str, keep_accents: bool = True) -> str:
    """
    Normalise le texte :
    - Conversion en minuscules
    - Normalisation Unicode (NFC)
    - Optionnel : suppression des accents
    """
    if not text:
        return ""

    # Minuscules
    text = text.lower()

    # Normalisation Unicode
    if keep_accents:
        text = unicodedata.normalize('NFC', text)
    else:
        # Décompose puis supprime les accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    return text


# -------------------------------------------------
# Étape 3 : Détection de langue
# -------------------------------------------------
def detect_language(text: str) -> str:
    """
    Détecte la langue du texte.
    Retourne 'fr' ou 'en' (fallback).
    """
    if not text or len(text) < 20:
        return 'en'

    try:
        lang = detect(text)
        # On supporte principalement fr et en
        if lang in ['fr', 'en']:
            return lang
        return 'en'  # Fallback pour autres langues
    except LangDetectException:
        return 'en'


# -------------------------------------------------
# Étape 4 : Tokenisation
# -------------------------------------------------
def tokenize(text: str, lang: str) -> list[str]:
    """
    Tokenise le texte en mots.
    Filtre les tokens non-alphabétiques courts.
    """
    if not text:
        return []

    try:
        lang_nltk = 'french' if lang == 'fr' else 'english'
        tokens = word_tokenize(text, language=lang_nltk)
    except Exception:
        # Fallback simple si NLTK échoue
        tokens = text.split()

    # Filtrer : garder uniquement les tokens alphabétiques de 2+ caractères
    tokens = [t for t in tokens if t.isalpha() and len(t) >= 2]

    return tokens


# -------------------------------------------------
# Étape 5 : Suppression des stop words
# -------------------------------------------------
def remove_stopwords(tokens: list[str], lang: str) -> list[str]:
    """
    Supprime les mots vides selon la langue.
    """
    if not tokens:
        return []

    try:
        lang_nltk = 'french' if lang == 'fr' else 'english'
        stop_words = set(stopwords.words(lang_nltk))
    except Exception:
        stop_words = set()

    return [t for t in tokens if t.lower() not in stop_words]


# -------------------------------------------------
# Étape 6 : Lemmatisation / Stemming
# -------------------------------------------------
def lemmatize(tokens: list[str], lang: str) -> list[str]:
    """
    Réduit les mots à leur forme canonique.
    - Français : Stemming (SnowballStemmer)
    - Anglais : Lemmatisation (WordNet)
    """
    if not tokens:
        return []

    try:
        if lang == 'fr':
            stemmer = SnowballStemmer('french')
            return [stemmer.stem(t) for t in tokens]
        else:
            lemmatizer = WordNetLemmatizer()
            return [lemmatizer.lemmatize(t) for t in tokens]
    except Exception:
        return tokens


# -------------------------------------------------
# Pipeline complet
# -------------------------------------------------
def preprocess(text: str) -> dict:
    """
    Pipeline complet de prétraitement NLP.

    Args:
        text: Texte brut extrait du document

    Returns:
        dict avec :
        - text: texte prétraité (tokens rejoints)
        - lang: langue détectée ('fr' ou 'en')
        - token_count: nombre de tokens après filtrage
        - original_length: longueur du texte original
    """
    original_length = len(text) if text else 0

    # Étape 1 : Nettoyage
    cleaned = clean_text(text)

    # Étape 2 : Détection de langue (avant normalisation pour garder les indices)
    lang = detect_language(cleaned)

    # Étape 3 : Normalisation
    normalized = normalize_text(cleaned, keep_accents=True)

    # Étape 4 : Tokenisation
    tokens = tokenize(normalized, lang)

    # Étape 5 : Suppression stop words
    tokens = remove_stopwords(tokens, lang)

    # Étape 6 : Lemmatisation
    tokens = lemmatize(tokens, lang)

    # Reconstruction du texte
    processed_text = ' '.join(tokens)

    return {
        'text': processed_text,
        'lang': lang,
        'token_count': len(tokens),
        'original_length': original_length
    }
