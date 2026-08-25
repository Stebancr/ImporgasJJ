#!/bin/bash
# Script de inicialización de Ollama para producción
# Asegura que el modelo esté descargado antes de que el backend lo use

echo "🚀 Iniciando Ollama..."
ollama serve &
OLLAMA_PID=$!

echo "⏳ Esperando que Ollama esté listo..."
sleep 10

echo "📦 Verificando modelo qwen2.5:1.5b..."
if ollama list | grep -q "qwen2.5:1.5b"; then
  echo "✅ Modelo ya descargado"
else
  echo "⬇️ Descargando modelo qwen2.5:1.5b (puede tomar varios minutos)..."
  ollama pull qwen2.5:1.5b
  echo "✅ Modelo descargado exitosamente"
fi

echo "✅ Ollama listo para recibir peticiones"
wait $OLLAMA_PID
