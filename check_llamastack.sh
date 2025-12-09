#!/bin/bash
# Script de vérification de llama-stack-instance

set -e

NAMESPACE="llama-serve"
DISTRIBUTION_NAME="llama-stack-instance"

echo "🔍 Vérification de llama-stack-instance"
echo "========================================"
echo ""

# 1. Vérifier le LlamaStackDistribution
echo "1️⃣  État du LlamaStackDistribution:"
oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.status.phase}' 2>/dev/null && echo "" || echo "❌ Non trouvé"
echo ""

# 2. Vérifier les conditions
echo "2️⃣  Conditions:"
oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{range .status.conditions[*]}{.type}: {.status} ({.reason}){"\n"}{end}' 2>/dev/null || echo "Aucune condition trouvée"
echo ""

# 3. Vérifier le service
echo "3️⃣  Service:"
if oc get svc llama-stack-instance-service -n ${NAMESPACE} &>/dev/null; then
    echo "✅ Service existe"
    oc get svc llama-stack-instance-service -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}:{.spec.ports[0].port}' && echo ""
else
    echo "❌ Service non trouvé"
fi
echo ""

# 4. Vérifier les endpoints
echo "4️⃣  Endpoints:"
ENDPOINTS=$(oc get endpoints llama-stack-instance-service -n ${NAMESPACE} -o jsonpath='{.subsets[0].addresses[*].ip}' 2>/dev/null)
if [ -n "$ENDPOINTS" ]; then
    echo "✅ Endpoints: $ENDPOINTS"
else
    echo "❌ Aucun endpoint prêt"
    NOT_READY=$(oc get endpoints llama-stack-instance-service -n ${NAMESPACE} -o jsonpath='{.subsets[0].notReadyAddresses[*].ip}' 2>/dev/null)
    if [ -n "$NOT_READY" ]; then
        echo "⚠️  Endpoints non prêts: $NOT_READY"
    fi
fi
echo ""

# 5. Vérifier les pods
echo "5️⃣  Pods:"
PODS=$(oc get pods -n ${NAMESPACE} -l app.kubernetes.io/name=${DISTRIBUTION_NAME} -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
if [ -n "$PODS" ]; then
    for pod in $PODS; do
        PHASE=$(oc get pod $pod -n ${NAMESPACE} -o jsonpath='{.status.phase}' 2>/dev/null)
        echo "   Pod: $pod - Phase: $PHASE"
        if [ "$PHASE" != "Running" ]; then
            echo "   ⚠️  Pod non en cours d'exécution"
            oc get pod $pod -n ${NAMESPACE} -o jsonpath='{.status.containerStatuses[*].state.waiting.reason}' 2>/dev/null | grep -q . && \
                oc get pod $pod -n ${NAMESPACE} -o jsonpath='{.status.containerStatuses[*].state.waiting.reason}' && echo ""
        fi
    done
else
    echo "❌ Aucun pod trouvé"
fi
echo ""

# 6. Vérifier la configuration VLLM_URL
echo "6️⃣  Configuration VLLM_URL:"
VLLM_URL=$(oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.server.containerSpec.env[?(@.name=="VLLM_URL")].value}' 2>/dev/null)
if [ -n "$VLLM_URL" ]; then
    echo "   VLLM_URL: $VLLM_URL"
    # Extraire le nom du service
    SERVICE_NAME=$(echo $VLLM_URL | sed 's|http://||' | sed 's|:.*||')
    NAMESPACE_VLLM=$(echo $SERVICE_NAME | cut -d'.' -f2)
    echo "   Service attendu: $SERVICE_NAME dans namespace: $NAMESPACE_VLLM"
    
    # Vérifier si le service existe
    if oc get svc $(echo $SERVICE_NAME | cut -d'.' -f1) -n ${NAMESPACE_VLLM:-llama-serve} &>/dev/null; then
        echo "   ✅ Service vLLM trouvé"
    else
        echo "   ❌ Service vLLM non trouvé: $(echo $SERVICE_NAME | cut -d'.' -f1)"
    fi
else
    echo "   ⚠️  VLLM_URL non configuré"
fi
echo ""

# 7. Vérifier le modèle INFERENCE_MODEL
echo "7️⃣  Configuration INFERENCE_MODEL:"
INFERENCE_MODEL=$(oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.server.containerSpec.env[?(@.name=="INFERENCE_MODEL")].value}' 2>/dev/null)
echo "   INFERENCE_MODEL: ${INFERENCE_MODEL:-non configuré}"
echo ""

# 8. Résumé
echo "📊 RÉSUMÉ"
echo "========="
PHASE=$(oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.status.phase}' 2>/dev/null)
echo "Phase: $PHASE"

DEPLOYMENT_READY=$(oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.status.conditions[?(@.type=="DeploymentReady")].status}' 2>/dev/null)
echo "Deployment Ready: $DEPLOYMENT_READY"

SERVICE_READY=$(oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.status.conditions[?(@.type=="ServiceReady")].status}' 2>/dev/null)
echo "Service Ready: $SERVICE_READY"

HEALTH_CHECK=$(oc get llamastackdistribution ${DISTRIBUTION_NAME} -n ${NAMESPACE} -o jsonpath='{.status.conditions[?(@.type=="HealthCheck")].status}' 2>/dev/null)
echo "Health Check: $HEALTH_CHECK"
echo ""

if [ "$DEPLOYMENT_READY" != "True" ] || [ "$HEALTH_CHECK" != "True" ]; then
    echo "❌ llama-stack-instance ne fonctionne PAS correctement"
    echo ""
    echo "💡 Solutions:"
    echo "   1. Vérifier que le modèle vLLM attendu est déployé"
    echo "   2. Vérifier les logs: oc logs -n ${NAMESPACE} -l app.kubernetes.io/name=${DISTRIBUTION_NAME}"
    echo "   3. Utiliser directement votre modèle: llama-instruct-32-3b"
    exit 1
else
    echo "✅ llama-stack-instance fonctionne correctement"
    exit 0
fi

