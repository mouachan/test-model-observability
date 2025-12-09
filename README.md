# Test Model Observability

Ce dépôt contient les scripts de test pour valider le fonctionnement de Llama Stack avec l'observabilité et le tracing distribué.

## 📋 À propos

Ces tests sont conçus pour fonctionner avec le projet [lls-observability](https://github.com/rh-ai-quickstart/lls-observability), un quickstart Red Hat qui déploie une infrastructure complète d'observabilité pour les applications AI sur OpenShift AI.

**Dépôt de base:** [rh-ai-quickstart/lls-observability](https://github.com/rh-ai-quickstart/lls-observability)

## 🚀 Prérequis

Avant d'exécuter ces tests, vous devez avoir déployé l'infrastructure d'observabilité et les services AI :

1. **Déployer le stack complet** selon les instructions du [dépôt principal](https://github.com/rh-ai-quickstart/lls-observability)
2. **Vérifier que les services sont disponibles** :
   ```bash
   # Vérifier Llama Stack
   oc get svc llama-stack-instance-service -n llama-serve
   
   # Vérifier Llama Guard
   oc get svc llama-guard-3-1b-predictor -n llama-serve
   
   # Vérifier otel-collector
   oc get opentelemetrycollector otel-collector -n observability-hub
   ```

## 📦 Installation

```bash
# Cloner ce dépôt
git clone https://github.com/mouachan/test-model-observability.git
cd test-model-observability

# Installer les dépendances
pip install -r requirements.txt
```

## 🧪 Tests disponibles

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

**Fonctionnalités:**
- Analyse d'image avec modèle multimodal
- Extraction structurée des produits et prix
- Génération de JSON avec les résultats
- Traces OpenTelemetry pour l'observabilité

**Résultats:**
- Affiche les produits extraits avec leurs prix
- Sauvegarde les résultats dans `receipt_extraction_result.json`
- Envoie les traces à Tempo via otel-collector

**Note:** Ce script nécessite un modèle multimodal compatible avec les images. Si votre modèle ne supporte pas directement les images, vous devrez peut-être utiliser un service OCR préalable ou adapter le script.

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

## 🔧 Configuration

Les scripts utilisent des variables d'environnement avec des valeurs par défaut pour se connecter aux services déployés dans le cluster :

### Variables d'environnement

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `LLAMA_STACK_URL` | `http://llama-stack-instance-service.llama-serve.svc.cluster.local:8321` | URL du service Llama Stack |
| `LLAMA_GUARD_URL` | `http://llama-guard-3-1b-predictor.llama-serve.svc.cluster.local/v1` | URL du service Llama Guard |
| `MODEL_NAME` | `meta-llama/Llama-3.2-3B-Instruct` | Nom du modèle à utiliser |
| `OTEL_TRACE_ENDPOINT` | `http://otel-collector-collector.observability-hub.svc.cluster.local:4318/v1/traces` | Endpoint OTLP pour les traces |

### Personnalisation

Pour utiliser des endpoints différents, définissez les variables d'environnement avant d'exécuter les tests :

```bash
export LLAMA_STACK_URL="http://votre-service:8321"
export LLAMA_GUARD_URL="http://votre-guard-service/v1"
export MODEL_NAME="votre-modele"
python test_multimodal_receipt.py receipt.jpg
```

## 📊 Traces OpenTelemetry

Les deux scripts envoient automatiquement les traces à l'otel-collector configuré. Vous pouvez visualiser les traces dans:

1. **OpenShift Console** → Observe → Traces
2. **Grafana** → Tempo datasource

Les traces incluent:
- Durée des requêtes
- Statut des réponses (succès/erreur)
- Métadonnées sur les modèles utilisés
- Informations sur les guardrails appliqués
- Spans détaillés pour chaque étape du processus

### Exemple de visualisation

Après avoir exécuté les tests, vous pouvez :

1. Ouvrir OpenShift Console
2. Naviguer vers **Observe** → **Traces**
3. Filtrer par service :
   - `multimodal-receipt-extractor` pour le test multimodal
   - `llama-guardrails-test` pour le test guardrails
4. Examiner les spans détaillés de chaque requête

## 🐳 Exécution depuis un Pod dans le cluster

Pour exécuter les tests depuis un pod dans le cluster (recommandé pour éviter les problèmes de réseau) :

### Option 1: Pod temporaire avec Python

```bash
# Créer un pod temporaire
oc run test-pod \
  --image=python:3.11 \
  --rm -it \
  --restart=Never \
  --namespace=llama-serve \
  -- sh

# Dans le pod, installer les dépendances
pip install requests opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

# Copier les scripts (depuis votre machine locale)
# ou cloner le dépôt dans le pod
git clone https://github.com/mouachan/test-model-observability.git
cd test-model-observability
pip install -r requirements.txt

# Exécuter les tests
python test_llama_guardrails.py
python test_multimodal_receipt.py <chemin_image>
```

### Option 2: Job Kubernetes

Créez un Job Kubernetes pour exécuter les tests :

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: test-model-observability
  namespace: llama-serve
spec:
  template:
    spec:
      containers:
      - name: test
        image: python:3.11
        command:
        - /bin/sh
        - -c
        - |
          pip install -r requirements.txt
          python test_llama_guardrails.py
        volumeMounts:
        - name: test-scripts
          mountPath: /tests
      volumes:
      - name: test-scripts
        configMap:
          name: test-scripts
      restartPolicy: Never
```

## 🔍 Dépannage

### Erreur de connexion à Llama Stack

**Symptômes:** `Connection refused` ou `Name resolution failed`

**Solutions:**
- Vérifier que le service `llama-stack-instance-service` est disponible dans le namespace `llama-serve`
- Vérifier les routes et les services: `oc get svc,route -n llama-serve`
- Si vous exécutez depuis l'extérieur du cluster, utilisez la route publique :
  ```bash
  export LLAMA_STACK_URL="https://$(oc get route llama-stack-instance-service -n llama-serve -o jsonpath='{.spec.host}')"
  ```

### Erreur de connexion à Llama Guard

**Symptômes:** `Connection refused` ou erreur 404

**Solutions:**
- Vérifier que le service `llama-guard-3-1b-predictor` est disponible
- Vérifier les logs: `oc logs -n llama-serve -l app=llama-guard`
- Vérifier que l'InferenceService est prêt: `oc get inferenceservice llama-guard-3-1b -n llama-serve`

### Traces non visibles dans Tempo

**Symptômes:** Les traces n'apparaissent pas dans l'interface

**Solutions:**
- Vérifier que l'otel-collector est déployé: `oc get opentelemetrycollector -n observability-hub`
- Vérifier les logs de l'otel-collector: `oc logs -n observability-hub -l app=otel-collector`
- Vérifier la configuration de l'endpoint OTLP dans les variables d'environnement
- Vérifier que Tempo est accessible: `oc get svc -n observability-hub | grep tempo`
- Attendre quelques secondes pour que les traces soient indexées

### Erreur "Model not found"

**Symptômes:** Le modèle spécifié n'est pas disponible

**Solutions:**
- Vérifier les modèles disponibles: `oc get inferenceservice -n llama-serve`
- Utiliser le nom exact du modèle déployé
- Vérifier que le modèle est prêt: `oc get inferenceservice <nom-modele> -n llama-serve -o jsonpath='{.status.conditions}'`

## 📚 Ressources

- **Dépôt principal:** [rh-ai-quickstart/lls-observability](https://github.com/rh-ai-quickstart/lls-observability)
- **Documentation OpenTelemetry:** [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- **Documentation Tempo:** [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
- **Documentation Llama Stack:** [Llama Stack Documentation](https://docs.llamastack.ai/)

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Ouvrir une issue pour signaler un bug ou proposer une amélioration
- Créer une pull request avec vos modifications
- Partager vos cas d'usage et vos retours d'expérience

## 📝 Licence

Ce projet fait partie du quickstart [lls-observability](https://github.com/rh-ai-quickstart/lls-observability) et suit la même licence.
