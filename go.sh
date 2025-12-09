#!/bin/bash
docker compose up -d --build
echo "Tout est up !"
echo "Backend  → http://localhost:8000"
echo "Frontend → http://localhost:3000"
echo ""
echo "Pour recharger après modif Python  → ./go.sh indexer"
echo "Pour recharger après modif React   → ./go.sh frontend"
echo "Pour tout arrêter                  → ./go.sh down"

if [ "$1" = "indexer" ]; then
  docker compose restart indexer
  docker compose logs -f indexer
elif [ "$1" = "frontend" ]; then
  docker compose restart frontend
  docker compose logs -f frontend
elif [ "$1" = "down" ]; then
  docker compose down -v
else
  docker compose logs -f
fi