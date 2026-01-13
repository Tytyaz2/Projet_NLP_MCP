#!/usr/bin/env python3
"""
Script principal pour orchestrer le tri automatique de fichiers via MCP.
Usage: python main.py --folder <chemin_du_dossier> [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict
import logging

from src.tools import server

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_files_to_analyze(folder: Path, extensions: List[str] = None) -> List[Path]:
    """
    Récupère tous les fichiers à analyser dans le dossier.
    
    Args:
        folder: Chemin du dossier à scanner
        extensions: Liste des extensions à filtrer (ex: ['.pdf', '.docx'])
    
    Returns:
        Liste des chemins de fichiers
    """
    if extensions is None:
        extensions = ['.pdf', '.docx', '.txt', '.doc', '.odt']
    
    files = []
    for ext in extensions:
        files.extend(folder.rglob(f'*{ext}'))
    
    # Ne garder que les fichiers (pas les dossiers)
    files = [f for f in files if f.is_file()]
    
    logger.info(f" {len(files)} fichier(s) trouvé(s) dans {folder}")
    return files


def analyze_all_files(files: List[Path]) -> List[Dict]:
    """
    Analyse tous les fichiers avec l'outil MCP analyze_file.
    
    Args:
        files: Liste des fichiers à analyser
    
    Returns:
        Liste des informations extraites pour chaque fichier
    """
    logger.info(" Début de l'analyse des fichiers...")
    
    analyze_tool = server.tools.get("analyze_file")
    if not analyze_tool:
        logger.error(" Outil 'analyze_file' non trouvé dans le serveur MCP")
        return []
    
    files_info = []
    for i, file_path in enumerate(files, 1):
        logger.info(f"  [{i}/{len(files)}] Analyse de: {file_path.name}")
        try:
            info = analyze_tool(str(file_path))
            files_info.append(info)
            logger.info(f"    ✓ Type: {info['type']}, Keywords: {', '.join(info['keywords'][:3])}")
        except Exception as e:
            logger.error(f"    ✗ Erreur lors de l'analyse de {file_path.name}: {e}")
    
    logger.info(f" Analyse terminée : {len(files_info)}/{len(files)} fichiers analysés avec succès\n")
    return files_info


def group_analyzed_files(files_info: List[Dict]) -> Dict:
    """
    Groupe les fichiers analysés par type et keywords.
    
    Args:
        files_info: Liste des informations de fichiers
    
    Returns:
        Dictionnaire contenant les groupes
    """
    logger.info(" Regroupement des documents...")
    
    group_tool = server.tools.get("group_files")
    if not group_tool:
        logger.error(" Outil 'group_files' non trouvé dans le serveur MCP")
        return {"groups": []}
    
    try:
        groups = group_tool(files_info)
        logger.info(f" {len(groups['groups'])} groupe(s) créé(s)\n")
        
        # Afficher un résumé des groupes
        for i, group in enumerate(groups['groups'], 1):
            logger.info(f"  Groupe {i}: {group['type']} - {len(group['files'])} fichier(s)")
            logger.info(f"    Keywords: {', '.join(group['keywords'][:5])}")
        
        return groups
    except Exception as e:
        logger.error(f" Erreur lors du regroupement: {e}")
        return {"groups": []}


def apply_organization_plan(root_folder: Path, groups: Dict, dry_run: bool = False) -> Dict:
    """
    Applique le plan d'organisation en déplaçant les fichiers.
    
    Args:
        root_folder: Dossier racine où organiser les fichiers
        groups: Groupes de fichiers à organiser
        dry_run: Si True, simule les déplacements sans les effectuer
    
    Returns:
        Dictionnaire avec les déplacements effectués
    """
    if dry_run:
        logger.info(" MODE DRY-RUN : Simulation des déplacements (aucun fichier ne sera déplacé)\n")
    else:
        logger.info(" Application du plan d'organisation...\n")
    
    apply_tool = server.tools.get("apply_file_plan")
    if not apply_tool:
        logger.error(" Outil 'apply_file_plan' non trouvé dans le serveur MCP")
        return {"moved": []}
    
    if dry_run:
        # En mode dry-run, on simule juste l'affichage
        for i, group in enumerate(groups['groups'], 1):
            doc_type = group['type']
            keywords = group['keywords'][:2]
            logger.info(f"  Groupe {i} ({doc_type}) -> {len(group['files'])} fichier(s)")
            for file_path in group['files']:
                file_name = Path(file_path).name
                logger.info(f"    • {file_name}")
        logger.info("\n  Aucun fichier n'a été déplacé (mode dry-run)")
        return {"moved": []}
    
    try:
        result = apply_tool(str(root_folder), groups['groups'])
        logger.info(f" {len(result['moved'])} fichier(s) déplacé(s)\n")
        
        # Afficher les déplacements
        for move in result['moved']:
            from_path = Path(move['from']).name
            to_path = move['to']
            logger.info(f"  ✓ {from_path} → {to_path}")
        
        return result
    except Exception as e:
        logger.error(f" Erreur lors de l'application du plan: {e}")
        return {"moved": []}


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Tri automatique de documents avec MCP et Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py --folder ./documents
  python main.py --folder ./documents --dry-run
  python main.py --folder /data --extensions .pdf .docx
        """
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        default=os.getenv('FILES_TO_SORT', '/files'),
        help='Chemin du dossier à trier (défaut: /files ou variable d\'environnement FILES_TO_SORT)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulation sans déplacer les fichiers'
    )
    
    parser.add_argument(
        '--extensions',
        nargs='+',
        default=['.pdf', '.docx', '.txt', '.doc', '.odt'],
        help='Extensions de fichiers à analyser (défaut: .pdf .docx .txt .doc .odt)'
    )
    
    args = parser.parse_args()
    
    folder_path = Path(args.folder)
    
    # Vérifications
    if not folder_path.exists():
        logger.error(f" Le dossier {folder_path} n'existe pas")
        sys.exit(1)
    
    if not folder_path.is_dir():
        logger.error(f" {folder_path} n'est pas un dossier")
        sys.exit(1)
    
    # Bannière
    logger.info("=" * 60)
    logger.info(" MCP - Système de Tri Automatique de Documents")
    logger.info("=" * 60)
    logger.info(f" Dossier à trier: {folder_path}")
    logger.info(f" Extensions: {', '.join(args.extensions)}")
    logger.info("=" * 60 + "\n")
    
    # Étape 1 : Récupération des fichiers
    files = get_files_to_analyze(folder_path, args.extensions)
    if not files:
        logger.warning("  Aucun fichier à analyser")
        return
    
    # Étape 2 : Analyse des fichiers
    files_info = analyze_all_files(files)
    if not files_info:
        logger.error(" Aucun fichier n'a pu être analysé")
        return
    
    # Étape 3 : Regroupement
    groups = group_analyzed_files(files_info)
    if not groups['groups']:
        logger.error(" Aucun groupe n'a pu être créé")
        return
    
    # Étape 4 : Application du plan
    result = apply_organization_plan(folder_path, groups, args.dry_run)
    
    # Résumé final
    logger.info("\n" + "=" * 60)
    if args.dry_run:
        logger.info(" Simulation terminée avec succès")
    else:
        logger.info(f" Tri terminé : {len(result.get('moved', []))} fichier(s) organisé(s)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
