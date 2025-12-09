#!/usr/bin/env python3
"""
Test multimodal pour extraire les produits et leurs prix d'un ticket de caisse.
Ce script utilise Llama Stack avec un modèle multimodal pour analyser une image de ticket de caisse.
"""

import os
import sys
import json
import base64
import requests
from typing import Dict, List, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Configuration OpenTelemetry
def setup_tracing():
    """Configure le tracing OpenTelemetry pour envoyer les traces à otel-collector"""
    resource = Resource.create({
        "service.name": "multimodal-receipt-extractor",
        "service.version": "1.0.0",
    })
    
    provider = TracerProvider(resource=resource)
    
    # Exporter vers otel-collector
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv(
            "OTEL_TRACE_ENDPOINT",
            "http://otel-collector-collector.observability-hub.svc.cluster.local:4318/v1/traces"
        ),
        headers={}
    )
    
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(__name__)

# Configuration
LLAMA_STACK_URL = os.getenv(
    "LLAMA_STACK_URL",
    "http://llama-stack-instance-service.llama-serve.svc.cluster.local:8321"
)
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.2-3B-Instruct")

# Initialiser le tracing
tracer = setup_tracing()

def encode_image_to_base64(image_path: str) -> str:
    """Encode une image en base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_products_from_receipt(image_path: str) -> Dict[str, Any]:
    """
    Extrait les produits et leurs prix d'un ticket de caisse en utilisant un modèle multimodal.
    
    Args:
        image_path: Chemin vers l'image du ticket de caisse
        
    Returns:
        Dictionnaire contenant les produits extraits avec leurs prix
    """
    with tracer.start_as_current_span("extract_products_from_receipt") as span:
        span.set_attribute("image_path", image_path)
        span.set_attribute("model", MODEL_NAME)
        
        try:
            # Encoder l'image en base64
            with tracer.start_as_current_span("encode_image"):
                image_base64 = encode_image_to_base64(image_path)
                span.set_attribute("image_size_bytes", len(image_base64))
            
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

            # Appel à Llama Stack
            with tracer.start_as_current_span("llama_stack_request") as request_span:
                request_span.set_attribute("llama_stack_url", LLAMA_STACK_URL)
                request_span.set_attribute("model", MODEL_NAME)
                
                payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
                
                response = requests.post(
                    f"{LLAMA_STACK_URL}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=120
                )
                
                request_span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code != 200:
                    error_msg = f"Erreur API: {response.status_code} - {response.text}"
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                    request_span.record_exception(Exception(error_msg))
                    raise Exception(error_msg)
            
            # Parser la réponse
            with tracer.start_as_current_span("parse_response"):
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
                
                span.set_attribute("products_count", len(extracted_data.get("products", [])))
                span.set_attribute("total_amount", extracted_data.get("total"))
                
                return extracted_data
                
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise

def main():
    """Fonction principale"""
    with tracer.start_as_current_span("multimodal_receipt_test") as main_span:
        main_span.set_attribute("test_type", "multimodal_receipt_extraction")
        
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
        
        main_span.set_attribute("input_image", image_path)
        
        print(f"🔍 Analyse du ticket de caisse: {image_path}")
        print(f"📡 Connexion à Llama Stack: {LLAMA_STACK_URL}")
        print(f"🤖 Modèle: {MODEL_NAME}\n")
        
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
            main_span.set_attribute("output_file", output_file)
            main_span.set_attribute("success", True)
            
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            main_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            main_span.record_exception(e)
            sys.exit(1)

if __name__ == "__main__":
    main()

