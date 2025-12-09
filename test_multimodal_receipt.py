#!/usr/bin/env python3
"""
Test multimodal pour extraire les produits et leurs prix d'un ticket de caisse.
Ce script utilise directement vLLM pour analyser une image de ticket de caisse.
La traçabilité est automatique via OpenTelemetry dans OpenShift (pas de configuration manuelle).
"""

import os
import sys
import json
import base64
import requests
from typing import Dict, List, Any

# Configuration
# Utilisation directe de la route OpenShift du modèle vLLM
# La route expose une API OpenAI-compatible
# La traçabilité est automatique via l'instrumentation OpenTelemetry d'OpenShift
VLLM_ROUTE_URL = os.getenv(
    "VLLM_ROUTE_URL",
    "https://llama-instruct-32-3b-predictor-llama-instruct-32-3b-demo.apps.cluster.example.com"
)
MODEL_NAME = os.getenv("MODEL_NAME", "llama-instruct-32-3b")

def encode_image_to_base64(image_path: str) -> str:
    """Encode une image en base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_products_from_receipt(image_path: str) -> Dict[str, Any]:
    """
    Extrait les produits et leurs prix d'un ticket de caisse en utilisant un modèle multimodal.
    La traçabilité est automatique via OpenTelemetry dans OpenShift.
    
    Args:
        image_path: Chemin vers l'image du ticket de caisse
        
    Returns:
        Dictionnaire contenant les produits extraits avec leurs prix
    """
    try:
        # Encoder l'image en base64
        image_base64 = encode_image_to_base64(image_path)
        
        # Préparer le prompt pour l'extraction
        prompt = """Analyse ce ticket de caisse et extrais tous les produits avec leurs prix.
            
Format de réponse attendu (JSON):
{
  "products": [
    {
      "name": "nom du produit",
      "price": prix_en_euros,
      "quantity": quantité_si_disponible
    }
  ],
  "total": montant_total_en_euros,
  "date": "date_du_ticket",
  "store": "nom_du_magasin"
}

Extrais uniquement les informations présentes sur le ticket."""

        # Préparer le message avec l'image
        # Note: Le format dépend du modèle utilisé. Pour les modèles OpenAI-compatibles avec vision:
        # - Certains modèles supportent directement les images dans le format OpenAI
        # - D'autres nécessitent une approche différente
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        # Alternative: Si le modèle ne supporte pas les images directement,
        # on peut décrire l'image ou utiliser OCR préalable
        # Pour l'instant, on essaie avec le format standard

        # Appel direct au modèle via la route OpenShift - la traçabilité est automatique
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                f"{VLLM_ROUTE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
                verify=False  # Désactiver la vérification SSL pour les routes internes
            )
        except requests.exceptions.ConnectionError as e:
            error_msg = f"""❌ Erreur de connexion au modèle!

La route n'est pas accessible à l'adresse: {VLLM_ROUTE_URL}

🔍 Diagnostic:
1. Vérifiez que la route existe:
   oc get route -n llama-instruct-32-3b-demo | grep llama-instruct-32-3b

2. Obtenez l'URL de la route:
   oc get route llama-instruct-32-3b-predictor -n llama-instruct-32-3b-demo -o jsonpath='{{.spec.host}}'

3. Configuration recommandée:
   export VLLM_ROUTE_URL="https://<route-host-from-step-2>"
   export MODEL_NAME="llama-instruct-32-3b"

Erreur originale: {str(e)}"""
            raise Exception(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout lors de la connexion à vLLM après 120 secondes. Le service peut être surchargé ou inaccessible."
            raise Exception(error_msg)
        
        if response.status_code != 200:
            error_msg = f"""❌ Erreur API: {response.status_code}

Réponse du serveur: {response.text[:500]}

Vérifiez:
- Que le modèle '{MODEL_NAME}' est disponible
- Que la route est opérationnelle: oc get route -n llama-instruct-32-3b-demo
- Les logs du pod: oc logs -n llama-instruct-32-3b-demo -l app=llama-instruct-32-3b-predictor"""
            raise Exception(error_msg)
        
        # Parser la réponse
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
        
        # Extraire le JSON de la réponse
        # Le modèle peut retourner du texte avec du JSON, on essaie de l'extraire
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            extracted_data = json.loads(json_match.group())
        else:
            # Si pas de JSON trouvé, créer une structure basique
            extracted_data = {
                "raw_response": content,
                "products": [],
                "total": None,
                "date": None,
                "store": None
            }
        
        return extracted_data
        
    except Exception as e:
        raise

def main():
    """Fonction principale - la traçabilité est automatique via OpenTelemetry dans OpenShift"""
    # Chemin vers l'image du ticket de caisse
    # L'utilisateur doit fournir le chemin vers l'image
    if len(sys.argv) < 2:
        print("Usage: python test_multimodal_receipt.py <chemin_vers_image>")
        print("\nExemple:")
        print("  python test_multimodal_receipt.py ../docs/images/receipt.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Erreur: Le fichier {image_path} n'existe pas")
        sys.exit(1)
    
    print(f"🔍 Analyse du ticket de caisse: {image_path}")
    print(f"📡 Connexion au modèle via route OpenShift: {VLLM_ROUTE_URL}")
    print(f"🤖 Modèle: {MODEL_NAME}")
    print(f"📊 Traçabilité automatique via OpenTelemetry dans OpenShift\n")
    
    try:
        # Extraire les produits
        result = extract_products_from_receipt(image_path)
        
        # Afficher les résultats
        print("=" * 60)
        print("📋 RÉSULTATS DE L'EXTRACTION")
        print("=" * 60)
        
        if "store" in result and result["store"]:
            print(f"🏪 Magasin: {result['store']}")
        
        if "date" in result and result["date"]:
            print(f"📅 Date: {result['date']}")
        
        print(f"\n🛒 Produits ({len(result.get('products', []))}):")
        print("-" * 60)
        
        total_calculated = 0.0
        for i, product in enumerate(result.get("products", []), 1):
            name = product.get("name", "N/A")
            price = product.get("price", 0.0)
            quantity = product.get("quantity", 1)
            
            print(f"{i}. {name}")
            print(f"   Prix: {price:.2f} €")
            if quantity > 1:
                print(f"   Quantité: {quantity}")
            
            total_calculated += price * quantity
            print()
        
        print("-" * 60)
        if result.get("total"):
            print(f"💰 Total (extrait): {result['total']} €")
        print(f"💰 Total (calculé): {total_calculated:.2f} €")
        print("=" * 60)
        
        # Sauvegarder les résultats en JSON
        output_file = "receipt_extraction_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés dans: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

