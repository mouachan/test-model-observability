# Solution rapide : llama-stack-instance en erreur

Si `llama-stack-instance` est en erreur, vous avez plusieurs options :

1. **Utiliser directement vLLM** (si déployé) - API OpenAI-compatible
2. **Déployer le modèle manquant** - Le problème vient souvent d'un modèle non déployé
3. **Corriger llama-stack-instance** - Vérifier les logs et corriger la configuration

## Solution immédiate

### Depuis un terminal ou script Python

```bash
export LLAMA_STACK_URL="http://llama3-2-3b-predictor.llama-serve.svc.cluster.local:8080"
export MODEL_NAME="meta-llama/Llama-3.2-3B-Instruct"
python test_multimodal_receipt.py download/receipt.jpeg
```

### Depuis Jupyter

Dans une cellule du notebook, avant d'exécuter le test:

```python
import os
os.environ['LLAMA_STACK_URL'] = 'http://llama3-2-3b-predictor.llama-serve.svc.cluster.local:8080'
os.environ['MODEL_NAME'] = 'meta-llama/Llama-3.2-3B-Instruct'
```

## Vérifier les services disponibles

```bash
# Lister tous les InferenceServices
oc get inferenceservice -n llama-serve

# Lister tous les services
oc get svc -n llama-serve

# Vérifier l'état de llama-stack-instance
oc get pods -n llama-serve | grep llama-stack-instance
oc describe pod -n llama-serve -l app.kubernetes.io/name=llama-stack-instance
```

## Si le modèle vLLM n'est pas déployé

Si vous ne voyez pas `llama3-2-3b` dans les InferenceServices, vous devez le déployer :

```bash
# Depuis le dépôt lls-observability
cd lls-observability
helm install llama3-2-3b ./helm/03-ai-services/llama3.2-3b -n llama-serve \
  --set model.name="meta-llama/Llama-3.2-3B-Instruct" \
  --set resources.limits."nvidia\.com/gpu"=1

# Attendre que le modèle soit prêt
oc wait --for=condition=Ready inferenceservice/llama3-2-3b -n llama-serve --timeout=600s
```

## Pourquoi utiliser vLLM directement ?

- ✅ Même API OpenAI-compatible que llama-stack-instance
- ✅ Pas de dépendance sur llama-stack-instance
- ✅ Plus simple et direct
- ✅ Fonctionne même si llama-stack-instance est en erreur

## Différences mineures

- vLLM expose directement l'API OpenAI, donc pas besoin du chemin `/v1/chat/completions` si vous utilisez l'URL complète
- Le format des requêtes reste identique
- Les traces OpenTelemetry fonctionnent de la même manière

## Corriger llama-stack-instance (optionnel)

Si vous voulez corriger llama-stack-instance:

1. **Vérifier les logs:**
   ```bash
   oc logs -n llama-serve -l app.kubernetes.io/name=llama-stack-instance --tail=100
   ```

2. **Vérifier les événements:**
   ```bash
   oc describe pod -n llama-serve -l app.kubernetes.io/name=llama-stack-instance
   ```

3. **Vérifier que le modèle vLLM est déployé:**
   ```bash
   oc get inferenceservice llama3-2-3b -n llama-serve
   ```

4. **Redémarrer le pod:**
   ```bash
   oc delete pod -n llama-serve -l app.kubernetes.io/name=llama-stack-instance
   ```

