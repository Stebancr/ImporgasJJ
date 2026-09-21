#!/bin/bash
# Script de inicialización de Ollama para producción
# Asegura que el modelo esté descargado antes de que el backend lo use

echo "🚀 Iniciando Ollama..."
ollama serve &
OLLAMA_PID=$!

echo "⏳ Esperando que Ollama esté listo..."
sleep 10

OLLAMA_MODEL="${OLLAMA_MODEL:-qwen:4b}"
echo "📦 Verificando modelo ${OLLAMA_MODEL}..."
if ollama list | grep -q "${OLLAMA_MODEL}"; then
  echo "✅ Modelo ya descargado"
else
  echo "⬇️ Descargando modelo ${OLLAMA_MODEL} (puede tomar varios minutos)..."
  ollama pull "${OLLAMA_MODEL}"
  echo "✅ Modelo descargado exitosamente"
fi

echo "✅ Ollama listo para recibir peticiones"
wait $OLLAMA_PID
