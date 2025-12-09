# Guide de dépannage - Tests Model Observability

## Problème: Connection refused à llama-stack-instance

### Symptômes
```
❌ Erreur: HTTPConnectionPool(host='llama-stack-instance-service.llama-serve.svc.cluster.local', port=8321): 
Max retries exceeded with url: /v1/chat/completions 
(Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### Causes possibles

1. **Le pod `llama-stack-instance` n'est pas en cours d'exécution**
   ```bash
   oc get pods -n llama-serve | grep llama-stack-instance
   ```
   Si le pod est en état `Init:CreateContainerConfigError` ou `Error`, c'est un problème de déploiement.

2. **Le modèle vLLM requis n'est pas déployé**
   `llama-stack-instance` dépend du modèle `llama3-2-3b`. Vérifiez:
   ```bash
   oc get inferenceservice -n llama-serve
   ```
   Si `llama3-2-3b` n'est pas dans la liste, vous devez le déployer:
   ```bash
   # Depuis le dépôt lls-observability
   helm install llama3-2-3b ./helm/03-ai-services/llama3.2-3b -n llama-serve \
     --set model.name="meta-llama/Llama-3.2-3B-Instruct" \
     --set resources.limits."nvidia\.com/gpu"=1
   ```

### Solutions

#### Solution 1: Vérifier et corriger le déploiement

1. **Vérifier les événements du pod:**
```bash
oc describe pod -n llama-serve -l app.kubernetes.io/name=llama-stack-instance
```

2. **Vérifier les logs de l'init container:**
```bash
oc logs -n llama-serve -l app.kubernetes.io/name=llama-stack-instance -c ca-bundle-init
```

3. **Problème courant: runAsNonRoot**
Si vous voyez l'erreur `container has runAsNonRoot and image will run as root`, vous devez corriger la configuration du pod dans le chart Helm.

#### Solution 2: Utiliser directement vLLM (recommandé pour les tests)

Si `llama-stack-instance` ne fonctionne pas, vous pouvez utiliser directement le service vLLM:

```bash
# Trouver l'URL du service vLLM
export LLAMA_STACK_URL="http://llama3-2-3b-predictor.llama-serve.svc.cluster.local:8080"
export MODEL_NAME="meta-llama/Llama-3.2-3B-Instruct"

python test_multimodal_receipt.py receipt.jpeg
```

**Note:** vLLM utilise l'API OpenAI-compatible, donc le format des requêtes est le même.

#### Solution 3: Utiliser la route publique (si disponible)

Si une route est configurée pour le service:

```bash
# Trouver la route
ROUTE_HOST=$(oc get route llama-stack-instance-service -n llama-serve -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -n "$ROUTE_HOST" ]; then
    export LLAMA_STACK_URL="https://${ROUTE_HOST}"
    python test_multimodal_receipt.py receipt.jpeg
else
    echo "Aucune route trouvée"
fi
```

#### Solution 4: Créer une route pour le service

Si le service fonctionne mais n'a pas de route:

```bash
# Créer une route pour llama-stack-instance-service
oc create route passthrough llama-stack-instance-route \
  --service=llama-stack-instance-service \
  --port=8321 \
  -n llama-serve

# Utiliser la route
export LLAMA_STACK_URL="https://$(oc get route llama-stack-instance-route -n llama-serve -o jsonpath='{.spec.host}')"
python test_multimodal_receipt.py receipt.jpeg
```

## Vérification de la connectivité

### Depuis un pod dans le cluster

```bash
# Créer un pod de test
oc run test-curl --image=curlimages/curl --rm -it --restart=Never -n llama-serve -- sh

# Dans le pod, tester la connexion
curl -v http://llama-stack-instance-service.llama-serve.svc.cluster.local:8321/health
```

### Depuis votre machine locale

Si vous êtes en dehors du cluster, vous devez utiliser une route ou un port-forward:

```bash
# Port-forward vers le service
oc port-forward svc/llama-stack-instance-service 8321:8321 -n llama-serve

# Dans un autre terminal
export LLAMA_STACK_URL="http://localhost:8321"
python test_multimodal_receipt.py receipt.jpeg
```

## Vérification des services disponibles

```bash
# Lister tous les services dans llama-serve
oc get svc -n llama-serve

# Vérifier les endpoints
oc get endpoints -n llama-serve

# Vérifier les pods en cours d'exécution
oc get pods -n llama-serve
```

## Modèles disponibles

Pour vérifier quels modèles sont disponibles:

```bash
# Lister les InferenceServices
oc get inferenceservice -n llama-serve

# Vérifier le statut d'un modèle spécifique
oc get inferenceservice llama3-2-3b -n llama-serve -o yaml
```

## Logs utiles

```bash
# Logs du service llama-stack-instance
oc logs -n llama-serve -l app.kubernetes.io/name=llama-stack-instance --tail=100

# Logs de l'otel-collector
oc logs -n observability-hub -l app=otel-collector --tail=100

# Événements du namespace
oc get events -n llama-serve --sort-by='.lastTimestamp' | tail -20
```

## Support

Si le problème persiste:
1. Vérifiez la documentation du dépôt principal: https://github.com/rh-ai-quickstart/lls-observability
2. Ouvrez une issue avec les détails de votre environnement
3. Incluez les sorties des commandes de diagnostic ci-dessus

