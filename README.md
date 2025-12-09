# Tests pour Llama Stack Observability

Ce dossier contient les scripts de test pour valider le fonctionnement de Llama Stack avec l'observabilité.

## Prérequis

1. Installer les dépendances Python:
```bash
pip install -r requirements.txt
```

2. Configurer les variables d'environnement (optionnel):
```bash
export LLAMA_STACK_URL="http://llama-stack-instance-service.llama-serve.svc.cluster.local:8321"
export LLAMA_GUARD_URL="http://llama-guard-3-1b-predictor.llama-serve.svc.cluster.local/v1"
export MODEL_NAME="meta-llama/Llama-3.2-3B-Instruct"
export OTEL_TRACE_ENDPOINT="http://otel-collector-collector.observability-hub.svc.cluster.local:4318/v1/traces"
```

## Tests disponibles

### 1. Test Multimodal - Extraction de ticket de caisse

Ce test utilise un modèle multimodal pour extraire les produits et leurs prix d'une image de ticket de caisse.

**Préparation:**
Si vous avez une URL d'image, vous pouvez la télécharger d'abord:
```bash
python download_receipt_image.py <url_de_l_image> receipt.jpg
```

**Usage:**
```bash
python test_multimodal_receipt.py <chemin_vers_image>
```

**Exemple:**
```bash
# Télécharger l'image depuis une URL (optionnel)
python download_receipt_image.py https://example.com/receipt.jpg receipt.jpg

# Analyser l'image
python test_multimodal_receipt.py receipt.jpg
```

**Note:** Ce script nécessite un modèle multimodal compatible avec les images. Si votre modèle ne supporte pas directement les images, vous devrez peut-être utiliser un service OCR préalable ou adapter le script.

**Fonctionnalités:**
- Analyse d'image avec modèle multimodal
- Extraction structurée des produits et prix
- Génération de JSON avec les résultats
- Traces OpenTelemetry pour l'observabilité

**Résultats:**
- Affiche les produits extraits avec leurs prix
- Sauvegarde les résultats dans `receipt_extraction_result.json`
- Envoie les traces à Tempo via otel-collector

### 2. Test Llama avec Guardrails

Ce test vérifie que Llama Guard fonctionne correctement pour filtrer les réponses non sécurisées.

**Usage:**
```bash
python test_llama_guardrails.py
```

**Fonctionnalités:**
- Génération de réponses avec Llama Stack
- Vérification avec Llama Guard pour chaque réponse
- Tests avec différents types de prompts (sûrs et potentiellement problématiques)
- Rapport détaillé des résultats

**Résultats:**
- Affiche chaque test avec le statut SAFE/UNSAFE
- Sauvegarde les résultats dans `guardrails_test_results.json`
- Envoie les traces à Tempo via otel-collector

## Traces OpenTelemetry

Les deux scripts envoient automatiquement les traces à l'otel-collector configuré. Vous pouvez visualiser les traces dans:

1. **OpenShift Console** → Observe → Traces
2. **Grafana** → Tempo datasource

Les traces incluent:
- Durée des requêtes
- Statut des réponses (succès/erreur)
- Métadonnées sur les modèles utilisés
- Informations sur les guardrails appliqués

## Exécution depuis un Pod dans le cluster

Pour exécuter les tests depuis un pod dans le cluster:

```bash
# Créer un pod temporaire
oc run test-pod --image=python:3.11 --rm -it --restart=Never -- sh

# Dans le pod, installer les dépendances et exécuter les tests
pip install -r requirements.txt
python test_multimodal_receipt.py <image_path>
python test_llama_guardrails.py
```

## Dépannage

### Erreur de connexion à Llama Stack
- Vérifier que le service `llama-stack-instance-service` est disponible dans le namespace `llama-serve`
- Vérifier les routes et les services: `oc get svc,route -n llama-serve`

### Erreur de connexion à Llama Guard
- Vérifier que le service `llama-guard-3-1b-predictor` est disponible
- Vérifier les logs: `oc logs -n llama-serve -l app=llama-guard`

### Traces non visibles dans Tempo
- Vérifier que l'otel-collector est déployé: `oc get opentelemetrycollector -n observability-hub`
- Vérifier les logs de l'otel-collector: `oc logs -n observability-hub -l app=otel-collector`
- Vérifier la configuration de l'endpoint OTLP dans les variables d'environnement

