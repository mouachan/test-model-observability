#!/usr/bin/env python3
"""
Script utilitaire pour télécharger l'image du ticket de caisse depuis une URL.
"""

import sys
import requests
from pathlib import Path

def download_image(url: str, output_path: str = "receipt.jpg"):
    """Télécharge une image depuis une URL"""
    try:
        print(f"📥 Téléchargement de l'image depuis: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Image téléchargée avec succès: {output_path}")
        print(f"   Taille: {len(response.content)} bytes")
        return output_path
        
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_receipt_image.py <url> [output_path]")
        print("\nExemple:")
        print("  python download_receipt_image.py https://example.com/receipt.jpg receipt.jpg")
        sys.exit(1)
    
    url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "receipt.jpg"
    
    download_image(url, output_path)

